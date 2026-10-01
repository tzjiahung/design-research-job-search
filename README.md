# Design internship digest

Three emails a day (11am, 3pm and 9pm Seattle time) with every new UX / product design /
UX research internship in the US, Singapore, Hong Kong, London and Taiwan. Each job appears
once, even when several boards list it.

**Sources:**
- ~100 companies' own job boards on Greenhouse, Lever, Ashby and SmartRecruiters (Figma, Airbnb, Stripe,
  Notion, Coinbase, Roblox, Pinterest, Duolingo, Wise, ServiceNow, ...), including hardware
  and device makers (Oura, WHOOP, Eight Sleep, Nothing, Peloton, GoPro, Skydio, Figure,
  1X, Agility Robotics, Anduril, Lucid, Zoox, Nuro, Motional, Wayve)
- Big-company sites: Google, Meta, Apple, Microsoft, Amazon/AWS, NVIDIA, Adobe, IBM,
  ByteDance/TikTok, Atlassian, Salesforce/Slack, Walmart, Boeing, Nordstrom, Expedia,
  T-Mobile, Uber, JPMorgan, Citi, Capital One, Dell, Ford, Honda, Sony, Samsung, TSMC,
  Foxconn, Garmin, Rivian, Snap, Logitech, Sonos, Bose, Dyson, DocuSign, GitHub,
  MathWorks, ...
- The SimplifyJobs and Intern Dock internship lists, and Y Combinator startups
- Job-alert emails in your inbox (Handshake, Jobright, Lenny's Jobs, LinkedIn), read without changing anything

Edit [config.py](config.py) to change roles, regions or companies. A company that can't
be read on a given day is listed at the bottom of the email instead of breaking it.

**How it works:** a GitHub Action runs [jobdigest.py](jobdigest.py) at 11am, 3pm and 9pm
Seattle time. The first email listed everything open at the time; since then each email
has only jobs you haven't been sent. If nothing is new, you still get a short "No new
design internships" email. Jobs already sent are remembered in `seen.json`, which the
Action updates on its own.

## Which jobs count

A job title has to pass three checks. The lists live in [config.py](config.py), and
capitals don't matter.

**1. A design keyword** (`ROLE_PATTERNS`)

| Keyword | Also catches | Example |
|---|---|---|
| UX | UX Designer, UX Writer, UX Researcher | UX Design Intern |
| UI, UI/UX, UIUX | | UI/UX Intern |
| user experience | | 2027 Summer Internship – User Experience |
| product design | Product Designer | Product Design Intern |
| experience design, interaction design, visual design | …Designer | Internship – Interaction Design |
| brand / service / web / communication / creative design | …Designer | Brand Design Intern |
| user research, UX research, design research, experience research | User Researcher | User Research Intern |
| design and research | | Graduate Intern, Design and Research |
| HCI, human-computer interaction, human factors, human-centered design | | Human Factors Intern |
| information architecture / architect, design technologist, design system | | Design System Design Intern |
| product builder, "(Design)" | | Digital Village (Design) |
| Chinese: 使用者經驗, 使用者體驗, 使用者研究, 介面設計, 互動設計, 視覺設計, 產品設計, 體驗設計 (and simplified) | | 產品設計實習生 |

There are two more ways in:
- **Plain "Design(er) Intern(ship)"** (`GENERIC_DESIGN_PATTERNS`) counts when nothing comes
  before "Design": at the start of the title ("Designer Intern – Austin"), after a dash,
  comma, season or year ("Summer 2027 Design Intern"), or "Intern, Design". Otherwise
  engineering titles like "Propulsion Design Intern" would slip in. It also doesn't
  count if the title names another design field (`OTHER_DESIGN_FIELDS`): graphic,
  industrial, interior, fashion, landscape, architecture, instructional, learning,
  packaging, lighting, textile, jewelry, apparel, footwear, garden, kitchen, floral,
  print, motion.
- **Plain "Research Intern"** counts when the job description shows it's UX or user
  research (it mentions user research, UX research, Research & Insights, usability,
  design research or qualitative research). Machine-learning and science research
  internships stay out.

**2. None of these words** (`EXCLUDE_PATTERNS`). They remove engineering and chip-design
jobs that share design vocabulary: engineer, developer, programmer, mechanical,
electrical, circuit, chip, IC, RFIC, ASIC, analog, mixed-signal, verification, physical
design, digital design, civil, structural, water. So "UX Engineer" and "Product Design
Engineer" are left out.

"Hardware" is allowed only next to a clear UX term (`UX_ONLY_WITH`, `CLEAR_UX_TERMS`): UX,
UI, user experience, user research, interaction design, human factors or HCI. So "UX
Research Intern, Hardware" counts, but "Hardware Design Intern" (chip design) doesn't.

**3. An internship word** (`INTERN_PATTERNS`): intern, internship, co-op, placement,
"Summer 2027" (any year), "Summer Analyst" / "Summer Associate" (how banks name them),
實習 / 实习. Sources that only list internships (SimplifyJobs, Intern Dock, TikTok's
intern board) skip this check.

**Not included on purpose:** Content Design, graphic, industrial and motion design, and
"X Design Intern" titles where X is an engineering field. To change any of this, edit
the lists in `config.py`.

**Locations** (`REGIONS`): US, Singapore, Hong Kong, London and Taiwan. Remote roles count
unless they're tied to another country.

## When emails arrive, and why

The goal is to see every new internship early enough to **apply within 24 hours of it
being posted**.

**When companies actually post.** Greenhouse, Lever, Ashby and SmartRecruiters record the
exact moment a job is published. Across 189 internships posted by 29 companies in the
120 days before Sep 26, 2026, and counting a company's batch posted in the same hour once
(106 posting events), Seattle time:

```
12am-6am  ###          7%
6am-9am   #####       12%
9am-12pm  ##########  24%
12pm-3pm  ########### 28%   ← busiest
3pm-6pm   ########    19%
6pm-9pm   ##           3%
9pm-12am  ##           3%
```
Mon 27 · Tue 20 · Wed 17 · Thu 17 · Fri 23 · Sat 0 · Sun 2

Recruiters post during US business hours on weekdays: about 83% between 6am and 6pm
Seattle (9am–9pm Eastern), and almost nothing in the evening or on weekends.

**Why 11am, 3pm and 9pm.** How long a job waits for the next email, using the posting
times above:

| Emails (Seattle) | Typical wait | 90% of jobs within | Worst case |
|---|---|---|---|
| **11am + 3pm + 9pm (current)** | 2.8h | 6.0h | 13.6h |
| 11am + 9pm | 5.2h | 9.1h | 13.6h |
| 11am + 2pm + 6pm + 9pm | 2.0h | 5.7h | 13.6h |
| 12pm + 6pm | 3.7h | 11.1h | 18.0h |

- **11am** covers the overnight and early-morning postings.
- **3pm** covers the busy 9am–3pm stretch the same afternoon. Adding it roughly halves the
  typical wait.
- **9pm** covers 3pm–6pm and the few evening postings, plus the day's alert emails.
- **The worst case is ~14 hours** (a job posted just after 9pm waits for 11am), which
  still leaves 10+ hours to apply within 24 hours. Putting all the emails in the daytime
  would push the worst case to 18 hours.
- **Freshness differs by source.** Jobs from company career sites are checked the moment
  each email is built. Jobs from job-alert emails arrive later, often hours later.
  They show the date the alert arrived instead of a posting date, because alerts don't
  include one.

**Getting the email on time.** GitHub's own scheduler started runs 4–6 hours late (a
10:37am run started at 2:30pm, an 8:37pm run at 3am). So the times are kept by
[cron-job.org](https://cron-job.org) instead, set to Seattle time (daylight saving is
handled there). At 10:58am, 2:58pm and 8:58pm it presses "Run workflow" through GitHub's
API, which starts within seconds, and the email arrives about two minutes later.

