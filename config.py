"""Everything you might want to tweak lives here."""

# A title must match one of these (case-insensitive regex) to count as a design role.
ROLE_PATTERNS = [
    r"\bux\b",
    r"\bui\b",
    r"user experience",
    r"product design",
    r"experience design",
    r"interaction design",
    r"visual design",
    r"product builder",
    r"user research",
    r"ux research",
    r"design research",
    r"experience research",
    r"(brand|service|web|communication|creative) design",
    r"\bui ?/?ux\b",  # "UIUX", "UI/UX"
    r"design and research",
    r"^design intern",
    r"\(design\)",  # e.g. KPMG's "Digital Village (Design)"
    # Chinese titles (Taiwan / Hong Kong): UX, UI, interaction, visual, product design, user research
    r"使用者經驗", r"使用者體驗", r"使用者研究", r"介面設計", r"互動設計", r"視覺設計",
    r"產品設計", r"體驗設計", r"用戶體驗", r"用户体验", r"交互设计", r"产品设计", r"用户研究",
]

# ...and must NOT match any of these (filters out chip design, "UX Engineer", etc.).
EXCLUDE_PATTERNS = [
    r"engineer",
    r"developer",
    r"verification",
    r"hardware",
    r"mechanical",
    r"circuit",
    r"asic",
    r"\bchip\b",
    r"analog",
    r"\bic\b",
    r"rfic",
    r"physical design",
    r"digital design",
    r"mixed.signal",
    r"programmer",
]

# A title must match one of these to count as an internship.
INTERN_PATTERNS = [
    r"\bintern(ship)?s?\b", r"co-?op\b", r"\bplacement\b", r"\bsummer 20\d\d\b",
    r"summer (analyst|associate)",  # how banks like JPMorgan name internships
    r"实习", r"實習",  # "intern" in Chinese
]

# Search words for the Taiwan sites, whose titles are in Chinese.
TAIWAN_TERMS = ["設計", "實習", "UX", "UI", "使用者"]

# Which regions to keep. Remote roles are kept when they aren't tied to another country.
REGIONS = ["US", "Singapore", "Hong Kong", "London", "Taiwan"]

# Companies whose job boards are read directly. Add more any time:
# find the company's careers page; if links go to boards.greenhouse.io/<slug>,
# jobs.lever.co/<slug>, jobs.ashbyhq.com/<slug> or jobs.smartrecruiters.com/<slug>,
# add <slug> to that list.
GREENHOUSE = [
    "figma", "airbnb", "stripe", "pinterest", "dropbox", "discord", "duolingo",
    "robinhood", "instacart", "lyft", "reddit", "databricks", "coinbase", "asana",
    "squarespace", "twitch", "gitlab", "affirm", "brex", "chime", "webflow",
    "anthropic", "vercel", "airtable", "gusto", "samsara", "okta", "cloudflare",
    "datadog", "roblox", "waymo", "nextdoor", "doordashusa", "okx", "mercury",
    "scaleai", "faire", "calendly", "intercom", "mongodb", "elastic", "twilio",
    "toast", "peloton", "ideo", "sonyinteractiveentertainmentglobal", "xai", "medium",
    "coursera", "pitchbookdata", "samsungresearchamerica", "samsungsemiconductor",
    "gemini", "upstart", "thoughtworks", "hs", "sharpelectronics",
    "thealleninstitute", "stackadapt",
]
LEVER = ["spotify", "palantir", "crypto", "binance", "brooksrunning"]
ASHBY = [
    "notion", "linear", "ramp", "openai", "perplexity", "miro", "plaid", "wealthsimple",
    "patreon", "thoughtworks", "Superhuman Platform Inc", "mobbin.com",
]
# Display names for boards whose slug isn't the company name.
NAMES = {"Superhuman Platform Inc": "Superhuman (Grammarly)", "mobbin.com": "Mobbin"}
SMARTRECRUITERS = ["wise", "servicenow"]

