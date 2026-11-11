# career-feed

Daily feed of business / data / BI / systems roles found directly on UAE
companies' own careers pages. It is used by the "Career Watch" scheduled task,
and it is separate from `job-feed` (the JobSpy feed behind the Job Hunt task).

**Output:** `career_jobs.json` at the repo root, rebuilt every day at about 06:45 Dubai time.

## How it works

1. `scanner/build_company_list.py` builds `companies.csv` from
   `companies_seed.csv` plus UAE organisations on Wikidata that list a website.
   It runs on the first run and every Monday. To add companies by hand, put
   them in `companies_extra.csv` with the same columns: name, domain, careers_url.
2. `scanner/scan.py`:
   - **Discovery:** finds each company's careers page and its applicant
     tracking system. It checks about 900 new companies per run.
   - **Scan:** reads the open jobs from about 1,500 companies per run, oldest
     scanned first. It uses public JSON APIs for Greenhouse, Lever, Workable,
     SmartRecruiters, Ashby, Recruitee, Teamtailor, Workday, Personio, Breezy
     and BambooHR. For other sites it reads the careers page HTML.
   - **Filter:** keeps business / data / BI / MIS / ERP-CRM / automation /
     strategy-type titles located in the UAE (or with no location given). It
     drops Director, Head, VP and Chief roles.
   - **Tracking:** records `first_seen` and `last_seen` for each job in
     `state/jobs_db.json`.
3. The workflow commits `career_jobs.json` and `state/` back to the repo.

## Feed format

```
generated_at_utc, stats{companies_in_list, discovery_done, careers_pages_found,
companies_scanned_today, ...}, unreadable_companies_today[{name, careers_page, reason}],
jobs[{title, company, location, url, careers_page, tier, first_seen, last_seen, description}]
```

Tier 1 is a strong title match (for example Business / Data / BI analyst,
Odoo, ERP, CRM, MIS). Tier 2 is a broader match.

## Run it manually

Actions → **Career feed** → **Run workflow**. Tick "Rebuild companies.csv"
to refresh the company list.
