# Design internship digest

Three emails a day (11am, 3pm and 9pm Seattle time) with every new UX / product design /
UX research internship in the US, Singapore, Hong Kong, London and Taiwan. Each job appears
once, even when several boards list it.

**Sources:**
- ~80 companies' own job boards on Greenhouse, Lever, Ashby and SmartRecruiters (Figma, Airbnb, Stripe,
  Notion, Coinbase, Roblox, Pinterest, Duolingo, Wise, ServiceNow, ...)
- Big-company sites: Google, Meta, Apple, Microsoft, Amazon/AWS, NVIDIA, Adobe, IBM,
  ByteDance/TikTok, Atlassian, Salesforce/Slack, Walmart, Boeing, Nordstrom, Expedia,
  T-Mobile, Uber, JPMorgan, Citi, Capital One, Dell, Ford, Honda, Sony, Samsung, TSMC,
  Foxconn, DocuSign, GitHub, MathWorks, ...
- The SimplifyJobs and Intern Dock internship lists, and Y Combinator startups
- Job-alert emails in your inbox (Handshake, Jobright, Lenny's Jobs), read without changing anything

Edit [config.py](config.py) to change roles, regions or companies. A company that can't
be read on a given day is listed at the bottom of the email instead of breaking it.

**How it works:** a GitHub Action runs [jobdigest.py](jobdigest.py) at 11am, 3pm and 9pm
Seattle time. The first email listed everything open at the time; since then each email
has only jobs you haven't been sent. If nothing is new, you still get a short "No new
design internships" email. Jobs already sent are remembered in `seen.json`, which the
Action updates on its own.

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

Jobright's alerts suggest otherwise: their "just posted" times peak at 6–9pm and include
weekends. That peak is when Jobright finds jobs and sends alerts, often hours after the
company posted, so the company data above is the one to plan around.

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
  each email is built. Jobs from alert emails (Jobright, Lenny's Jobs, Handshake) arrive
  later, often hours later. They show "received via Jobright on Sep 18" instead of a
  posting date, because alerts don't include one.

**Getting the email on time.** GitHub starts scheduled jobs late when it's busy,
especially exactly on the hour (one 9pm run once started five hours late). So the
schedule in [.github/workflows/daily.yml](.github/workflows/daily.yml) starts each run
at :37, about 20 minutes early, which is a quieter minute. The job then waits until the
exact hour before sending. Delays of up to ~20 minutes don't change when the email arrives. A longer
delay makes the email late, but it still arrives.

**Daylight saving.** GitHub schedules in UTC, and Seattle is UTC-7 in summer and UTC-8 in
winter, so each time is scheduled at both UTC hours. A check at the start of the job
skips whichever one doesn't match Seattle's clock that day.

**Changing the times.** Each email needs two cron lines in `daily.yml` (the PDT and PST
UTC hours) and a matching entry in the schedule check. Its hour also goes in the
"Wait until" step.

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

- **Sponsors** / **No sponsorship**: the posting says so explicitly.
- **Not stated**: most postings don't say; ask the recruiter.
