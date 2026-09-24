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
    # Chinese titles (ByteDance Beijing): interaction/UX/visual/product design, user research
    r"交互设计", r"用户体验", r"视觉设计", r"产品设计", r"用户研究", r"体验设计",
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
    r"实习",  # "intern" in Chinese
]

# Extra search words for ByteDance's China site, whose titles are in Chinese.
CHINESE_TERMS = ["设计实习生", "用户研究实习生", "交互设计", "用户体验"]

# Which regions to keep. Remote roles are kept when they aren't tied to another country.
REGIONS = ["US", "Singapore", "Hong Kong", "London", "Beijing"]

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
]

# SimplifyJobs' community-maintained internship list (mostly tech, US/Canada).
SIMPLIFY_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
    "dev/.github/scripts/listings.json"
)
