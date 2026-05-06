#!/usr/bin/env python3
"""
macro_dashboard.py
Fetches macroeconomic data from FRED, BLS, and Census APIs.
Writes JSON to /var/www/html/api/macro.json
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
import time
import os

FRED_API_KEY   = "3df5c01a2be61cd06cb9b64d478a03f8"
BLS_API_KEY    = "8c683d0a80df4e568154dd00af09977d"
CENSUS_API_KEY = "1f1d3bd20058a4976c6a5028df24286b3a01076a"
OUT_FILE       = "/var/www/html/api/macro.json"

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

# ── FRED ──────────────────────────────────────────────────────────────────────
def fred_series(series_id, limit=500, observation_start="2000-01-01"):
    time.sleep(0.5)
    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={FRED_API_KEY}"
            f"&file_type=json&sort_order=asc&limit={limit}"
            f"&observation_start={observation_start}"
        )
        data = fetch_json(url)
        obs = []
        for o in data.get("observations", []):
            try:
                obs.append({"date": o["date"], "value": float(o["value"])})
            except (ValueError, KeyError):
                pass
        return obs
    except Exception as e:
        print(f"  WARNING: failed to fetch {series_id}: {e}")
        return []

def fred_latest(series_id):
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={FRED_API_KEY}"
        f"&file_type=json&sort_order=desc&limit=1"
    )
    data = fetch_json(url)
    for o in data.get("observations", []):
        try:
            return {"date": o["date"], "value": float(o["value"])}
        except (ValueError, KeyError):
            pass
    return None

def fred_on_date(series_id, date):
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={FRED_API_KEY}"
        f"&file_type=json&sort_order=desc&limit=1"
        f"&observation_end={date}"
    )
    data = fetch_json(url)
    for o in data.get("observations", []):
        try:
            return {"date": o["date"], "value": float(o["value"])}
        except (ValueError, KeyError):
            pass
    return None

def to_billions(series):
    return [{"date": o["date"], "value": o["value"] / 1000} for o in series]

def val_to_billions(obs):
    if not obs: return obs
    return {"date": obs["date"], "value": obs["value"] / 1000}

def yoy_pct(series):
    if len(series) < 13:
        return []
    result = []
    for i in range(12, len(series)):
        try:
            prev = series[i - 12]["value"]
            curr = series[i]["value"]
            if prev != 0:
                pct = round((curr - prev) / prev * 100, 2)
                result.append({"date": series[i]["date"], "value": pct})
        except (KeyError, TypeError):
            pass
    return result

# ── BLS ───────────────────────────────────────────────────────────────────────
def bls_series(series_ids, start_year="2000", end_year=None):
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
def build_census():
    year = 2022
    ds = "acs/acs1"
    queries = {
        "median_household_income": "B19013_001E",
        "per_capita_income":       "B19301_001E",
        "total_population":        "B01003_001E",
        "median_age":              "B01002_001E",
        "total_housing_units":     "B25001_001E",
        "owner_occupied":          "B25003_002E",
        "total_occupied_units":    "B25003_001E",
        "poverty_population":      "B17001_002E",
        "total_poverty_universe":  "B17001_001E",
        "median_home_value":       "B25077_001E",
        "bachelors_degree":        "B15003_022E",
        "masters_degree":          "B15003_023E",
        "total_education_pop":     "B15003_001E",
        "gini_coefficient":        "B19083_001E",
        "labor_force":             "B23025_002E",
        "civilian_pop":            "B23025_001E",
    }
    vars_list = list(queries.values())
    url = (
        f"https://api.census.gov/data/{year}/{ds}"
        f"?get={','.join(vars_list)},NAME&for=us:1&key={CENSUS_API_KEY}"
    )
    try:
        raw_data = fetch_json(url)
        headers = raw_data[0]
        values  = raw_data[1]
        raw = {headers[i]: values[i] for i in range(len(headers))}
    except Exception as e:
        return {"error": str(e), "year": year}

    def safe_int(key):
        try:
            return int(raw.get(queries[key], 0) or 0)
        except:
            return None

    def safe_float(key):
        try:
            v = raw.get(queries[key])
            return float(v) if v else None
        except:
            return None

    occupied  = safe_int("total_occupied_units")
    owner_occ = safe_int("owner_occupied")
    pov_pop   = safe_int("poverty_population")
    pov_univ  = safe_int("total_poverty_universe")
    labor     = safe_int("labor_force")
    civ_pop   = safe_int("civilian_pop")
    bach      = safe_int("bachelors_degree")
    masters   = safe_int("masters_degree")
    edu_pop   = safe_int("total_education_pop")

    homeownership_pct = round(owner_occ / occupied * 100, 1) if occupied else None
    poverty_rate      = round(pov_pop / pov_univ * 100, 1) if pov_univ else None
    lfp_rate          = round(labor / civ_pop * 100, 1) if civ_pop else None
    edu_pct           = round(((bach or 0) + (masters or 0)) / edu_pop * 100, 1) if edu_pop else None

    return {
        "year": year,
        "median_household_income": {"value": safe_int("median_household_income"), "label": "Median Household Income",    "unit": "USD"},
        "per_capita_income":       {"value": safe_int("per_capita_income"),        "label": "Per Capita Income",          "unit": "USD"},
        "total_population":        {"value": safe_int("total_population"),          "label": "Total Population",           "unit": "people"},
        "median_age":              {"value": safe_float("median_age"),              "label": "Median Age",                 "unit": "years"},
        "total_housing_units":     {"value": safe_int("total_housing_units"),       "label": "Total Housing Units",        "unit": "units"},
        "homeownership_rate":      {"value": homeownership_pct,                    "label": "Homeownership Rate",         "unit": "%"},
        "poverty_rate":            {"value": poverty_rate,                          "label": "Poverty Rate",               "unit": "%"},
        "median_home_value":       {"value": safe_int("median_home_value"),         "label": "Median Home Value",          "unit": "USD"},
        "labor_force_participation":{"value": lfp_rate,                             "label": "Labor Force Participation",  "unit": "%"},
        "bachelors_or_higher":     {"value": edu_pct,                               "label": "Bachelor's Degree or Higher","unit": "%"},
        "gini_coefficient":        {"value": safe_float("gini_coefficient"),        "label": "Gini Coefficient",           "unit": "index"},
    }

# ── Debt ──────────────────────────────────────────────────────────────────────
def build_debt():
    print("  Fetching debt data...")
    debt_series  = to_billions(fred_series("GFDEBTN", limit=500, observation_start="2000-01-01"))
    debt_latest  = val_to_billions(fred_latest("GFDEBTN"))
    debt_feb2000 = val_to_billions(fred_on_date("GFDEBTN", "2000-02-01"))

    debt_added_raw = None
    debt_added_pct = None
    if debt_latest and debt_feb2000:
        debt_added_raw = round(debt_latest["value"] - debt_feb2000["value"], 2)
        debt_added_pct = round((debt_latest["value"] - debt_feb2000["value"]) / debt_feb2000["value"] * 100, 2)

    household_debt   = to_billions(fred_series("HHMSDODNS", limit=500, observation_start="2000-01-01"))
    household_latest = val_to_billions(fred_latest("HHMSDODNS"))
    cc_debt          = fred_series("REVOLSL",         limit=500, observation_start="2000-01-01")
    cc_latest        = fred_latest("REVOLSL")
    consumer_debt    = fred_series("DTCTHFNM",        limit=500, observation_start="2000-01-01")
    consumer_latest  = fred_latest("DTCTHFNM")
    debt_gdp         = fred_series("GFDEGDQ188S",     limit=500, observation_start="2000-01-01")
    debt_gdp_latest  = fred_latest("GFDEGDQ188S")
    dsr              = fred_series("TDSP",            limit=500, observation_start="2000-01-01")
    dsr_latest       = fred_latest("TDSP")

    # From 2022 Fed Survey of Consumer Finances
    debt_by_age = [
        {"range": "18–29", "value": 20000,  "label": "Avg Debt Age 18-29"},
        {"range": "30–44", "value": 167000, "label": "Avg Debt Age 30-44"},
        {"range": "45–59", "value": 134000, "label": "Avg Debt Age 45-59"},
        {"range": "60–74", "value": 94000,  "label": "Avg Debt Age 60-74"},
        {"range": "75+",   "value": 38000,  "label": "Avg Debt Age 75+"},
    ]

    return {
        "federal_debt": {
            "series": debt_series, "latest": debt_latest,
            "label": "Total Federal Debt", "unit": "B USD", "frequency": "Quarterly"
        },
        "debt_since_2000": {
            "baseline": debt_feb2000, "latest": debt_latest,
            "added_raw": debt_added_raw, "added_pct": debt_added_pct,
            "label": "Debt I've Seen", "unit": "B USD"
        },
        "household_debt": {
            "series": household_debt, "latest": household_latest,
            "label": "Total Household Debt", "unit": "B USD"
        },
        "credit_card_debt": {
            "series": cc_debt, "latest": cc_latest,
            "label": "Revolving Consumer Credit", "unit": "B USD"
        },
        "consumer_debt": {
            "series": consumer_debt, "latest": consumer_latest,
            "label": "Total Consumer Credit", "unit": "B USD"
        },
        "debt_to_gdp": {
            "series": debt_gdp, "latest": debt_gdp_latest,
            "label": "Federal Debt to GDP", "unit": "%"
        },
        "debt_service_ratio": {
            "series": dsr, "latest": dsr_latest,
            "label": "Household Debt Service Ratio", "unit": "%"
        },
        "debt_by_age": debt_by_age
    }

# ── Main ──────────────────────────────────────────────────────────────────────
def build_payload():
    print("Fetching FRED core data...")
    fed_funds  = fred_series("FEDFUNDS")
    unrate     = fred_series("UNRATE")
    gdp        = fred_series("GDPC1", limit=200)
    cpi        = fred_series("CPIAUCSL")
    pce        = fred_series("PCEPI")
    t10y2y     = fred_series("T10Y2Y")
    dgs10      = fred_series("DGS10")
    dgs2       = fred_series("DGS2")
    m2         = fred_series("M2SL")
    payems     = fred_series("PAYEMS")
    houst      = fred_series("HOUST")
    umcsent    = fred_series("UMCSENT")

    print("Fetching additional indicators...")
    sp500      = fred_series("SP500")
    vix        = fred_series("VIXCLS")
    dxy        = fred_series("DTWEXM")
    oil        = fred_series("DCOILWTICO")
    gold       = [] # TODO: find correct FRED series ID for gold
    jolts_quit = fred_series("JTSQUR", limit=200)
    jolts_hire = fred_series("JTSHIR", limit=200)
    real_wage  = fred_series("CES0500000003")
    savings    = fred_series("PSAVERT")
    retail     = fred_series("RSAFS")
    indpro     = fred_series("INDPRO")

    print("Fetching BLS data...")
    bls_data = bls_series(["CUUR0000SA0", "JTS000000000000000JOL"])

    print("Fetching Census data...")
    census = build_census()

    print("Fetching debt data...")
    debt = build_debt()

    cpi_yoy = yoy_pct(cpi)
    pce_yoy = yoy_pct(pce)

    def latest(s):
        return s[-1] if s else None

    return {
        "updated": datetime.now().isoformat(),
        "fred": {
            "fed_funds":       {"series": fed_funds,   "latest": latest(fed_funds),   "label": "Fed Funds Rate",         "unit": "%"},
            "unemployment":    {"series": unrate,      "latest": latest(unrate),      "label": "Unemployment Rate",      "unit": "%"},
            "gdp":             {"series": gdp,          "latest": latest(gdp),         "label": "Real GDP",               "unit": "B USD"},
            "cpi":             {"series": cpi,          "latest": latest(cpi),         "label": "CPI",                    "unit": "index",
                                "yoy_series": cpi_yoy,  "yoy_latest": latest(cpi_yoy)},
            "pce":             {"series": pce,          "latest": latest(pce),         "label": "PCE Inflation",          "unit": "index",
                                "yoy_series": pce_yoy,  "yoy_latest": latest(pce_yoy)},
            "t10y2y":          {"series": t10y2y,       "latest": latest(t10y2y),      "label": "10Y-2Y Spread",          "unit": "%"},
            "dgs10":           {"series": dgs10,         "latest": latest(dgs10),       "label": "10-Year Treasury",       "unit": "%"},
            "dgs2":            {"series": dgs2,          "latest": latest(dgs2),        "label": "2-Year Treasury",        "unit": "%"},
            "m2":              {"series": m2,            "latest": latest(m2),          "label": "M2 Money Supply",        "unit": "B USD"},
            "payrolls":        {"series": payems,        "latest": latest(payems),      "label": "Nonfarm Payrolls",       "unit": "K"},
            "housing_starts":  {"series": houst,         "latest": latest(houst),       "label": "Housing Starts",         "unit": "K units"},
            "sentiment":       {"series": umcsent,       "latest": latest(umcsent),     "label": "Consumer Sentiment",     "unit": "index"},
            "sp500":           {"series": sp500,         "latest": latest(sp500),       "label": "S&P 500",                "unit": "index"},
            "vix":             {"series": vix,           "latest": latest(vix),         "label": "VIX Volatility",         "unit": "index"},
            "dollar_index":    {"series": dxy,           "latest": latest(dxy),         "label": "USD Index",              "unit": "index"},
            "oil":             {"series": oil,           "latest": latest(oil),         "label": "WTI Crude Oil",          "unit": "$/bbl"},
            "gold":            {"series": gold,          "latest": latest(gold),        "label": "Gold Price",             "unit": "$/oz"},
            "quit_rate":       {"series": jolts_quit,    "latest": latest(jolts_quit),  "label": "Quit Rate (JOLTS)",      "unit": "%"},
            "hire_rate":       {"series": jolts_hire,    "latest": latest(jolts_hire),  "label": "Hire Rate (JOLTS)",      "unit": "%"},
            "hourly_earnings": {"series": real_wage,     "latest": latest(real_wage),   "label": "Avg Hourly Earnings",    "unit": "$/hr"},
            "savings_rate":    {"series": savings,       "latest": latest(savings),     "label": "Personal Savings Rate",  "unit": "%"},
            "retail_sales":    {"series": retail,        "latest": latest(retail),      "label": "Retail Sales",           "unit": "M USD"},
            "industrial_prod": {"series": indpro,        "latest": latest(indpro),      "label": "Industrial Production",  "unit": "index"},
        },
        "bls": {
            "cpi_u":        {"series": bls_data.get("CUUR0000SA0", []),           "label": "CPI-U (BLS)",  "unit": "index"},
            "job_openings": {"series": bls_data.get("JTS000000000000000JOL", []), "label": "Job Openings", "unit": "K"},
        },
        "census": census,
        "debt":   debt,
    }

def main():
    print(f"[{datetime.now().isoformat()}] Building macro dashboard data...")
    try:
        payload = build_payload()
        os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
        tmp = OUT_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, OUT_FILE)
        os.chmod(OUT_FILE, 0o644)
        print(f"Done. Written to {OUT_FILE}")
    except Exception as e:
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()