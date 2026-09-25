"""Collect design internships from many job boards and email one de-duplicated digest.

Usage:
    python jobdigest.py --dry-run   # write digest.html, don't email or update seen.json
    python jobdigest.py             # email the digest and remember what was sent

Needs GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars to send (TO_EMAIL optional).
"""

import argparse
import concurrent.futures
import datetime
import html
import http.cookiejar
import json
import os
import re
import smtplib
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from email.mime.text import MIMEText
from pathlib import Path

import config

ROOT = Path(__file__).parent
SEEN_FILE = ROOT / "seen.json"

ROLE_RE = re.compile("|".join(config.ROLE_PATTERNS), re.I)
EXCLUDE_RE = re.compile("|".join(config.EXCLUDE_PATTERNS), re.I)
INTERN_RE = re.compile("|".join(config.INTERN_PATTERNS), re.I)

US_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()
US_RE = re.compile(
    r"united states|\busa?\b|u\.s\.|\bnyc\b|\bsf\b|new york|san francisco|seattle|"
    r"boston|chicago|los angeles|austin|san jose|mountain view|palo alto|menlo park|"
    r"sunnyvale|cupertino|redmond|bellevue|kirkland|san diego|san mateo|culver city|"
    r"washington|atlanta|denver|miami|dallas|houston|pittsburgh|philadelphia|"
    r",\s*(" + "|".join(US_STATES) + r")\b",
    re.I,
)
REGION_RES = {
    "US": US_RE,
    "Singapore": re.compile(r"singapore|\bsg\b", re.I),
    "Hong Kong": re.compile(r"hong kong|\bhk\b", re.I),
    "London": re.compile(r"london", re.I),
    "Taiwan": re.compile(r"taiwan|taipei|hsinchu|taichung|taoyuan|kaohsiung|台灣|臺灣|台北|臺北|"
                         r"新竹|台中|臺中|桃園|高雄|新北", re.I),
}
REGION_ORDER = list(REGION_RES) + ["Remote"]
# Anything that names a country outside our regions means "not for us", even if remote.
FOREIGN_RE = re.compile(
    r"canada|toronto|vancouver|\buk\b|united kingdom|ireland|dublin|germany|berlin|"
    r"france|paris|india|bangalore|bengaluru|japan|tokyo|australia|sydney|brazil|mexico|"
    r"netherlands|amsterdam|spain|poland|china|beijing|shanghai|korea|seoul|israel",
    re.I,
)

NO_SPONSOR_RE = re.compile(
    r"(not|unable to|cannot|can't|won't|will not)\s+(be able to\s+)?(offer|provide|support|sponsor)"
    r"[^.]{0,40}sponsor|"
    r"without (the need for )?(current or future |future )?(visa |employment )?sponsorship|"
    r"(does not|do not|doesn't|don't) (offer |provide )?(visa |immigration )?sponsor|"
    r"u\.?s\.? citizen(ship)? (is )?required|must be a u\.?s\.? citizen|security clearance",
    re.I,
)
SPONSOR_RE = re.compile(
    r"(visa )?sponsorship (is )?available|will sponsor|(offer|provide)s? (visa )?sponsorship|"
    r"sponsorship (may be|can be) (provided|offered)",
    re.I,
)


BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


