# Findings and interpretation

## Checked results

- EPA's annual county AQI files contain 997 rows for 2024 and 985 for 2025. The curated U.S./territories panel excludes the single Sonora, Mexico row in each year, leaving **996** and **984** county-year rows.
- **977** county identifiers occur in both years. For year-to-year comparison, **773** of those have at least **300 days with AQI in both years**. This threshold is an analytical coverage rule, not an EPA completeness certification.
- Within that matched 773-county panel, the median county share of *observed AQI days* rated Unhealthy for Sensitive Groups or worse is **0.27% in 2024** and **0.28% in 2025**. The median of county-level changes is **0.00 percentage points**. Many counties have zero such days, so medians alone hide variation.
- Across the same county panel, the sum of recorded unhealthy-or-worse county-days falls from **3,772** to **2,902**. This counts county-days, so one calendar day can contribute in many counties; it is not a count of unique U.S. days or people exposed.
- In 2025, San Bernardino County, California has **30.14%** of its **365 observed days** in the 101+ categories. This identifies a county for closer investigation, not a causal explanation or an estimate of individual exposure.

## Dashboard design

The planned overview uses a year selector, a state/territory selector, four KPI cards (counties, observed AQI days, unhealthy-or-worse county-days, and median county share), a category-day composition chart, and a ranked county comparison. A second page will expose the matched-coverage panel and county details so viewers can distinguish a change in the monitored sample from a within-county comparison. All cards and charts must state their unit and denominator.

## Limits

- EPA says county AQI reflects available monitor measurements. Coverage and monitored pollutants differ across counties, and unmonitored counties are absent. The highest pollutant index defines the daily AQI. This panel is not a full-county census or a population-weighted exposure measure.
- The `unhealthy_share_observed_pct` denominator is **Days with AQI**. A low percentage with few observed days is not evidence of uniformly clean air.
- The two-year comparison is descriptive. Weather, smoke, emissions, monitoring network changes, and data revisions can all affect values; no cause is identified here.
- The ZIP files are a dated source snapshot identified by hashes in `validation_summary.json`. EPA can revise records, and a later rebuild may change the results.
- The Sonora, Mexico records in the EPA downloads are excluded because this case study is scoped to U.S. states and territories. Puerto Rico and the U.S. Virgin Islands remain in scope.

