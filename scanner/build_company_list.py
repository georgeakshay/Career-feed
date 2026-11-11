"""Build companies.csv = companies_seed.csv + UAE companies from Wikidata.

Run weekly by the workflow. If Wikidata is unreachable, the existing
companies.csv is kept as it is.
"""
import csv
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "companies_seed.csv")
OUT = os.path.join(ROOT, "companies.csv")
EXTRA = os.path.join(ROOT, "companies_extra.csv")  # optional, hand-added

UA = "career-feed/1.0 (personal job search; github.com/georgeakshay/career-feed)"

# Organisation types worth scanning (companies, banks, airlines, government
# bodies, etc.). Kept as a VALUES list instead of P279* so the query is fast.
TYPES = [
    "Q4830453",   # business
    "Q783794",    # company
    "Q6881511",   # enterprise
    "Q891723",    # public company
    "Q1589009",   # privately held company
    "Q219577",    # holding company
    "Q22687",     # bank
    "Q46970",     # airline
    "Q1331793",   # media company
    "Q18388277",  # technology company
    "Q1058914",   # software company
    "Q167037",    # corporation
    "Q327333",    # government agency
    "Q270791",    # state-owned enterprise
    "Q2085381",   # publisher
    "Q1145276",   # insurance company
    "Q650241",    # financial institution
    "Q778575",    # conglomerate
    "Q2659904",   # government organization
    "Q43229",     # organization
    "Q4287745",   # medical organization
]
SKIP_TYPES_IN_NAME = re.compile(r"\b(school|university|college|academy|embassy|consulate|mosque|church|club|fc|stadium)\b", re.I)

QUERY = """
SELECT DISTINCT ?item ?itemLabel ?website WHERE {
  VALUES ?type { %s }
  ?item wdt:P31 ?type .
  { ?item wdt:P17 wd:Q878 . }
  UNION { ?item wdt:P159 ?hq . ?hq wdt:P17 wd:Q878 . }
  ?item wdt:P856 ?website .
  FILTER NOT EXISTS { ?item wdt:P576 ?dissolved . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""" % " ".join("wd:" + t for t in TYPES)

BAD_DOMAINS = re.compile(
    r"(facebook|twitter|x\.com|instagram|linkedin|youtube|wikipedia|google|"
    r"blogspot|wordpress\.com|archive\.org|apple\.com/app)", re.I)


def norm_domain(url):
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    host = urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_wikidata():
    for attempt in range(3):
        try:
            r = requests.get(
                "https://query.wikidata.org/sparql",
                params={"query": QUERY, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=120,
            )
            if r.status_code == 200:
                rows = []
                for b in r.json()["results"]["bindings"]:
                    name = b.get("itemLabel", {}).get("value", "").strip()
                    site = b.get("website", {}).get("value", "").strip()
                    if not name or re.fullmatch(r"Q\d+", name):
                        continue
                    if SKIP_TYPES_IN_NAME.search(name):
                        continue
                    if BAD_DOMAINS.search(site):
                        continue
                    rows.append({"name": name, "domain": norm_domain(site), "careers_url": ""})
                return rows
            print(f"wikidata HTTP {r.status_code}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"wikidata error: {e}", file=sys.stderr)
        time.sleep(20)
    return None


def main():
    seed = read_csv(SEED) + read_csv(EXTRA)
    wd = fetch_wikidata()
    if wd is None:
        if os.path.exists(OUT):
            print("Wikidata unavailable; keeping existing companies.csv")
            return
        wd = []
    merged, seen = [], set()
    for row in seed + wd:
        dom = norm_domain(row.get("domain", ""))
        if not dom or dom in seen:
            continue
        seen.add(dom)
        merged.append({"name": row["name"].strip(), "domain": dom,
                       "careers_url": (row.get("careers_url") or "").strip()})
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "domain", "careers_url"])
        w.writeheader()
        w.writerows(merged)
    print(f"companies.csv: {len(merged)} companies ({len(seed)} seed, {len(wd)} from Wikidata)")


if __name__ == "__main__":
    main()