def fetch(url, body=None, ua=BROWSER_UA, headers=None):
    """GET, or POST `body` as JSON when given. Returns the raw response bytes."""
    headers = {"User-Agent": ua, "Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            time.sleep(5 * 2 ** attempt)  # the site asked us to slow down
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(5)  # network blip; try again


def fetch_json(url, body=None, headers=None):
    return json.loads(fetch(url, body, headers=headers))


def strip_html(text):
    return re.sub(r"<[^>]+>", " ", html.unescape(text or ""))


def sponsorship_from_text(text):
    if NO_SPONSOR_RE.search(text):
        return "No sponsorship"
    if SPONSOR_RE.search(text):
        return "Sponsors"
    return "Not stated"


def regions_for(locations):
    joined = " | ".join(locations)
    found = [name for name, rx in REGION_RES.items() if name in config.REGIONS and rx.search(joined)]
    if not found and re.search(r"remote|anywhere", joined, re.I) and not FOREIGN_RE.search(joined):
        found = ["Remote"]
    return found


def is_design_role(title):
    return bool(ROLE_RE.search(title) and not EXCLUDE_RE.search(title))


def is_design_internship(title):
    return is_design_role(title) and bool(INTERN_RE.search(title))


def job(company, title, url, locations, source, sponsorship, posted=None):
    return {
        "company": company.strip(),
        "title": re.sub(r"\s+", " ", title).strip(),
        "url": url,
        "locations": [l.strip() for l in locations if l and l.strip()],
        "source": source,
        "sponsorship": sponsorship,
        "posted": posted,
    }


# ---------- sources ----------

def from_greenhouse(slug):
    data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    company = data.get("meta", {}).get("name") if isinstance(data.get("meta"), dict) else None
    out = []
    for j in data.get("jobs", []):
        if not is_design_internship(j["title"]):
            continue
        locs = [(j.get("location") or {}).get("name", "")]
        locs += [o.get("name", "") for o in j.get("offices", [])]
        out.append(job(
            company or j.get("company_name") or slug.title(), j["title"], j["absolute_url"],
            locs, "Greenhouse", sponsorship_from_text(strip_html(j.get("content"))),
            (j.get("first_published") or j.get("updated_at") or "")[:10] or None,
        ))
    return out


def from_lever(slug):
    data = fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in data:
        if not is_design_internship(j["text"]):
            continue
        cats = j.get("categories", {})
        locs = cats.get("allLocations") or [cats.get("location", "")]
        text = " ".join([j.get("descriptionPlain", ""), j.get("additionalPlain", "")]
                        + [strip_html(l.get("content", "")) for l in j.get("lists", [])])
        posted = datetime.datetime.fromtimestamp(j["createdAt"] / 1000, datetime.timezone.utc).date().isoformat()
        out.append(job(slug.title(), j["text"], j["hostedUrl"], locs, "Lever",
                       sponsorship_from_text(text), posted))
    return out


def from_ashby(slug):
    data = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{urllib.parse.quote(slug)}")
    out = []
    for j in data.get("jobs", []):
        if not is_design_internship(j["title"]):
            continue
        locs = [j.get("location", "")] + [
            s.get("location", "") for s in j.get("secondaryLocations", [])
        ]
        if j.get("isRemote"):
            locs.append("Remote")
        out.append(job(config.NAMES.get(slug, slug.title()), j["title"], j["jobUrl"], locs, "Ashby",
                       sponsorship_from_text(j.get("descriptionPlain", "")),
                       (j.get("publishedAt") or "")[:10] or None))
    return out


def from_smartrecruiters(slug):
    base = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    out, offset = [], 0
    while True:  # keyword search is unreliable here, so page through everything
        page = fetch_json(f"{base}?limit=100&offset={offset}")
        for j in page.get("content", []):
            if not is_design_internship(j["name"]):
                continue
            detail = fetch_json(f"{base}/{j['id']}")
            sections = (detail.get("jobAd") or {}).get("sections", {})
            text = " ".join(strip_html(s.get("text")) for s in sections.values())
            loc = j.get("location", {})
            locs = [loc.get("fullLocation", "")] + (["Remote"] if loc.get("remote") else [])
            out.append(job(j["company"]["name"], j["name"],
                           f"https://jobs.smartrecruiters.com/{slug}/{j['id']}", locs,
                           "SmartRecruiters", sponsorship_from_text(text),
                           (j.get("releasedDate") or "")[:10] or None))
        offset += 100
        if offset >= page.get("totalFound", 0):
            return out


# Big-company career sites don't list everything in one call, so we search them.
# Their keyword search is loose; is_design_internship() does the real filtering.
SEARCH_TERMS = ["design intern", "UX intern", "research intern"]


def from_workday(site):
    host, tenant, name = site["host"], site["tenant"], site["site"]
    api = f"https://{host}/wday/cxs/{tenant}/{name}"
    paths = {}
    for term in SEARCH_TERMS:
        for offset in (0, 20):
            body = {"appliedFacets": site.get("facets", {}), "limit": 20, "offset": offset,
                    "searchText": term}
            postings = fetch_json(f"{api}/jobs", body).get("jobPostings", [])
            for p in postings:
                if is_design_internship(p.get("title", "")):
                    paths[p["externalPath"]] = p["title"]
            if len(postings) < 20:
                break
    out = []
    for path, title in paths.items():
        info = fetch_json(f"{api}{path}").get("jobPostingInfo", {})
        locs = [info.get("location", "")] + info.get("additionalLocations", [])
        out.append(job(site["company"], title, f"https://{host}/{name}{path}", locs, "Workday",
                       sponsorship_from_text(strip_html(info.get("jobDescription"))),
                       info.get("startDate")))
    return out


def from_oracle(site):
    host, num = site["host"], site["site"]
    api = f"https://{host}/hcmRestApi/resources/latest"
    found = {}
    for term in SEARCH_TERMS:
        url = (f"{api}/recruitingCEJobRequisitions?onlyData=true"
               f"&expand=requisitionList.secondaryLocations"
               f"&finder=findReqs;siteNumber={num},keyword={urllib.parse.quote(term)},limit=50")
        items = fetch_json(url).get("items") or [{}]
        for r in items[0].get("requisitionList", []):
            if is_design_internship(r.get("Title", "")):
                found[r["Id"]] = r
    out = []
    for rid, r in found.items():
        detail = fetch_json(
            f"{api}/recruitingCEJobRequisitionDetails?onlyData=true&expand=all"
            f'&finder=ById;Id="{rid}",siteNumber={num}'
        ).get("items") or [{}]
        text = " ".join(strip_html(detail[0].get(k)) for k in
                        ("ExternalDescriptionStr", "ExternalQualificationsStr",
                         "ExternalResponsibilitiesStr"))
        locs = [r.get("PrimaryLocation", "")] + [l.get("Name", "") for l in
                                                 r.get("secondaryLocations", [])]
        out.append(job(site["company"], r["Title"],
                       f"https://{host}/hcmUI/CandidateExperience/en/sites/"
                       f"{site.get('url_site', num)}/job/{rid}",
                       locs, "Oracle", sponsorship_from_text(text), r.get("PostedDate")))
    return out


def from_phenom(site):
    found = {}
    for term in SEARCH_TERMS:
        body = {"lang": site.get("lang", "en_us"), "deviceType": "desktop",
                "country": site.get("country", "us"),
                "pageName": "search-results", "ddoKey": "refineSearch", "sortBy": "",
                "subsearch": "", "from": 0, "jobs": True, "counts": True, "all_fields": [],
                "size": 50, "clearAll": False, "jdsource": "facets", "isSliderEnable": False,
                "pageId": "page20", "siteType": "external", "keywords": term, "global": True,
                "selected_fields": {}, "locationData": {}}
        data = fetch_json(f"{site['base']}/widgets", body)
        for j in data.get("refineSearch", {}).get("data", {}).get("jobs", []):
            if is_design_internship(j.get("title", "")):
                found[j.get(site.get("id_field", "jobId"))] = j
    return [
        job(site["company"], j["title"], f"{site['base']}/{site.get('path', 'us/en')}/job/{jid}",
            j.get("multi_location") or [j.get("location", "")], "Phenom",
            sponsorship_from_text(j.get("descriptionTeaser", "")),
            (j.get("postedDate") or "")[:10] or None)
        for jid, j in found.items()
    ]


def from_ibm():
    out = []
    for term in SEARCH_TERMS:
        body = {"appId": "careers", "scopes": ["careers2"], "size": 50, "from": 0, "lang": "zz",
                "query": {"bool": {"must": [{"simple_query_string": {
                    "query": term, "fields": ["title^2", "description"]}}]}},
                "_source": ["title", "url", "dcdate", "field_keyword_05", "field_keyword_19"]}
        for hit in fetch_json("https://www-api.ibm.com/search/api/v2", body)["hits"]["hits"]:
            src = hit["_source"]
            if is_design_internship(src.get("title", "")):
                loc = ", ".join(x for x in (src.get("field_keyword_19"),
                                            src.get("field_keyword_05")) if x)
                out.append(job("IBM", src["title"], src["url"], [loc], "IBM", "Not stated",
                               src.get("dcdate")))
    return out


def from_mathworks():
    import xml.etree.ElementTree as ET
    # Their bot filter blocks browser-looking user agents but allows plain ones.
    root = ET.fromstring(fetch("https://www.mathworks.com/company/jobs/opportunities/rss.xml",
                               ua="curl/8"))
    out = []
    for item in root.iter("item"):
        title = item.findtext("title_raw") or item.findtext("title") or ""
        if not is_design_internship(title) and not (
            item.findtext("job_type") == "Internships" and ROLE_RE.search(title)
            and not EXCLUDE_RE.search(title)
        ):
            continue
        loc = item.findtext("locationName") or ", ".join(
            x for x in (item.findtext("city"), item.findtext("country")) if x)
        out.append(job("MathWorks", title, item.findtext("link"), [loc], "MathWorks",
                       "Not stated"))
    return out


def session():
    """An opener that keeps cookies, for sites that hand out a CSRF token first."""
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def post_json(opener, url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "User-Agent": BROWSER_UA, "Content-Type": "application/json", **headers})
    with opener.open(req, timeout=60) as resp:
        return json.load(resp)


