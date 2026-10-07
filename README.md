# Pulse · Insight Engine

Auto-analytics for district health data. Drop in a CSV and it finds trends, outliers, correlations and target breaches, then writes each one up as a short, data-driven insight.

Built with **NiceGUI** (Python UI on FastAPI) and **pandas**. One process, no separate API.

## Run

Python 3.11+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dashboard, opens on http://localhost:8080

```bash
python app.py
```

Console report (head, info, missing values) and exports to `output/`

```bash
python engine.py
python engine.py data/health.csv --trend 15 --method robust --corr 0.8 --target 85
```

Windows: activate with `.venv\Scripts\activate`.

## Files

```
engine.py         loading, validation, detection, insight writer, CLI
app.py            dashboard
data/health.csv   sample dataset
output/           insights.csv, insights.json, correlation_matrix.csv, correlation_changes.csv
```

## How it works

| Step | Method | Default |
|---|---|---|
| Load | Auto-detects the month column, the district column and every numeric indicator. Duplicates are merged and missing values reported. | |
| Trend | `pct_change = (current − previous) / previous × 100` per district and indicator | ±10% |
| Outlier | IQR fence `Q1 − k·IQR`, `Q3 + k·IQR`, or Z-score, or robust Z (median / MAD) | k = 1.5, z = 3, robust z = 3.5 |
| Correlation | Pearson on indicator levels, plus Pearson on month-over-month changes | \|r\| ≥ 0.70 |
| Breach | Coverage-type indicator (0–100, higher is better) below target | 80% |

Every threshold is a slider in the UI.

**Severity comes from the data, measured against your own threshold.** Each finding gets a ratio: how far it goes past its threshold.

- Below 1.2× is **Low**, 1.2× to 1.5× is **Medium**, 1.5× and above is **High**
- Favourable movements (coverage up, risk cases down) drop one level
- A breach that is new this month moves up one level
- Correlations are scored by where |r| sits between the threshold and 1. They drop one level when n < 10.

Indicators where lower is better (for example `high_risk_cases`) are detected from the column name, and you can change them in the UI.

**Insights are never hardcoded.** Sentences come from templates, and every name and number in them comes from the data. Each row has `insight_id, type, indicator, entity, period, value, prev_value, change_pct, metric, score, severity, explanation, adverse`.

## Sample output

```
INS-0004  High    trend             ANC Coverage in Ahmedabad dropped by 18.8% vs 2026-07 (85% → 69%), past the 10% threshold.
INS-0005  High    outlier           Mehsana's ANC Coverage of 42% sits outside the IQR fence (69.9% to 92.9%), 48% below the median.
INS-0011  Medium  correlation       Monthly shifts in ANC Coverage and High Risk Cases are inverse (r = -0.98, n = 6, small sample), driven by Mehsana.
```

Full list: `output/insights.json`

## Limitations

- **12 rows (2 months × 6 districts) is a very small sample.** The level correlations use n = 12, and the change correlations use n = 6. Treat them as hints, not evidence. The matrix is shown as it is, and small samples are labelled in the text.
- With n = 12, the largest Z-score possible is about 3.2, so a Z cutoff of 3 rarely fires. IQR or robust Z works better at this size, which is why IQR is the default.
- Trends compare consecutive months only. With 3+ months, a rolling baseline would be more stable.

## Images

Hero photos come from [Unsplash](https://unsplash.com) and are picked at random from a pool that matches the indicator in focus (maternal care, delivery, vaccination, clinical). Each photo is credited in the UI.
