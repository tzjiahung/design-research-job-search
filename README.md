# Design internship digest

Two emails a day (11am and 9pm Seattle time) with every new UX / product design / UX
research internship in the US, Singapore, Hong Kong, London and Taiwan. Each job appears
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

**How it works:** a GitHub Action runs [jobdigest.py](jobdigest.py) at 11am and 9pm
Seattle time. The first email listed everything open at the time; since then each email
has only jobs you haven't been sent. If nothing is new, you still get a short "No new
design internships" email. Jobs already sent are remembered in `seen.json`, which the
Action updates on its own.

## When emails arrive, and why

The goal is to see every new internship early enough to **apply within 24 hours of it
being posted**.

**When jobs go up.** Jobright's "just posted N minutes ago" alerts give a rough posting
time for each job. Across the 68 such alerts received Sep 1–25, 2026 (Seattle time):

```
12am-6am   0
6am-9am   ####### 7
9am-12pm  ########## 10
12pm-3pm  ########### 11
3pm-6pm   ############# 13
6pm-9pm   ################## 18   ← busiest
9pm-12am  ######### 9
```

Postings were spread across every day of the week, weekends included. These are the
times Jobright *noticed* each job, which can trail the real posting by up to an hour.

**Why 11am and 9pm.**
- **9pm** lands right after the busiest stretch (6–9pm), so the largest batch reaches you
  the same evening.
- **11am** picks up everything from the quiet overnight hours (nothing goes up between
  midnight and 6am) plus the morning.
- A job waits at most ~14 hours for the next email, and usually much less, which leaves
  at least ~10 hours to apply inside the 24-hour window.
- Jobs from company career sites are checked at the moment each email is built, so
  they're as fresh as possible. Jobs from alert emails (Jobright, Lenny's Jobs,
  Handshake) can lag by up to an hour. They show "received via Jobright on Sep 18"
  instead of a posting date, because alerts don't include one.

**Getting the email on time.** GitHub starts scheduled jobs late when it's busy,
especially exactly on the hour (one 9pm run once started five hours late). So the
schedule in [.github/workflows/daily.yml](.github/workflows/daily.yml) starts runs at
10:37am and 8:37pm, a quieter minute, and the job waits until 11:00 or 9:00 before
sending. Delays of up to ~20 minutes don't change when the email arrives. A longer
delay makes the email late, but it still arrives.

**Daylight saving.** GitHub schedules in UTC, and Seattle is UTC-7 in summer and UTC-8 in
winter, so each time is scheduled at both UTC hours. A check at the start of the job
skips whichever one doesn't match Seattle's clock that day.

**Want it fresher?** A third email costs nothing. 8am, 2pm and 9pm would cap the wait at
~11 hours. Add the matching cron lines and cases in `daily.yml`, and the target hour in its
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