def from_google():
    found = {}
    for term in SEARCH_TERMS:
        for page in (1, 2):
            url = ("https://www.google.com/about/careers/applications/jobs/results/"
                   f"?q={urllib.parse.quote(term)}&target_level=INTERN_AND_APPRENTICE&page={page}")
            text = fetch(url).decode("utf-8", "replace")
            m = re.search(r"AF_initDataCallback\(\{key: 'ds:1', hash: '[^']*', data:(.*?), "
                          r"sideChannel: \{\}\}\);", text, re.S)
            if not m:
                raise RuntimeError("page layout changed")
            rows = json.loads(m.group(1))[0] or []
            for r in rows:
                if is_design_internship(r[1]):
                    found[r[0]] = r
            if len(rows) < 20:
                break
    out = []
    for jid, r in found.items():
        slug = re.sub(r"[^a-z0-9]+", "-", r[1].lower()).strip("-")
        posted = None
        if r[12] and isinstance(r[12], list):
            posted = datetime.datetime.fromtimestamp(r[12][0], datetime.timezone.utc).date().isoformat()
        out.append(job("Google", r[1],
                       f"https://www.google.com/about/careers/applications/jobs/results/{jid}-{slug}",
                       [l[0] for l in (r[9] or [])], "Google", "Not stated", posted))
    return out


def from_apple():
    opener = session()
    with opener.open(urllib.request.Request("https://jobs.apple.com/api/v1/CSRFToken",
                                            headers={"User-Agent": BROWSER_UA}), timeout=60) as r:
        token = r.headers["x-apple-csrf-token"]
    found = {}
    for term in SEARCH_TERMS:
        for page in (1, 2):
            data = post_json(opener, "https://jobs.apple.com/api/v1/search",
                             {"query": term, "filters": {}, "page": page, "locale": "en-us",
                              "sort": "relevance"}, {"X-Apple-CSRF-Token": token})
            results = data.get("res", {}).get("searchResults", [])
            for j in results:
                if is_design_internship(j.get("postingTitle", "")):
                    found[j["id"]] = j
    return [
        job("Apple", j["postingTitle"],
            f"https://jobs.apple.com/en-us/details/{jid}/{j.get('transformedPostingTitle', '')}",
            [l.get("name", "") + ", " + l.get("countryName", "") for l in j.get("locations", [])],
            "Apple", "Not stated", (j.get("postDateInGMT") or "")[:10] or None)
        for jid, j in found.items()
    ]


# Meta changes this ID when they redeploy their site. If Meta starts failing, open
# metacareers.com/jobsearch, find "CareersJobSearchResultsDataQuery" in the page's
# scripts and copy the new doc_id here.
META_DOC_ID = "27506805582236862"


def from_meta():
    opener = session()
    headers = {"User-Agent": BROWSER_UA, "Accept": "text/html,application/xhtml+xml",
               "Accept-Language": "en-US,en;q=0.9", "sec-fetch-mode": "navigate",
               "sec-fetch-site": "none", "sec-fetch-dest": "document"}
    with opener.open(urllib.request.Request("https://www.metacareers.com/jobsearch/?q=intern",
                                            headers=headers), timeout=60) as r:
        lsd = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', r.read().decode()).group(1)
    found = {}
    for term in SEARCH_TERMS:
        variables = {"search_input": {
            "q": term, "divisions": [], "offices": [], "roles": [], "leadership_levels": [],
            "saved_jobs": [], "saved_searches": [], "sub_teams": [], "teams": [],
            "is_leadership": False, "is_remote_only": False, "sort_by_new": False,
            "results_per_page": None}, "isLoggedIn": False, "viewasUserID": None}
        form = urllib.parse.urlencode({
            "av": "0", "__user": "0", "__a": "1", "lsd": lsd,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "CareersJobSearchResultsDataQuery",
            "doc_id": META_DOC_ID, "server_timestamps": "true",
            "variables": json.dumps(variables)}).encode()
        req = urllib.request.Request("https://www.metacareers.com/graphql", data=form, headers={
            "User-Agent": BROWSER_UA, "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "en-US,en;q=0.9",
            "x-fb-lsd": lsd, "x-fb-friendly-name": "CareersJobSearchResultsDataQuery",
            "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors",
            "Origin": "https://www.metacareers.com",
            "Referer": "https://www.metacareers.com/jobsearch/"})
        with opener.open(req, timeout=60) as r:
            body = r.read().decode()
        data = json.loads(body.replace("for (;;);", "", 1))["data"]["job_search_with_featured_jobs"]
        for j in data.get("all_jobs", []) + data.get("featured_jobs", []):
            if is_design_internship(j.get("title", "")):
                found[j["id"]] = j
    return [job("Meta", j["title"], f"https://www.metacareers.com/jobs/{jid}",
                j.get("locations", []), "Meta", "Not stated")
            for jid, j in found.items()]


def from_bytedance():
    """ByteDance's own global careers site."""
    opener = session()
    post_json(opener, "https://jobs.bytedance.com/api/v1/csrf/token", {"portal_entrance": 1}, {})
    jar = next(h.cookiejar for h in opener.handlers
               if isinstance(h, urllib.request.HTTPCookieProcessor))
    token = next(urllib.parse.unquote(c.value) for c in jar if c.name == "atsx-csrf-token")
    searches = [("en", t) for t in SEARCH_TERMS]
    found = {}
    for path, term in searches:
        data = post_json(opener, "https://jobs.bytedance.com/api/v1/search/job/posts", {
            "keyword": term, "limit": 50, "offset": 0, "job_category_id_list": [],
            "location_code_list": [], "subject_id_list": [], "recruitment_id_list": [],
            "portal_type": 3, "job_function_id_list": [], "portal_entrance": 1,
        }, {"x-csrf-token": token, "website-path": path, "portal-channel": "office",
            "portal-platform": "pc"})
        for j in (data.get("data") or {}).get("job_post_list", []):
            is_intern = (j.get("recruit_type") or {}).get("en_name") == "Intern"
            if is_design_internship(j["title"]) or (is_intern and is_design_role(j["title"])):
                found[j["id"]] = (path, j)
    out = []
    for jid, (path, j) in found.items():
        cities = [c.get("en_name", "") for c in j.get("city_list") or []] or [
            (j.get("city_info") or {}).get("en_name", "")]
        section = "campus/position" if path == "campus" else "experienced/position"
        posted = None
        if j.get("publish_time"):
            posted = datetime.datetime.fromtimestamp(j["publish_time"] / 1000,
                                                     datetime.timezone.utc).date().isoformat()
        out.append(job("ByteDance", j["title"],
                       f"https://jobs.bytedance.com/{section}/{jid}/detail", cities,
                       "ByteDance", "Not stated", posted))
    return out


