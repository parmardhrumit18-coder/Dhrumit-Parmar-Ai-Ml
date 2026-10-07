from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
SAMPLE = ROOT / "data" / "health.csv"
OUTPUT = ROOT / "output"

TIME_NAMES = ("month", "period", "date", "year_month")
LOWER_IS_BETTER = re.compile(r"risk|case|death|mortal|dropout|anaemi|anemi|stunt|wast|fail|incident", re.I)
SMALL_WORDS = {"of", "and", "per", "to", "in", "by"}
LEVELS = ("Low", "Medium", "High")
TYPES = ("trend", "outlier", "correlation", "threshold_breach")
METHODS = {"iqr": "IQR", "zscore": "Z-score", "robust": "Robust"}
COLUMNS = [
    "insight_id", "type", "indicator", "entity", "period", "value", "prev_value",
    "change_pct", "metric", "score", "severity", "explanation", "adverse",
]
STABLE_N = 10


@dataclass
class Settings:
    trend_pct: float = 10.0
    method: str = "iqr"
    iqr_k: float = 1.5
    z: float = 3.0
    robust_z: float = 3.5
    corr_r: float = 0.70
    target: float = 80.0
    lower_better: list[str] | None = None

    @property
    def cutoff(self) -> float:
        return {"iqr": self.iqr_k, "zscore": self.z, "robust": self.robust_z}[self.method]


@dataclass
class Dataset:
    raw: pd.DataFrame
    frame: pd.DataFrame
    time: str
    entity: str
    indicators: list[str]
    name: str
    duplicates: int = 0

    @property
    def periods(self) -> list[str]:
        return sorted(self.frame[self.time].unique())

    @property
    def entities(self) -> list[str]:
        return sorted(self.frame[self.entity].unique())

    @property
    def missing(self) -> dict[str, int]:
        return {k: int(v) for k, v in self.raw.isna().sum().items()}

    @property
    def warnings(self) -> list[str]:
        notes = []
        if len(self.periods) < 3:
            notes.append(f"{len(self.periods)} months loaded, 3+ recommended for trends")
        if len(self.entities) < STABLE_N:
            notes.append(f"{len(self.entities)} districts loaded, {STABLE_N}+ recommended for stable correlations")
        if self.duplicates:
            notes.append(f"{self.duplicates} duplicate district-month rows merged")
        if sum(self.missing.values()):
            notes.append(f"{sum(self.missing.values())} missing values skipped")
        return notes


@dataclass
class Result:
    insights: pd.DataFrame
    levels: pd.DataFrame
    changes: pd.DataFrame
    lower_better: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        found = self.insights["severity"].value_counts()
        return {level: int(found.get(level, 0)) for level in reversed(LEVELS)}


def label(column: str) -> str:
    words = column.split("_")
    return " ".join(w if w in SMALL_WORDS else w.upper() if len(w) <= 3 else w.capitalize() for w in words)


def numeric_share(series: pd.Series) -> float:
    return pd.to_numeric(series, errors="coerce").notna().mean()


def load(source: str | Path | object = SAMPLE, name: str | None = None) -> Dataset:
    raw = pd.read_csv(source)
    raw.columns = [str(c).strip().lower().replace(" ", "_") for c in raw.columns]
    time = next((c for c in raw.columns if c in TIME_NAMES), raw.columns[0])
    entity = next((c for c in raw.columns if c != time and numeric_share(raw[c]) < 0.5), None)
    if entity is None:
        raise ValueError("No text column found for districts")
    indicators = [c for c in raw.columns if c not in (time, entity) and numeric_share(raw[c]) >= 0.8]
    if not indicators:
        raise ValueError("No numeric indicator columns found")

    frame = raw[[time, entity, *indicators]].copy()
    frame[time] = pd.to_datetime(frame[time].astype(str), errors="coerce").dt.strftime("%Y-%m")
    frame[entity] = frame[entity].astype(str).str.strip()
    frame[indicators] = frame[indicators].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=[time, entity])
    if frame.empty:
        raise ValueError(f"No valid dates in '{time}'")
    duplicates = int(frame.duplicated([entity, time]).sum())
    frame = frame.groupby([entity, time], as_index=False)[indicators].mean()
    frame = frame.sort_values([entity, time]).reset_index(drop=True)
    return Dataset(raw, frame, time, entity, indicators, name or Path(str(source)).name, duplicates)


def grade(ratio: float, shift: int = 0) -> str:
    level = 2 if ratio >= 1.5 else 1 if ratio >= 1.2 else 0
    return LEVELS[min(max(level + shift, 0), 2)]


def is_rate(ds: Dataset, column: str, lower: list[str]) -> bool:
    values = ds.frame[column].dropna()
    return column not in lower and values.between(0, 100).all()


def fmt(value: float, unit: str = "") -> str:
    return f"{value:,.1f}".rstrip("0").rstrip(".") + unit


