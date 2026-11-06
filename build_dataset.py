"""Build a reproducible two-year county AQI panel from EPA AirData files."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
YEARS = (2024, 2025)
URL = "https://aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_{year}.zip"
EXCLUDED_STATES = {"Country Of Mexico"}
DAY_FIELDS = (
    "Good Days", "Moderate Days", "Unhealthy for Sensitive Groups Days",
    "Unhealthy Days", "Very Unhealthy Days", "Hazardous Days",
)
POLLUTANT_FIELDS = ("Days CO", "Days NO2", "Days Ozone", "Days PM2.5", "Days PM10")


def read_year(year: int) -> tuple[list[dict], str]:
    path = ROOT / f"annual_aqi_by_county_{year}.zip"
    if not path.exists():
        urllib.request.urlretrieve(URL.format(year=year), path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as bundle:
        with bundle.open(f"annual_aqi_by_county_{year}.csv") as data:
            import io
            rows = list(csv.DictReader(io.TextIOWrapper(data, encoding="utf-8-sig", newline="")))
    if not rows:
        raise ValueError(f"EPA file is empty: {year}")
    return rows, digest


def main() -> None:
    output = []
    counts = {}
    hashes = {}
    excluded_rows = []
    invalid = []
    seen = set()
    for year in YEARS:
        rows, hashes[str(year)] = read_year(year)
        counts[str(year)] = len(rows)
        for row in rows:
            if int(row["Year"]) != year:
                raise ValueError("Year mismatch")
            key = (year, row["State"], row["County"])
            if key in seen:
                raise ValueError(f"Duplicate county-year: {key}")
            seen.add(key)
            days = int(row["Days with AQI"])
            categories = {field: int(row[field] or 0) for field in DAY_FIELDS}
            if sum(categories.values()) != days:
                invalid.append((key, "category sum", sum(categories.values()), days))
            if days <= 0 or days > (366 if year == 2024 else 365):
                invalid.append((key, "days range", days))
            unhealthy = sum(categories[field] for field in DAY_FIELDS[2:])
            pollutant_days = {field: int(row[field] or 0) for field in POLLUTANT_FIELDS}
            if sum(pollutant_days.values()) != days:
                invalid.append((key, "main pollutant sum", sum(pollutant_days.values()), days))
            if row["State"] in EXCLUDED_STATES:
                excluded_rows.append({"year": year, "state": row["State"], "county": row["County"]})
                continue
            output.append({
                "year": year,
                "state": row["State"],
                "county": row["County"],
                "county_state": f'{row["County"]}, {row["State"]}',
                "days_with_aqi": days,
                "calendar_days": 366 if year == 2024 else 365,
                "coverage_pct": round(100 * days / (366 if year == 2024 else 365), 2),
                "good_days": categories["Good Days"],
                "moderate_days": categories["Moderate Days"],
                "sensitive_groups_days": categories["Unhealthy for Sensitive Groups Days"],
                "unhealthy_days": categories["Unhealthy Days"],
                "very_unhealthy_days": categories["Very Unhealthy Days"],
                "hazardous_days": categories["Hazardous Days"],
                "unhealthy_or_worse_days": unhealthy,
                "unhealthy_share_observed_pct": round(100 * unhealthy / days, 2),
                "median_aqi": int(row["Median AQI"]),
                "p90_aqi": int(row["90th Percentile AQI"]),
                "max_aqi": int(row["Max AQI"]),
                "days_co_main": pollutant_days["Days CO"],
                "days_no2_main": pollutant_days["Days NO2"],
                "days_ozone_main": pollutant_days["Days Ozone"],
                "days_pm25_main": pollutant_days["Days PM2.5"],
                "days_pm10_main": pollutant_days["Days PM10"],
            })
    if invalid:
        raise ValueError(f"Reconciliation errors: {invalid[:10]} (total {len(invalid)})")
    pairs = {}
    for row in output:
        pairs.setdefault((row["state"], row["county"]), {})[row["year"]] = row
    matched = [pair for pair in pairs.values() if len(pair) == 2]
    robust = [pair for pair in matched if all(pair[y]["days_with_aqi"] >= 300 for y in YEARS)]
    robust_keys = {(pair[2024]["state"], pair[2024]["county"]) for pair in robust}
    for row in output:
        key = (row["state"], row["county"])
        row["matched_300plus_both_years"] = 1 if key in robust_keys else 0
        row["county_change_share_pp_2025_minus_2024"] = (
            round(pairs[key][2025]["unhealthy_share_observed_pct"] - pairs[key][2024]["unhealthy_share_observed_pct"], 2)
            if key in robust_keys and row["year"] == 2025 else ""
        )
    fieldnames = list(output[0])
    csv_path = ROOT / "epa_county_aqi_2024_2025.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)
    summary = {
        "source_urls": {str(y): URL.format(year=y) for y in YEARS},
        "source_zip_sha256": hashes,
        "rows_by_year": counts,
        "excluded_non_us_rows": excluded_rows,
        "reconciliation_errors": 0,
        "matched_counties": len(matched),
        "matched_counties_with_300plus_days_both_years": len(robust),
        "by_year": {},
        "matched_300plus_day_panel": {},
    }
    for year in YEARS:
        subset = [row for row in output if row["year"] == year]
        summary["by_year"][str(year)] = {
            "reported_counties": len(subset),
            "counties_300plus_days": sum(row["days_with_aqi"] >= 300 for row in subset),
            "median_days_with_aqi": statistics.median(row["days_with_aqi"] for row in subset),
            "median_unhealthy_share_observed_pct": statistics.median(row["unhealthy_share_observed_pct"] for row in subset),
            "total_reported_aqi_days": sum(row["days_with_aqi"] for row in subset),
            "total_unhealthy_or_worse_days": sum(row["unhealthy_or_worse_days"] for row in subset),
            "counties_by_state": dict(sorted(Counter(row["state"] for row in subset).items())),
        }
        robust_rows = [pair[year] for pair in robust]
        summary["matched_300plus_day_panel"][str(year)] = {
            "median_unhealthy_share_observed_pct": statistics.median(row["unhealthy_share_observed_pct"] for row in robust_rows),
            "total_aqi_days": sum(row["days_with_aqi"] for row in robust_rows),
            "total_unhealthy_or_worse_days": sum(row["unhealthy_or_worse_days"] for row in robust_rows),
        }
    changes = [pair[2025]["unhealthy_share_observed_pct"] - pair[2024]["unhealthy_share_observed_pct"] for pair in robust]
    summary["matched_300plus_day_panel"]["median_county_change_percentage_points"] = statistics.median(changes)
    summary["matched_300plus_day_panel"]["counties_higher_share_2025"] = sum(x > 0 for x in changes)
    summary["matched_300plus_day_panel"]["counties_lower_share_2025"] = sum(x < 0 for x in changes)
    summary["matched_300plus_day_panel"]["counties_equal_share"] = sum(x == 0 for x in changes)
    (ROOT / "validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("rows_by_year", "matched_counties", "matched_counties_with_300plus_days_both_years", "matched_300plus_day_panel")}, indent=2))


if __name__ == "__main__":
    main()