def from_tiktok():
    found = {}
    for term in ["design", "UX", "research"]:
        data = fetch_json("https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts",
                          {"recruitment_id_list": ["202"], "job_category_id_list": [],
                           "subject_id_list": [], "location_code_list": [], "keyword": term,
                           "limit": 50, "offset": 0}, headers={"website-path": "tiktok"})
        for j in (data.get("data") or {}).get("job_post_list", []):
            if is_design_role(j["title"]):  # everything here is already an internship
                found[j["id"]] = j
    return [job("TikTok", j["title"], f"https://lifeattiktok.com/search/{jid}",
                [(j.get("city_info") or {}).get("en_name", "")], "TikTok", "Not stated")
            for jid, j in found.items()]


def from_jibe(site):
    """Careers sites built on Jibe/iCIMS (DocuSign, GitHub)."""
    found = {}
    for term in SEARCH_TERMS:
        data = fetch_json(f"{site['base']}/api/jobs?"
                          + urllib.parse.urlencode({"keywords": term, "page": 1, "limit": 50}))
        for item in data.get("jobs", []):
            j = item.get("data", {})
            if is_design_internship(j.get("title", "")):
                found[j["req_id"]] = j
    return [job(site["company"], j["title"],
                (j.get("meta_data") or {}).get("canonical_url") or j.get("apply_url"),
                [j.get("full_location", "")], site["company"],
                sponsorship_from_text(strip_html(j.get("description"))),
                (j.get("posted_date") or "")[:10] or None)
            for j in found.values()]


def from_microsoft():
    found = {}
    for term in SEARCH_TERMS:
        for start in (0, 10, 20):
            data = fetch_json("https://apply.careers.microsoft.com/api/pcsx/search?"
                              + urllib.parse.urlencode({"domain": "microsoft.com",
                                                        "query": term, "start": start}))
            positions = (data.get("data") or {}).get("positions", [])
            time.sleep(1)  # Microsoft rate-limits quick bursts
            for p in positions:
                if is_design_internship(p.get("name", "")):
                    found[p["id"]] = p
            if len(positions) < 10:
                break
    out = []
    for p in found.values():
        posted = None
        if p.get("postedTs"):
            posted = datetime.datetime.fromtimestamp(p["postedTs"], datetime.timezone.utc).date().isoformat()
        out.append(job("Microsoft", p["name"],
                       "https://apply.careers.microsoft.com" + p["positionUrl"],
                       p.get("locations", []), "Microsoft", "Not stated", posted))
    return out


def from_amazon():
    found = {}
    for term in SEARCH_TERMS:
        data = fetch_json("https://www.amazon.jobs/en/search.json?" + urllib.parse.urlencode(
            {"base_query": term, "offset": 0, "result_limit": 100, "sort": "relevant"}))
        for j in data.get("jobs", []):
            if is_design_internship(j.get("title", "")):
                found[j["id_icims"]] = j
    out = []
    for j in found.values():
        try:
            posted = datetime.datetime.strptime(j["posted_date"], "%B %d, %Y").date().isoformat()
        except (KeyError, ValueError):
            posted = None
        text = " ".join([j.get("basic_qualifications", ""), j.get("preferred_qualifications", ""),
                         j.get("description", "")])
        out.append(job("Amazon", j["title"], "https://www.amazon.jobs" + j["job_path"],
                       [j.get("normalized_location") or j.get("location", "")], "Amazon",
                       sponsorship_from_text(strip_html(text)), posted))
    return out


# Walmart's site uses a query ID from its front-end code; if Walmart starts failing,
# it has probably changed (search their _app-*.js for "JobSearchQuery").
WALMART_QUERY_ID = "7f8023e8-44dc-4292-aa8b-2987b977b67a"


def from_walmart():
    found = {}
    for term in SEARCH_TERMS:
        data = fetch_json("https://careers.walmart.com/api/graphql", {
            "queryId": WALMART_QUERY_ID,
            "variables": {"jobSearchRequest": {
                "searchString": term, "isTitleSearch": True,
                "population": ["WALMART_EXT_CAMPUS_US", "WALMART_EXT_FIELD_US"],
                "from": 0, "size": 50}}})
        for j in data["data"]["jobSearch"]["searchResults"]:
            if is_design_internship(j.get("jobTitle", "")):
                found[j.get(site.get("id_field", "jobId"))] = j
    return [job("Walmart", j["jobTitle"], f"https://careers.walmart.com/us/en/jobs/{jid}",
                [l.get("storeName", "") for l in j.get("location") or []] or ["United States"],
                "Walmart", "Not stated")
            for jid, j in found.items()]