def span(periods: list[str]) -> str:
    first, last = periods[0], periods[-1]
    return first if first == last else f"{first}..{last[5:] if first[:4] == last[:4] else last}"


def insight(kind, column, entity, period, value, reference, change, metric, score, severity, text, adverse):
    return {
        "type": kind, "indicator": column, "entity": entity, "period": period,
        "value": round(float(value), 2), "prev_value": None if reference is None else round(float(reference), 2),
        "change_pct": None if change is None else round(float(change), 1), "metric": metric,
        "score": round(float(score), 2), "severity": severity, "explanation": text, "adverse": bool(adverse),
    }


def trends(ds: Dataset, s: Settings, lower: list[str]) -> list[dict]:
    f, rows = ds.frame, []
    groups = f.groupby(ds.entity)
    prev_period = groups[ds.time].shift(1)
    for col in ds.indicators:
        unit = "%" if is_rate(ds, col, lower) else ""
        prev = groups[col].shift(1)
        pct = ((f[col] - prev) / prev * 100).replace([np.inf, -np.inf], np.nan)
        for i in pct.index[pct.abs() >= s.trend_pct]:
            change, rising = pct[i], pct[i] > 0
            adverse = rising == (col in lower)
            text = (
                f"{label(col)} in {f.at[i, ds.entity]} {'rose' if rising else 'dropped'} by {abs(change):.1f}% "
                f"vs {prev_period[i]} ({fmt(prev[i], unit)} → {fmt(f.at[i, col], unit)}), "
                f"past the {s.trend_pct:g}% threshold."
            )
            ratio = abs(change) / s.trend_pct
            rows.append(insight("trend", col, f.at[i, ds.entity], f.at[i, ds.time], f.at[i, col], prev[i],
                                change, "pct_change", ratio, grade(ratio, 0 if adverse else -1), text, adverse))
    return rows


def outliers(ds: Dataset, s: Settings, lower: list[str]) -> list[dict]:
    rows, cut = [], s.cutoff
    for col in ds.indicators:
        unit = "%" if is_rate(ds, col, lower) else ""
        sub = ds.frame[[ds.entity, ds.time, col]].dropna()
        x = sub[col]
        if len(x) < 4:
            continue
        if s.method == "zscore":
            centre, spread = x.mean(), x.std()
            score = (x - centre) / spread
        elif s.method == "robust":
            centre = x.median()
            spread = (x - centre).abs().median()
            score = 0.6745 * (x - centre) / spread
        else:
            q1, q3 = x.quantile(0.25), x.quantile(0.75)
            centre, spread = x.median(), q3 - q1
            score = ((x - q3).clip(lower=0) - (q1 - x).clip(lower=0)) / spread
        if not np.isfinite(spread) or spread == 0:
            continue
        flagged = score.abs() > cut if s.method == "iqr" else score.abs() >= cut
        for i in score.index[flagged]:
            v, z = x[i], score[i]
            side = "below" if z < 0 else "above"
            who = f"{sub.at[i, ds.entity]}'s {label(col)} of {fmt(v, unit)}"
            if s.method == "iqr":
                lo, hi = q1 - cut * spread, q3 + cut * spread
                text = f"{who} sits outside the IQR fence ({fmt(lo, unit)} to {fmt(hi, unit)}), {abs(v - centre) / centre * 100:.0f}% {side} the median."
            elif s.method == "zscore":
                text = f"{who} is {abs(z):.1f}σ {side} the mean ({fmt(centre, unit)}), flagging for review."
            else:
                text = f"{who} is {abs(z):.1f} robust σ {side} the median ({fmt(centre, unit)}), flagging for review."
            adverse = (z < 0) != (col in lower)
            ratio = abs(z) / cut
            rows.append(insight("outlier", col, sub.at[i, ds.entity], sub.at[i, ds.time], v, centre,
                                (v - centre) / centre * 100 if centre else None,
                                {"iqr": "iqr_distance", "zscore": "z_score", "robust": "robust_z"}[s.method],
                                z, grade(ratio, 0 if adverse else -1), text, adverse))
    return rows


def correlate(ds: Dataset) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    levels = ds.frame[ds.indicators].corr(method="pearson")
    deltas = ds.frame.groupby(ds.entity)[ds.indicators].diff().dropna(how="all")
    return levels, deltas.corr(method="pearson"), deltas


