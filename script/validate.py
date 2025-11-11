import csv, sys, re

REQUIRED = ["title","organisation","year","scope","link","summary"]
URL_PATTERN = re.compile(r"^https?://")

def main():
    path = "data/strategies.csv"
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ok = True
    for i, r in enumerate(rows, start=2):
        for k in REQUIRED:
            if not r.get(k):
                print(f"[Row {i}] Missing required field: {k}")
                ok = False
        if r.get("year") and not re.match(r"^\d{4}$", r["year"]):
            print(f"[Row {i}] Year is not YYYY: {r['year']}"); ok = False
        if r.get("link") and not URL_PATTERN.match(r["link"]):
            print(f"[Row {i}] Link not http/https: {r['link']}"); ok = False
        if r.get("scope") not in {"national","departmental","agency","devolved","local","cross-government"}:
            print(f"[Row {i}] Scope invalid: {r['scope']}"); ok = False
        if r.get("summary") and len(r["summary"]) > 280:
            print(f"[Row {i}] Summary too long (>280 chars)"); ok = False
    if ok:
        print("✓ strategies.csv looks good.")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