def from_foxconn():
    """Foxconn Industrial Internet's US job board (JazzHR XML feed)."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(fetch("https://app.jazz.co/feeds/export/jobs/foxconnggroup"))
    out = []
    for j in root.iter("job"):
        title = j.findtext("title") or ""
        if is_design_internship(title):
            loc = ", ".join(x for x in (j.findtext("city"), j.findtext("state"),
                                        j.findtext("country")) if x)
            out.append(job("Foxconn (FII)", title, j.findtext("url"), [loc], "Foxconn",
                           sponsorship_from_text(strip_html(j.findtext("description")))))
    return out


def from_successfactors(site):
    """SAP SuccessFactors career sites (TSMC overseas, KPMG Singapore, Deloitte SEA, EY). HTML."""
    base = re.match(r"https://[^/]+", site["search"]).group(0)
    out = {}
    for term in SEARCH_TERMS:
        for where in site.get("locations", [None]):
            params = {"q": term, "startrow": 0}
            if where:
                params["locationsearch"] = where
            page = fetch(site["search"] + "?" + urllib.parse.urlencode(params),
                         headers={"Accept": "text/html"}).decode("utf-8", "replace")
            for row in re.findall(r'<tr class="data-row".*?</tr>', page, re.S):
                link = re.search(r'class="jobTitle-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                                 row, re.S)
                if not link:
                    continue
                title = html.unescape(strip_html(link.group(2))).strip()
                if not is_design_internship(title):
                    continue
                loc = re.search(r'class="jobLocation"[^>]*>(.*?)</span>', row, re.S)
                loc = html.unescape(strip_html(loc.group(1))).strip() if loc else ""
                out[link.group(1)] = job(site["company"], title, base + link.group(1),
                                         [loc or site.get("location") or where or ""],
                                         site["company"], "Not stated")
    return list(out.values())


def html_rows(url, row_re, headers=None):
    return re.findall(row_re, fetch(url, headers={"Accept": "text/html", **(headers or {})})
                      .decode("utf-8", "replace"), re.S)


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(strip_html(fragment))).strip()


def from_deloitte_us():
    out = {}
    for term in SEARCH_TERMS:
        url = ("https://apply.deloitte.com/en_US/careers/SearchJobs/"
               f"{urllib.parse.quote(term)}?listFilterMode=1&jobRecordsPerPage=50&sort=relevancy")
        for row in html_rows(url, r'<article class="article--result.*?</article>'):
            link = re.search(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', row, re.S)
            if not link or not is_design_internship(text_of(link.group(2))):
                continue
            # Subtitle reads "Deloitte US | Deloitte Tax LLP | <location>".
            sub = re.search(r'article__header__text__subtitle[^>]*>(.*?)</div>', row, re.S)
            spans = re.findall(r"<span[^>]*>(.*?)</span>", sub.group(1), re.S) if sub else []
            loc = text_of(spans[-1]) if spans else ""
            if loc.lower() in ("", "multiple locations"):
                loc += ", United States"
            out[link.group(1)] = job("Deloitte", text_of(link.group(2)), link.group(1),
                                     [loc], "Deloitte", "Not stated")
    return list(out.values())


def from_kpmg_us():
    out = {}
    for term in SEARCH_TERMS:
        url = "https://www.kpmguscareers.com/job-search/?" + urllib.parse.urlencode({"keyword": term})
        for href, inner in html_rows(url, r'<a[^>]*href="(/jobdetail/\?jobId=[^"]+)"[^>]*>(.*?)</a>'):
            title_m = re.search(r'class="[^"]*h4[^"]*"[^>]*>(.*?)<', inner, re.S)
            title = text_of(title_m.group(1) if title_m else inner)
            if not is_design_internship(title):
                continue
            # Titles look like "Tax Intern | Tampa Winter 2027".
            city = title.split("|", 1)[1] if "|" in title else ""
            out[href] = job("KPMG", title, "https://www.kpmguscareers.com" + html.unescape(href),
                            [re.sub(r"(Summer|Winter|Fall|Spring)?\s*20\d\d", "", city).strip()
                             + ", United States"], "KPMG", "Not stated")
    return list(out.values())


def from_fred_hutch():
    out = []
    url = ("https://careers-fhcrc.icims.com/jobs/search?ss=1&in_iframe=1&"
           + urllib.parse.urlencode({"searchKeyword": "intern"}))
    for card in html_rows(url, r'<li class="[^"]*iCIMS_JobCardItem.*?</li>'):
        link = re.search(r'<a href="([^"]+)" class="iCIMS_Anchor".*?<h3[^>]*>(.*?)</h3>', card, re.S)
        if link and is_design_internship(text_of(link.group(2))):
            loc = re.search(r'Location.*?<dd[^>]*>(.*?)</dd>', card, re.S)
            out.append(job("Fred Hutch", text_of(link.group(2)), html.unescape(link.group(1)),
                           [text_of(loc.group(1)) if loc else "Seattle, WA"], "Fred Hutch",
                           "Not stated"))
    return out


def from_neogov(site):
    """City governments on governmentjobs.com: one XML feed of every open job."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(fetch(
        f"https://www.governmentjobs.com/SearchEngine/JobsFeed?agency={site['agency']}",
        headers={"Accept": "application/xml"}))
    out = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        if not is_design_internship(title):
            continue
        loc = next((el.text for el in item if el.tag.endswith("location")), "") or site["location"]
        posted = None
        try:
            posted = datetime.datetime.strptime(item.findtext("pubDate")[:16],
                                                "%a, %d %b %Y").date().isoformat()
        except (TypeError, ValueError):
            pass
        out.append(job(site["company"], title, item.findtext("link"), [loc], "NEOGOV",
                       "Not stated", posted))
    return out


def from_sound_transit():
    base = ("https://recruiting.ultipro.com/SOU1036SOUND/JobBoard/"
            "dcc5dbea-875e-4cd1-bfd2-8e046cecc54f")
    found = {}
    for term in SEARCH_TERMS:
        data = fetch_json(f"{base}/JobBoardView/LoadSearchResults", {
            "opportunitySearch": {"Top": 50, "Skip": 0, "QueryString": term, "Filters": [],
                                  "OrderBy": [{"Value": "postedDateDesc", "PropertyName":
                                               "PostedDate", "Ascending": False}]},
            "matchCriteria": {"PreferredJobs": [], "Educations": [],
                              "LicenseAndCertifications": [], "Skills": [],
                              "hasNoLicenses": False, "SkippedSkills": []}})
        for o in data.get("opportunities", []):
            if is_design_internship(o.get("Title", "")):
                found[o["Id"]] = o
    return [job("Sound Transit", o["Title"], f"{base}/OpportunityDetail?opportunityId={oid}",
                [", ".join(x for x in ((l.get("Address") or {}).get("City"),
                                       ((l.get("Address") or {}).get("State") or {}).get("Code"))
                           if x) for l in o.get("Locations") or []] or ["Seattle, WA"],
                "Sound Transit", "Not stated", (o.get("PostedDate") or "")[:10] or None)
            for oid, o in found.items()]


def from_allen_institute():
    data = fetch_json("https://careers-api.clearcompany.com/v1/f724f829-c8a2-8b32-a83b-2a479b88b77f")
    return [job("Allen Institute", j["positionTitle"], j.get("applyLink"),
                [j.get("location") or "Seattle, WA"], "Allen Institute", "Not stated",
                (j.get("postedDate") or "")[:10] or None)
            for j in data.get("results", []) if is_design_internship(j.get("positionTitle", ""))]