**cron-job.org setup (once).**
1. GitHub → Settings → Developer settings → Fine-grained personal access tokens →
   Generate new token. Repository access: only this repo. Permissions: **Actions: Read
   and write**. Expiration: up to a year (renew it when GitHub emails you).
2. cron-job.org → Create cronjob, three times (or one job, then copy it):
   - URL: `https://api.github.com/repos/tzjiahung/design-research-job-search/actions/workflows/daily.yml/dispatches`
   - Schedule: custom, every day, at 10:58 / 14:58 / 20:58; time zone **America/Los_Angeles**
   - Advanced → Request method **POST**; headers
     `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`,
     `Content-Type: application/json`; body `{"ref":"main"}`
   - "Test run" should return **204**, and a run appears in the Actions tab.

**Changing the times.** Edit the cron-job.org jobs. Nothing in the repo changes.

**Manual runs.** Actions tab → "Daily design internship digest" → **Run workflow** sends
an email right away. Its "How far back to read job-alert emails" box takes a number of
days (e.g. `60`), for when alerts need catching up.

## Setup (once, ~10 minutes)

1. **Gmail app password.** Turn on 2-Step Verification in your Google account, then go
   to <https://myaccount.google.com/apppasswords>, create one named "job digest" and
   copy the 16-character password.
2. **GitHub repo.** Create a *private* repo and push this folder to it.
3. **Secrets.** In the repo: Settings → Secrets and variables → Actions → New repository secret:
   - `GMAIL_ADDRESS`: the Gmail account that sends the digest
   - `GMAIL_APP_PASSWORD`: the password from step 1
   - `TO_EMAIL` (optional): where to send it; defaults to `GMAIL_ADDRESS`
   - `ALERTS_EMAIL` and `ALERTS_APP_PASSWORD` (optional): the Gmail inbox that receives
     your Handshake/LinkedIn/... alerts, if it isn't `GMAIL_ADDRESS`. Needs its own app
     password. Alerts sent to other inboxes (e.g. a school address) can be auto-forwarded
     there with a Gmail filter.
4. **Test.** Actions tab → "Daily design internship digest" → Run workflow.

## Preview locally

```bash
python3 jobdigest.py --dry-run
```

Writes `digest.html` without sending anything or touching `seen.json`.

## Sponsorship labels

Read from the job description where the source provides one.

- **No sponsorship**: the posting rules it out. Examples: "unable to sponsor", "without
  current or future sponsorship", "not available for any work sponsorship", "not eligible
  for F-1/J-1 students", "U.S. citizenship required", "security clearance".
- **Sponsors**: the posting says sponsorship is available.
- **Not stated**: the posting doesn't say, or the source has no description (alert
  emails, lists like Intern Dock). Check the posting or ask the recruiter.