def correlations(ds: Dataset, s: Settings, levels: pd.DataFrame, changes: pd.DataFrame, deltas: pd.DataFrame) -> list[dict]:
    rows, period = [], span(ds.periods)
    sources = (("levels", levels, ds.frame), ("changes", changes, deltas))
    for i, a in enumerate(ds.indicators):
        for b in ds.indicators[i + 1:]:
            for kind, matrix, data in sources:
                r = matrix.at[a, b]
                pair = data[[a, b]].dropna()
                n = len(pair)
                if n < 3 or not np.isfinite(r) or abs(r) < s.corr_r:
                    continue
                z = (pair - pair.mean()) / pair.std()
                lead = (z[a] * z[b] * np.sign(r)).idxmax()
                who = ds.frame.at[lead, ds.entity]
                stretch = (abs(r) - s.corr_r) / (1 - s.corr_r) if s.corr_r < 1 else 1
                level = 2 if stretch >= 2 / 3 else 1 if stretch >= 1 / 3 else 0
                caveat = "" if n >= STABLE_N else ", small sample"
                if kind == "levels":
                    text = (f"{label(a)} and {label(b)} move {'together' if r > 0 else 'in opposite directions'} "
                            f"(r = {r:+.2f}, n = {n}{caveat}), led by {who}.")
                else:
                    text = (f"Monthly shifts in {label(a)} and {label(b)} are {'aligned' if r > 0 else 'inverse'} "
                            f"(r = {r:+.2f}, n = {n}{caveat}), driven by {who}.")
                adverse = (r < 0) != ((a in s.lower_better) != (b in s.lower_better))
                rows.append(insight("correlation", f"{a}:{b}", who, period, r, None, None, f"pearson_r_{kind}",
                                    abs(r), LEVELS[max(level - (n < STABLE_N), 0)], text, adverse))
    return rows


def breaches(ds: Dataset, s: Settings, lower: list[str]) -> list[dict]:
    f, rows = ds.frame, []
    for col in [c for c in ds.indicators if is_rate(ds, c, lower)]:
        prev = f.groupby(ds.entity)[col].shift(1)
        for i in f.index[f[col] < s.target]:
            v = f.at[i, col]
            gap = (s.target - v) / s.target * 100
            fresh = bool(prev[i] >= s.target)
            text = (f"{f.at[i, ds.entity]}'s {label(col)} of {fmt(v, '%')} is {'newly ' if fresh else ''}"
                    f"below the {s.target:g}% target, {gap:.1f}% short.")
            ratio = gap / s.trend_pct
            rows.append(insight("threshold_breach", col, f.at[i, ds.entity], f.at[i, ds.time], v, s.target,
                                -gap, "gap_to_target", ratio, grade(ratio, int(fresh)), text, True))
    return rows


def lower_defaults(ds: Dataset) -> list[str]:
    return [c for c in ds.indicators if LOWER_IS_BETTER.search(c)]


def analyze(ds: Dataset, s: Settings | None = None) -> Result:
    s = replace(s) if s else Settings()
    if s.lower_better is None:
        s.lower_better = lower_defaults(ds)
    lower = s.lower_better
    levels, changes, deltas = correlate(ds)
    rows = [*trends(ds, s, lower), *outliers(ds, s, lower), *correlations(ds, s, levels, changes, deltas), *breaches(ds, s, lower)]
    out = pd.DataFrame(rows, columns=COLUMNS[1:])
    if not out.empty:
        out["_rank"] = out["severity"].map({k: i for i, k in enumerate(LEVELS)})
        out["_type"] = out["type"].map({k: i for i, k in enumerate(TYPES)})
        out["_mag"] = out["score"].abs()
        out = out.sort_values(["_rank", "adverse", "_type", "_mag"], ascending=[False, False, True, False])
        out = out.drop(columns=["_rank", "_type", "_mag"]).reset_index(drop=True)
    out.insert(0, "insight_id", [f"INS-{i:04d}" for i in range(1, len(out) + 1)])
    return Result(out, levels, changes, lower)


def export(result: Result, folder: Path = OUTPUT) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    result.insights.to_csv(folder / "insights.csv", index=False)
    result.insights.to_json(folder / "insights.json", orient="records", indent=2)
    result.levels.round(4).to_csv(folder / "correlation_matrix.csv")
    result.changes.round(4).to_csv(folder / "correlation_changes.csv")
    return folder


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated insights for district health indicators")
    parser.add_argument("csv", nargs="?", default=SAMPLE)
    parser.add_argument("--trend", type=float, default=10.0)
    parser.add_argument("--method", choices=list(METHODS), default="iqr")
    parser.add_argument("--corr", type=float, default=0.70)
    parser.add_argument("--target", type=float, default=80.0)
    args = parser.parse_args()

    ds = load(args.csv)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print("\n── head()\n", ds.raw.head(), sep="")
    print("\n── info()")
    ds.raw.info()
    print("\n── missing values\n", ds.raw.isna().sum().to_string(), sep="")
    for note in ds.warnings:
        print(f"! {note}")

    result = analyze(ds, Settings(trend_pct=args.trend, method=args.method, corr_r=args.corr, target=args.target))
    folder = export(result)
    print("\n── correlation matrix\n", result.levels.round(2), sep="")
    print(f"\n── {len(result.insights)} insights  ", "  ".join(f"{k} {v}" for k, v in result.counts().items()))
    for row in result.insights.itertuples():
        print(f"{row.insight_id}  {row.severity:<6}  {row.type:<16}  {row.explanation}")
    print(f"\nSaved to {folder}")


if __name__ == "__main__":
    main()