def from_accenture():
    out = {}
    countries = [("USA", "us-en"), ("Singapore", "sg-en"), ("Hong Kong", "hk-en"),
                 ("United Kingdom", "gb-en")]
    for term in SEARCH_TERMS:
        for country, site in countries:
            fields = {"startIndex": "0", "maxResultSize": "50", "jobKeyword": term,
                      "jobCountry": country, "jobLanguage": "en", "countrySite": site,
                      "sortBy": "0", "searchType": "vectorSearch", "totalHits": "true",
                      "jobFilters": "[]"}
            boundary = "----jobdigest"
            body = "".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"'
                           f"\r\n\r\n{v}\r\n" for k, v in fields.items())
            body += f"--{boundary}--\r\n"
            req = urllib.request.Request(
                "https://www.accenture.com/api/accenture/elastic/findjobs",
                data=body.encode(), headers={
                    "User-Agent": BROWSER_UA, "Accept": "application/json",
                    "Content-Type": f"multipart/form-data; boundary={boundary}"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
            for j in data.get("data", []):
                if is_design_internship(j.get("title", "")):
                    out[j.get("jobDetailUrl")] = job(
                        "Accenture", j["title"], (j.get("jobDetailUrl") or "").replace("{0}", site),
                        j.get("location") or [country], "Accenture", "Not stated",
                        (j.get("updateDate") or "")[:10] or None)
    return list(out.values())


def from_mckinsey():
    found = {}
    for term in SEARCH_TERMS:
        data = fetch_json("https://gateway.mckinsey.com/apigw-x0cceuow60/v1/api/jobs/search?"
                          + urllib.parse.urlencode({"pageSize": 50, "start": 1, "lang": "en",
                                                    "q": term}))
        for j in data.get("docs") or []:
            if is_design_internship(j.get("title", "")):
                found[j["friendlyURL"]] = j
    return [job("McKinsey", j["title"],
                f"https://www.mckinsey.com/careers/search-jobs/jobs/{slug}",
                (j.get("cities") or []) + (j.get("countries") or []), "McKinsey", "Not stated")
            for slug, j in found.items()]


def from_moka(site):
    """Moka job sites (PwC Hong Kong, KPMG China/HK). Replies are AES-encrypted."""
    import base64
    import subprocess
    out = {}
    for term in SEARCH_TERMS + ["实习", "intern"]:
        reply = fetch_json("https://app.mokahr.com/api/outer/ats-apply/website/jobs/v2",
                           {"orgId": site["org"], "siteId": site["site"], "limit": 50,
                            "offset": 0, "keyword": term})
        key = reply["necromancer"].encode().hex()
        plain = subprocess.run(
            ["openssl", "enc", "-d", "-aes-128-cbc", "-K", key, "-iv", key, "-a", "-A"],
            input=reply["data"].encode(), capture_output=True, check=True).stdout
        # The first block decrypts to junk; the JSON is intact from "data": onward.
        text = plain[16:].decode("utf-8", "replace")
        jobs = json.loads("{" + text[text.find('"data":'):])["data"].get("jobs", [])
        for j in jobs:
            title = j.get("title", "")
            if is_design_role(title) and (INTERN_RE.search(title) or site.get("all_intern")):
                locs = [l.get("address", "") for l in j.get("locations") or []]
                out[j["id"]] = job(site["company"], title,
                                   f"https://app.mokahr.com/campus-recruitment/{site['org']}/"
                                   f"{site['site']}#/job/{j['id']}",
                                   locs or [site["location"]], site["company"], "Not stated",
                                   (j.get("openedAt") or "")[:10] or None)
    return list(out.values())


def from_atlassian():
    seen, out = set(), []
    for j in fetch_json("https://www.atlassian.com/endpoint/careers/listings"):
        if j["id"] in seen or not is_design_internship(j.get("title", "")):
            continue
        seen.add(j["id"])
        post = j.get("portalJobPost") or {}
        out.append(job("Atlassian", j["title"],
                       f"https://www.atlassian.com/company/careers/details/{j['id']}",
                       j.get("locations", []), "Atlassian", "Not stated",
                       (post.get("updatedDate") or "")[:10] or None))
    return out


def from_ycombinator():
    """YC startups' public job pages. (The full list at workatastartup.com needs a login.)"""
    found = {}
    for path in ("internships", "jobs/role/design"):
        page = fetch(f"https://www.ycombinator.com/{path}",
                     headers={"Accept": "text/html"}).decode("utf-8", "replace")
        m = re.search(r'data-page="([^"]+)"', page)
        if not m:
            raise RuntimeError("page layout changed")
        for j in json.loads(html.unescape(m.group(1)))["props"].get("jobPostings", []):
            intern = j.get("type") in ("Intern", "Internship") or INTERN_RE.search(j["title"])
            design = j.get("role") == "design" or is_design_role(j["title"])
            if intern and design and not EXCLUDE_RE.search(j["title"]):
                found[j["id"]] = j
    visa = {"US citizen/visa only": "No sponsorship", "Will sponsor": "Sponsors"}
    return [job(f"{j['companyName']} (YC {j.get('companyBatchName', '')})".replace(" (YC )", ""),
                j["title"], "https://www.ycombinator.com" + j["url"],
                re.split(r"\s*/\s*", j.get("location", "")), "Y Combinator",
                visa.get(j.get("visa"), "Not stated"))
            for j in found.values()]


def from_isite(site):
    """Foxconn group's Taiwan recruiting sites (Hon Hai, FIT). Titles are in Chinese."""
    found = {}
    for term in config.TAIWAN_TERMS:
        for j in fetch_json(f"{site['api']}/JobVacancies?" + urllib.parse.urlencode({"keywords": term})):
            title = j.get("job_name") or ""
            intern = "INTERN" in (j.get("job_type") or "") or INTERN_RE.search(title)
            if intern and is_design_role(title):
                found[j["id"]] = j
    return [job(site["company"], j["job_name"], f"{site['web']}/main/jobsearch/detail?id={jid}",
                [j.get("loc_name") or "台灣"], site["company"], "Not stated")
            for jid, j in found.items()]


# ---------- job-alert emails (Handshake, ...) ----------

def unwrap_link(url):
    """Undo UW's urldefense.com link wrapping so links go straight to the site."""
    url = html.unescape(url)
    m = re.match(r"https://urldefense\.com/v3/__(.+?)__;", url)
    return m.group(1) if m else url


def parse_handshake(body):
    """Handshake round-ups and single-job notifications share one card shape:
    <a><span>company</span><span>title</span><span>meta</span></a>, where meta reads like "$20–30/hr • Internship • Vienna, VA (Hybrid)"."""
    cards = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*<span[^>]*>([^<]*)</span>\s*'
                       r'<span[^>]*>([^<]*)</span>\s*<span[^>]*>([^<]*)</span>\s*</a>', body)
    out = []
    for href, company, title, meta in cards:
        company, title, meta = text_of(company), text_of(title), text_of(meta)
        parts = [p.strip() for p in meta.split("•")]
        intern = "Internship" in parts or INTERN_RE.search(title)
        if not (intern and is_design_role(title)):
            continue
        loc = re.sub(r"\s*\((Onsite|Hybrid|Remote)\)|\s*\+\d+$", "", parts[-1]).strip()
        if "(Remote)" in parts[-1]:
            loc += " / Remote"
        out.append(job(company, title, unwrap_link(href), [loc], "Handshake", "Not stated"))
    return out


def parse_trueup(body):
    """Lenny's Jobs (TrueUp) weekly and daily alerts. Each card: title linking to the
    company's own job page, then the company, then an uppercase location line."""
    out = []
    for card in body.split("font-weight:600;font-size:16px;margin-bottom:6px;")[1:]:
        link = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
        company = re.search(r'<a href="https://www\.trueup\.io/co/[^"]*"[^>]*>(.*?)</a>', card, re.S)
        loc = re.search(r'color:#737373;margin-bottom:10px;">(.*?)</div>', card, re.S)
        if not (link and company):
            continue
        title = text_of(link.group(2))
        if not is_design_internship(title):
            continue
        out.append(job(text_of(company.group(1)), title, html.unescape(link.group(1)),
                       [text_of(loc.group(1)) if loc else ""], "Lenny's Jobs", "Not stated"))
    return out


def parse_jobright(body):
    """Jobright alerts (single-job and round-ups share one card layout)."""
    out = []
    for card in body.split('id="job-company-name"')[1:]:
        company = re.search(r">\s*([^<]+?)\s*</p>", card)
        link = re.search(r'id="job-title"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
        if not (company and link):
            continue
        title = text_of(link.group(2))
        if not is_design_internship(title):
            continue
        # Tags hold location plus extras like "$25/hr - $30/hr" or "5+ referrals".
        tags = [text_of(t) for t in re.findall(r'id="job-tag"[^>]*>(.*?)</p>', card, re.S)]
        locs = [t for t in tags if not re.match(r"\$|\d+\+ referrals", t)]
        job_id = re.search(r"jobright\.ai/jobs/info/([0-9a-f]+)", link.group(1))
        url = (f"https://jobright.ai/jobs/info/{job_id.group(1)}" if job_id
               else html.unescape(link.group(1)))
        out.append(job(text_of(company.group(1)), title, url, locs, "Jobright", "Not stated"))
    return out


# Which parser handles alerts from which sender (matched anywhere in the email,
# so alerts forwarded from another inbox work too).
ALERT_PARSERS = {"joinhandshake.com": parse_handshake, "jobright.ai": parse_jobright,
                 "trueup.io": parse_trueup}

# How far back to read alert emails. The first run looks back further so the first
# digest includes everything your alerts have already sent you.
ALERT_LOOKBACK = os.environ.get("ALERT_LOOKBACK") or "3d"


def clean_lookback(value):
    """Turn whatever was typed in the Run-workflow box into e.g. "60d". Handles
    full-width characters from Chinese/Japanese keyboards (６０ｄ), stray quotes,
    backticks and spaces; falls back to 3 days if it can't make sense of it."""
    value = unicodedata.normalize("NFKC", value or "").strip().strip("`'\" ").lower()
    m = re.fullmatch(r"(\d+)\s*(d|m|y|days?)?", value)
    return f"{m.group(1)}{(m.group(2) or 'd')[0]}" if m else "3d"


def from_email_alerts():
    """Read recent job-alert emails from the inbox (read-only; nothing is changed)."""
    import email
    import email.policy
    import email.utils
    import zoneinfo
    import imaplib
    user = os.environ.get("ALERTS_EMAIL") or os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("ALERTS_APP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD")
    if not (user and password):
        raise RuntimeError("no inbox login set (GMAIL_ADDRESS/ALERTS_EMAIL secrets)")
    out = []
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(user, password)
        # "All Mail" has a translated name in non-English Gmail; find it by its \All flag.
        _, folders = imap.list()
        all_mail = next((f.decode().rsplit(' "/" ', 1)[-1] for f in folders
                         if "\\All" in f.decode()), "INBOX")
        if not all_mail.startswith('"'):
            all_mail = f'"{all_mail}"'
        if imap.select(all_mail, readonly=True)[0] != "OK":
            raise RuntimeError("couldn't open the mailbox")
        senders = " OR ".join(ALERT_PARSERS)  # no inner quotes: IMAP can't nest them
        query = f"newer_than:{clean_lookback(ALERT_LOOKBACK)} ({senders})"
        try:
            _, ids = imap.search(None, "X-GM-RAW", f'"{query}"')
        except imaplib.IMAP4.error as exc:
            raise RuntimeError(f"{exc} (search was: {query!r})") from None
        for msg_id in ids[0].split():
            _, data = imap.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1], policy=email.policy.default)
            part = msg.get_body(preferencelist=("html",))
            if part is None:
                continue
            body = part.get_content()
            sender = str(msg["From"])
            # Match on the sender first; only fall back to the body for forwarded alerts.
            matches = [p for d, p in ALERT_PARSERS.items() if d in sender] or [
                p for d, p in ALERT_PARSERS.items() if d in body]
            # Alerts don't say when a job was posted, so remember when the email came.
            received = email.utils.parsedate_to_datetime(msg["Date"]).astimezone(
                zoneinfo.ZoneInfo("America/Los_Angeles")).date().isoformat()
            for parser in matches[:1]:
                for j in parser(body):
                    j["received"] = received
                    out.append(j)
    return out


