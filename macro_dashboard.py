#!/usr/bin/env python3
"""
macro_dashboard.py
Fetches macroeconomic data from FRED, BLS, and Census APIs.
Writes JSON to /var/www/html/api/macro.json for the dashboard to consume.
"""
 
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
import os
import tempfile
 
# ── API Keys ──────────────────────────────────────────────────────────────────
FRED_API_KEY   = "3df5c01a2be61cd06cb9b64d478a03f8"
BLS_API_KEY    = "8c683d0a80df4e568154dd00af09977d"
CENSUS_API_KEY = "1f1d3bd20058a4976c6a5028df24286b3a01076a"
 
OUT_FILE = "/var/www/html/api/macro.json"
 
# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())
 
# ── FRED ──────────────────────────────────────────────────────────────────────
def fred_series(series_id, limit=60):
    """Return list of {date, value} for a FRED series."""
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={FRED_API_KEY}"
        f"&file_type=json&sort_order=desc&limit={limit}"
    )
    data = fetch_json(url)
    obs = []
    for o in reversed(data.get("observations", [])):
        try:
            obs.append({"date": o["date"], "value": float(o["value"])})
        except (ValueError, KeyError):
            pass
    return obs
 
def fred_latest(series_id):
    obs = fred_series(series_id, limit=1)
    return obs[-1] if obs else None
 
# ── BLS ───────────────────────────────────────────────────────────────────────
def bls_series(series_ids, start_year=None, end_year=None):
    """Fetch one or more BLS series. Returns dict keyed by series_id."""
    if start_year is None:
        start_year = str(datetime.now().year - 5)
    if end_year is None:
        end_year = str(datetime.now().year)
 
    payload = json.dumps({
        "seriesid": series_ids,
        "startyear": start_year,
        "endyear": end_year,
        "registrationkey": BLS_API_KEY
    }).encode()
 
    data = fetch_json(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
 
    result = {}
    for series in data.get("Results", {}).get("series", []):
        sid = series["seriesID"]
        obs = []
        for d in reversed(series.get("data", [])):
            try:
                # Skip annual/semi-annual periods
                if d["period"].startswith("A") or d["period"].startswith("S"):
                    continue
                obs.append({
                    "date": f"{d['year']}-{d['period'][1:]}",
                    "value": float(d["value"])
                })
            except (ValueError, KeyError):
                pass
        result[sid] = obs
    return result
 
# ── Census ────────────────────────────────────────────────────────────────────
def census_median_household_income():
    """Get latest US median household income from Census ACS."""
    url = (
        f"https://api.census.gov/data/2022/acs/acs1"
        f"?get=B19013_001E,NAME&for=us:1&key={CENSUS_API_KEY}"
    )
    try:
        data = fetch_json(url)
        # data[0] = headers, data[1] = values
        val = int(data[1][0])
        return {"value": val, "year": 2022, "label": "Median Household Income"}
    except Exception as e:
        return {"value": None, "year": None, "label": "Median Household Income", "error": str(e)}
 
def census_housing_units():
    """Get total US housing units from Census."""
    url = (
        f"https://api.census.gov/data/2022/acs/acs1"
        f"?get=B25001_001E,NAME&for=us:1&key={CENSUS_API_KEY}"
    )
    try:
        data = fetch_json(url)
        val = int(data[1][0])
        return {"value": val, "year": 2022, "label": "Total Housing Units"}
    except Exception as e:
        return {"value": None, "year": None, "label": "Total Housing Units", "error": str(e)}
 
# ── Main ──────────────────────────────────────────────────────────────────────
def build_payload():
    print("Fetching FRED data...")
 
    # FRED series
    fed_funds    = fred_series("FEDFUNDS", limit=60)       # Fed funds rate
    unrate       = fred_series("UNRATE", limit=60)         # Unemployment
    gdp          = fred_series("GDPC1", limit=20)          # Real GDP (quarterly)
    cpi          = fred_series("CPIAUCSL", limit=60)       # CPI
    t10y2y       = fred_series("T10Y2Y", limit=60)         # Yield spread
    dgs10        = fred_series("DGS10", limit=60)          # 10yr treasury
    dgs2         = fred_series("DGS2", limit=60)           # 2yr treasury
    m2           = fred_series("M2SL", limit=60)           # M2 money supply
    pce          = fred_series("PCEPI", limit=60)          # PCE inflation
    payems       = fred_series("PAYEMS", limit=60)         # Nonfarm payrolls
    houst        = fred_series("HOUST", limit=60)          # Housing starts
    umcsent      = fred_series("UMCSENT", limit=60)        # Consumer sentiment
 
    print("Fetching BLS data...")
    # BLS: CPI-U (CUUR0000SA0), Job Openings (JTS000000000000000JOL)
    bls_data = bls_series(
        ["CUUR0000SA0", "JTS000000000000000JOL"],
        start_year=str(datetime.now().year - 4),
        end_year=str(datetime.now().year)
    )
 
    print("Fetching Census data...")
    median_income  = census_median_household_income()
    housing_units  = census_housing_units()
 
    # Latest values for callout cards
    def latest(series):
        return series[-1] if series else None
 
    payload = {
        "updated": datetime.now().isoformat(),
        "fred": {
            "fed_funds":    {"series": fed_funds,    "latest": latest(fed_funds),    "label": "Fed Funds Rate",         "unit": "%"},
            "unemployment": {"series": unrate,       "latest": latest(unrate),       "label": "Unemployment Rate",      "unit": "%"},
            "gdp":          {"series": gdp,          "latest": latest(gdp),          "label": "Real GDP",               "unit": "B USD"},
            "cpi":          {"series": cpi,          "latest": latest(cpi),          "label": "CPI",                    "unit": "index"},
            "pce":          {"series": pce,          "latest": latest(pce),          "label": "PCE Inflation",          "unit": "index"},
            "t10y2y":       {"series": t10y2y,       "latest": latest(t10y2y),       "label": "10Y-2Y Spread",          "unit": "%"},
            "dgs10":        {"series": dgs10,        "latest": latest(dgs10),        "label": "10-Year Treasury",       "unit": "%"},
            "dgs2":         {"series": dgs2,         "latest": latest(dgs2),         "label": "2-Year Treasury",        "unit": "%"},
            "m2":           {"series": m2,           "latest": latest(m2),           "label": "M2 Money Supply",        "unit": "B USD"},
            "payrolls":     {"series": payems,       "latest": latest(payems),       "label": "Nonfarm Payrolls",       "unit": "K"},
            "housing_starts":{"series": houst,       "latest": latest(houst),        "label": "Housing Starts",         "unit": "K units"},
            "sentiment":    {"series": umcsent,      "latest": latest(umcsent),      "label": "Consumer Sentiment",     "unit": "index"},
        },
        "bls": {
            "cpi_u":       {"series": bls_data.get("CUUR0000SA0", []),  "label": "CPI-U (BLS)",      "unit": "index"},
            "job_openings":{"series": bls_data.get("JTS000000000000000JOL", []), "label": "Job Openings", "unit": "K"},
        },
        "census": {
            "median_income": median_income,
            "housing_units": housing_units,
        }
    }
    return payload
 
def main():
    print(f"[{datetime.now().isoformat()}] Building macro dashboard data...")
    try:
        payload = build_payload()
        os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
        tmp = OUT_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, OUT_FILE)
        os.chmod(OUT_FILE, 0o644)
        print(f"Written to {OUT_FILE}")
    except Exception as e:
        print(f"ERROR: {e}")
        raise
 
if __name__ == "__main__":
    main()