# Big-company career sites. "facets" narrows a Workday search (IDs come from the site).
WORKDAY = [
    {"company": "Citi", "host": "citi.wd5.myworkdayjobs.com", "tenant": "citi", "site": "2"},
    {"company": "Capital One", "host": "capitalone.wd12.myworkdayjobs.com",
     "tenant": "capitalone", "site": "Capital_One",
     "facets": {"workerSubType": ["a12c70bf789e10572aab83c4780919ad"]}},
    {"company": "Chewy", "host": "chewy.wd5.myworkdayjobs.com", "tenant": "chewy",
     "site": "External"},
    {"company": "eBay", "host": "ebay.wd5.myworkdayjobs.com", "tenant": "ebay", "site": "apply"},
    {"company": "Samsung", "host": "sec.wd3.myworkdayjobs.com", "tenant": "sec",
     "site": "Samsung_Careers"},
    {"company": "Sony", "host": "sonyglobal.wd1.myworkdayjobs.com", "tenant": "sonyglobal",
     "site": "SonyGlobalCareers"},
    {"company": "NVIDIA", "host": "nvidia.wd5.myworkdayjobs.com", "tenant": "nvidia",
     "site": "NVIDIAExternalCareerSite"},
    {"company": "Adobe", "host": "adobe.wd5.myworkdayjobs.com", "tenant": "adobe",
     "site": "external_experienced"},
    {"company": "Boeing", "host": "boeing.wd1.myworkdayjobs.com", "tenant": "boeing",
     "site": "EXTERNAL_CAREERS"},
    {"company": "Salesforce", "host": "salesforce.wd12.myworkdayjobs.com",
     "tenant": "salesforce", "site": "External_Career_Site",
     "facets": {"workerSubType": ["3a910852b2c31010f48d2cefdccd0000"]}},
    {"company": "Slack", "host": "salesforce.wd12.myworkdayjobs.com", "tenant": "salesforce",
     "site": "Slack"},
    {"company": "Nordstrom", "host": "nordstrom.wd501.myworkdayjobs.com",
     "tenant": "nordstrom", "site": "nordstrom_careers"},
    {"company": "Belkin (Foxconn)", "host": "belkin.wd5.myworkdayjobs.com", "tenant": "belkin",
     "site": "Belkin_Careers"},
    {"company": "Foxconn Interconnect", "host": "belkin.wd5.myworkdayjobs.com",
     "tenant": "belkin", "site": "FIT_Careers"},
    {"company": "PwC", "host": "pwc.wd3.myworkdayjobs.com", "tenant": "pwc",
     "site": "US_Entry_Level_Careers"},
    {"company": "PwC", "host": "pwc.wd3.myworkdayjobs.com", "tenant": "pwc",
     "site": "Global_Campus_Careers"},
    {"company": "PATH", "host": "path.wd1.myworkdayjobs.com", "tenant": "path",
     "site": "External"},
    {"company": "Seattle Children's", "host": "seattlechildrens.wd5.myworkdayjobs.com",
     "tenant": "seattlechildrens", "site": "External"},
    {"company": "Expedia", "host": "expedia.wd108.myworkdayjobs.com", "tenant": "expedia",
     "site": "search"},
    {"company": "T-Mobile", "host": "tmobile.wd1.myworkdayjobs.com", "tenant": "tmobile",
     "site": "External"},
]
ORACLE = [
    {"company": "JPMorgan Chase", "host": "jpmc.fa.oraclecloud.com", "site": "CX_1001"},
    {"company": "Dell", "host": "enterpriseplatform.dell.com", "site": "CX_1001",
     "url_site": "careers"},
    {"company": "Ford", "host": "efds.fa.em5.oraclecloud.com", "site": "CX_1"},
    {"company": "Uber", "host": "iaziqy.fa.ocs.oraclecloud.com", "site": "CX_1",
     "url_site": "UberCareers"},
]
JIBE = [
    {"company": "DocuSign", "base": "https://careers.docusign.com"},
    {"company": "GitHub", "base": "https://www.github.careers"},
]
PHENOM = [
    {"company": "Honda", "base": "https://careers.honda.com"},
    {"company": "Activision", "base": "https://careers.activision.com"},
    {"company": "Blizzard", "base": "https://careers.blizzard.com"},
    {"company": "BCG", "base": "https://careers.bcg.com", "lang": "en_global",
     "country": "global", "path": "global/en", "id_field": "jobSeqNo"},
]
SUCCESSFACTORS = [
    {"company": "TSMC", "search": "https://ro.careers.tsmc.com/search/"},
    {"company": "KPMG", "search": "https://careers.kpmg.com.sg/search/", "location": "Singapore"},
    {"company": "Deloitte", "search": "https://jobs.sea.deloitte.com/search/"},
    {"company": "EY", "search": "https://careers.ey.com/ey/search/",
     "locations": ["United States", "Singapore", "Hong Kong", "London"]},
]
NEOGOV = [
    {"company": "City of Seattle", "agency": "seattle", "location": "Seattle, WA"},
    {"company": "City of Bellevue", "agency": "bellevuewa", "location": "Bellevue, WA"},
]
# Foxconn group Taiwan sites.
ISITE = [
    {"company": "Foxconn (Hon Hai)", "api": "https://recruit.foxconn.com/hh_recruit_tw_api/portal_api",
     "web": "https://recruit.foxconn.com/isite-web-tw"},
    {"company": "Foxconn Interconnect", "api": "https://recruit.one-fit.com/recruit-api/portal_api",
     "web": "https://recruit.one-fit.com/isite-web-tw"},
]
# Moka sites (Hong Kong / China). "all_intern" = the whole site is internships/graduates.
MOKA = [
    {"company": "PwC", "org": "pwc", "site": 148260, "location": "Hong Kong", "all_intern": True},
    {"company": "KPMG", "org": "kpmg", "site": 74217, "location": "Hong Kong", "all_intern": True},
]

# SimplifyJobs' community-maintained internship list (mostly tech, US/Canada).
SIMPLIFY_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
    "dev/.github/scripts/listings.json"
)