def from_simplify():
    mapping = {
        "Offers Sponsorship": "Sponsors",
        "Does Not Offer Sponsorship": "No sponsorship",
        "U.S. Citizenship is Required": "No sponsorship",
    }
    out = []
    for j in fetch_json(config.SIMPLIFY_URL):
        if not (j.get("active") and j.get("is_visible")):
            continue
        # Simplify titles often omit "intern" because the whole list is internships.
        title = j["title"]
        if not is_design_role(title):
            continue
        posted = datetime.datetime.fromtimestamp(j["date_posted"], datetime.timezone.utc).date().isoformat()
        out.append(job(j["company_name"], title, j["url"], j.get("locations", []), "Simplify",
                       mapping.get(j.get("sponsorship"), "Not stated"), posted))
    return out


def collect():
    tasks = [(f"greenhouse:{s}", from_greenhouse, s) for s in config.GREENHOUSE]
    tasks += [(f"lever:{s}", from_lever, s) for s in config.LEVER]
    tasks += [(f"ashby:{s}", from_ashby, s) for s in config.ASHBY]
    tasks += [(f"smartrecruiters:{s}", from_smartrecruiters, s) for s in config.SMARTRECRUITERS]
    tasks += [(f"workday:{s['company']}", from_workday, s) for s in config.WORKDAY]
    tasks += [(f"oracle:{s['company']}", from_oracle, s) for s in config.ORACLE]
    tasks += [(f"phenom:{s['company']}", from_phenom, s) for s in config.PHENOM]
    tasks += [(name, lambda fn: fn(), fn) for name, fn in [
        ("ibm", from_ibm), ("mathworks", from_mathworks), ("google", from_google),
        ("apple", from_apple), ("meta", from_meta), ("bytedance", from_bytedance),
        ("tiktok", from_tiktok), ("atlassian", from_atlassian), ("microsoft", from_microsoft),
        ("amazon", from_amazon), ("walmart", from_walmart), ("foxconn", from_foxconn),
        ("ycombinator", from_ycombinator), ("deloitte-us", from_deloitte_us),
        ("kpmg-us", from_kpmg_us), ("fred-hutch", from_fred_hutch),
        ("sound-transit", from_sound_transit), ("allen-institute", from_allen_institute),
        ("accenture", from_accenture), ("mckinsey", from_mckinsey),
        ("email alerts", from_email_alerts),
    ]]
    tasks += [(f"successfactors:{s['company']}", from_successfactors, s)
              for s in config.SUCCESSFACTORS]
    tasks += [(f"neogov:{s['company']}", from_neogov, s) for s in config.NEOGOV]
    tasks += [(f"moka:{s['company']}", from_moka, s) for s in config.MOKA]
    tasks += [(f"isite:{s['company']}", from_isite, s) for s in config.ISITE]
    tasks += [(f"jibe:{s['company']}", from_jibe, s) for s in config.JIBE]
    tasks.append(("simplify", lambda _: from_simplify(), None))

    jobs, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(fn, arg): name for name, fn, arg in tasks}
        for fut in concurrent.futures.as_completed(futures):
            try:
                jobs.extend(fut.result())
            except Exception as exc:  # one broken board shouldn't kill the digest
                errors.append(f"{futures[fut]}: {exc}")
    return jobs, errors


