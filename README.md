# Design internship digest

One email a day with every new UX / product design / UX research internship in the
US, Singapore, Hong Kong, London and Taiwan. Each job appears once, even when several
boards list it.

**Sources**, all read straight from the employer's own careers site:
- ~80 companies on Greenhouse, Lever, Ashby and SmartRecruiters (Figma, Airbnb, Stripe,
  Notion, Coinbase, Roblox, Pinterest, Duolingo, Wise, ServiceNow, ...)
- Big-company sites: Google, Meta, Apple, Microsoft, Amazon/AWS, NVIDIA, Adobe, IBM,
  ByteDance/TikTok, Atlassian, Salesforce/Slack, Walmart, Boeing, Nordstrom, Expedia,
  T-Mobile, Uber, JPMorgan, Citi, Capital One, Dell, Ford, Honda, Sony, Samsung, TSMC,
  Foxconn, DocuSign, GitHub, MathWorks, ...
- The SimplifyJobs and Intern Dock internship lists, and Y Combinator startups
- Job-alert emails in your inbox (Handshake, Jobright, Lenny's Jobs), read without changing anything

Edit [config.py](config.py) to change roles, regions or companies. A company that can't
be read on a given day is listed at the bottom of the email instead of breaking it.

**How it works:** a GitHub Action runs [jobdigest.py](jobdigest.py) at 11am and 11pm Seattle time. The first
email lists everything open right now; after that you only get jobs you haven't seen.
Jobs already sent are remembered in `seen.json`, which the Action updates on its own.

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