# ---------- de-duplication ----------

def norm(text):
    text = text.lower()
    text = re.sub(r"\b(inc|llc|ltd|corp|co|technologies|labs)\b\.?", "", text)
    text = re.sub(r"\b20\d\d\b", "", text)
    text = re.sub(r"\binternship\b", "intern", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def merge(jobs):
    """One entry per company + title, however many boards list it."""
    merged = {}
    for j in jobs:
        regions = regions_for(j["locations"])
        if not regions:
            continue
        key = f"{norm(j['company'])}|{norm(j['title'])}"
        m = merged.setdefault(key, dict(j, key=key, regions=regions, links={}, received={}))
        m["links"].setdefault(j["source"], j["url"])
        if j.get("received"):  # earliest alert email per source
            prev = m["received"].get(j["source"])
            m["received"][j["source"]] = min(prev, j["received"]) if prev else j["received"]
        m["locations"] = sorted(set(m["locations"]) | set(j["locations"]))
        m["regions"] = [r for r in REGION_ORDER if r in set(m["regions"]) | set(regions)]
        if m["sponsorship"] == "Not stated":
            m["sponsorship"] = j["sponsorship"]
        if j["posted"] and (not m["posted"] or j["posted"] < m["posted"]):
            m["posted"] = j["posted"]
    return list(merged.values())


# ---------- email ----------

SPONSOR_STYLE = {
    "Sponsors": "background:#e6f4ea;color:#137333",
    "No sponsorship": "background:#fce8e6;color:#a50e0e",
    "Not stated": "background:#f1f3f4;color:#5f6368",
}


def short_date(iso):
    try:
        d = datetime.date.fromisoformat(iso[:10])
    except ValueError:
        return html.escape(iso)  # some site sent an odd date; show it as-is
    return f"{d:%b} {d.day}"


def when(j):
    """ "posted Sep 18 · " from the job site, or "received via Jobright on Sep 18 · "
    when the job only came from alert emails, which don't give a posting date."""
    if j["posted"]:
        return f"posted {short_date(j['posted'])} · "
    if j.get("received"):
        src, day = min(j["received"].items(), key=lambda kv: kv[1])
        return f"received via {html.escape(src)} on {short_date(day)} · "
    return ""


def render(new_jobs, total_open, first_run, errors):
    today = datetime.date.today().strftime("%a %b %d, %Y")
    intro = (
        f"First digest: all {len(new_jobs)} design internships open right now. "
        "From tomorrow you'll only get new ones."
        if first_run
        else f"{len(new_jobs)} new since the last email · {total_open} open in total."
    )
    rows_by_region = {}
    newest = lambda j: j["posted"] or max(j["received"].values(), default="")
    for j in sorted(new_jobs, key=lambda j: (newest(j), j["company"]), reverse=True):
        rows_by_region.setdefault(j["regions"][0], []).append(j)

    parts = [
        '<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
        'max-width:760px;color:#202124">',
        f'<h2 style="margin:0 0 4px">Design internships · {today}</h2>',
        f'<p style="margin:0 0 20px;color:#5f6368">{html.escape(intro)}</p>',
    ]
    for region in REGION_ORDER:
        rows = rows_by_region.get(region)
        if not rows:
            continue
        parts.append(f'<h3 style="margin:24px 0 8px">{region} ({len(rows)})</h3>')
        for j in rows:
            primary = next(iter(j["links"].values()))
            others = " · ".join(
                f'<a href="{html.escape(u)}" style="color:#5f6368">{html.escape(s)}</a>'
                for s, u in j["links"].items()
            )
            locs = ", ".join(j["locations"][:4]) + (" +more" if len(j["locations"]) > 4 else "")
            parts.append(
                '<div style="padding:10px 0;border-bottom:1px solid #eee">'
                f'<a href="{html.escape(primary)}" style="font-weight:600;color:#1a73e8;'
                f'text-decoration:none">{html.escape(j["title"])}</a><br>'
                f'<span>{html.escape(j["company"])}</span> · '
                f'<span style="color:#5f6368">{html.escape(locs)}</span><br>'
                f'<span style="font-size:12px;padding:1px 6px;border-radius:4px;'
                f'{SPONSOR_STYLE[j["sponsorship"]]}">{j["sponsorship"]}</span> '
                f'<span style="font-size:12px;color:#5f6368">'
                f'{when(j)}via {others}</span>'
                "</div>"
            )
    if not new_jobs:
        parts.append("<p>Nothing new today.</p>")
    if errors:
        parts.append(
            '<p style="margin-top:24px;font-size:12px;color:#999">Couldn\'t read: '
            + html.escape("; ".join(errors)) + "</p>"
        )
    parts.append("</div>")
    return "".join(parts)


def send(subject, body):
    sender = os.environ["GMAIL_ADDRESS"]
    to = os.environ.get("TO_EMAIL") or sender
    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, sender, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, os.environ["GMAIL_APP_PASSWORD"])
        smtp.send_message(msg)


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="write digest.html instead of emailing; don't update seen.json")
    args = parser.parse_args()

    global ALERT_LOOKBACK
    seen = json.loads(SEEN_FILE.read_text()) if SEEN_FILE.exists() else {}
    first_run = not seen
    if first_run and not os.environ.get("ALERT_LOOKBACK"):
        ALERT_LOOKBACK = "60d"  # include every alert already in the inbox
    raw, errors = collect()
    jobs = merge(raw)
    new_jobs = [j for j in jobs if j["key"] not in seen]

    body = render(new_jobs, len(jobs), first_run, errors)
    subject = f"🎨 {len(new_jobs)} {'open' if first_run else 'new'} design internships"
    print(f"{len(raw)} listings → {len(jobs)} unique · {len(new_jobs)} new · {len(errors)} errors")
    for e in errors:
        print("  error:", e, file=sys.stderr)

    if args.dry_run:
        (ROOT / "digest.html").write_text(body)
        print("Wrote digest.html")
        return

    # Scheduled runs stay quiet on empty days; manual runs always report back.
    if new_jobs or first_run or os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        send(subject, body)
    today = datetime.date.today().isoformat()
    for j in new_jobs:
        seen[j["key"]] = today
    SEEN_FILE.write_text(json.dumps(seen, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
