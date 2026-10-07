from __future__ import annotations

import io
import random
import re
import sys
from dataclasses import dataclass, field

import pandas as pd
from nicegui import events, ui

import engine as eng

ALL = "__all__"
INK, MUTED, LINE = "#15171a", "#6c6f76", "#e8e5de"
SEVERITY = {"High": "#e5484d", "Medium": "#e8930c", "Low": "#5b8def"}
SERIES = ["#0d6e5f", "#e07a3f", "#5b6ee1", "#c2417a", "#2f9e8f", "#b08a2e", "#7a5af8", "#3d8bd9", "#d6604d", "#4c956c"]
KINDS = {"trend": ("Trend", "show_chart"), "outlier": ("Outlier", "scatter_plot"),
         "correlation": ("Correlation", "hub"), "threshold_breach": ("Breach", "flag")}

UNSPLASH = "https://images.unsplash.com/photo-{}?auto=format&fit=crop&w=2000&q=80"
PHOTOS = {
    "maternal": [
        ("1632053652571-a6a45052bbbd", "CDC", "a-doctor-talking-to-a-pregnant-woman-in-a-waiting-room-c8fnD1rKGCk"),
        ("1739287376717-91c8f1fe89c1", "Jawn Gangte", "a-pregnant-woman-sitting-in-a-field-at-sunset-FUYvr9IZZIc"),
        ("1615473986468-e3ebf02e9e3d", "Amit Ranjan", "woman-in-red-shirt-carrying-baby-jX1iAUoXvFU"),
    ],
    "delivery": [
        ("1632052999485-d748103abf98", "CDC", "a-woman-in-scrubs-is-holding-a-baby-d5NFf1SLguY"),
        ("1604807787527-e7ad386cca6a", "Gabriel Tovar", "man-in-blue-scrub-suit-holding-baby-Hr01AKr8DG8"),
        ("1610401162696-dad858f5b16d", "engin akyurt", "man-in-green-scrub-suit-holding-baby-84fhDJI6Nfs"),
    ],
    "vaccine": [
        ("1576766125535-b04e15fd0273", "CDC", "girl-getting-vaccine-TDoPeUSOD1c"),
        ("1626955105848-742d9cfd0b50", "Parang Mehta", "white-and-black-labeled-bottle-6XIIfLEYw9M"),
        ("1612277795421-9bc7706a4a34", "CDC", "woman-in-black-crew-neck-t-shirt-wearing-white-face-mask-uN8TV9Pw2ik"),
    ],
    "clinical": [
        ("1676313030076-4ac0b37050fd", "Bermix Studio", "a-doctor-examining-a-childs-stomach-with-a-stethoscope-kinSYGfBSzc"),
        ("1505751172876-fa1923c5c528", "Hush Naidoo Jade Photography", "black-and-gray-stethoscope-yo01Z-9HQAw"),
        ("1517120026326-d87759a7b63b", "Hush Naidoo Jade Photography", "person-walking-on-hallway-in-blue-scrub-suit-near-incubator-ZCO_5Y29s8k"),
    ],
}
TOPICS = [
    (re.compile(r"anc|antenatal|pregnan|matern", re.I), "maternal"),
    (re.compile(r"deliver|birth|institution|neonat", re.I), "delivery"),
    (re.compile(r"immun|vaccin|dose", re.I), "vaccine"),
]

FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@500;600&display=swap" rel="stylesheet">
"""

CSS = """
:root { --bg:#f4f3ef; --card:#fff; --ink:#15171a; --muted:#6c6f76; --faint:#b3b5ba; --line:#e8e5de; --soft:#f8f7f4; }
html, body { background: var(--bg) !important; color: var(--ink); font-family: 'Geist', system-ui, -apple-system, sans-serif; -webkit-font-smoothing: antialiased; }
.q-field, .q-btn, .q-item, .q-menu, .q-uploader, .q-table { font-family: inherit; }
.nicegui-content { padding: 0 !important; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 20px; box-shadow: 0 1px 2px rgba(20,20,10,.03), 0 12px 32px -24px rgba(20,20,10,.18); }
.eyebrow { font-size: 11px; font-weight: 500; letter-spacing: .09em; text-transform: uppercase; color: var(--muted); }
.title { font-size: 15px; font-weight: 600; letter-spacing: -.01em; }
.muted { color: var(--muted); }
.num { font-family: 'Geist Mono', ui-monospace, monospace; font-feature-settings: 'tnum'; }
.brand { font-size: 19px; font-weight: 700; letter-spacing: -.03em; }
.brand-sub { font-size: 13px; color: var(--muted); padding-left: 10px; border-left: 1px solid var(--line); }
.brand-mark { width: 30px; height: 30px; border-radius: 9px; background: var(--ink); color: #fff; display: grid; place-items: center; }
.btn-dark { background: var(--ink) !important; color: #fff !important; border-radius: 12px; font-weight: 500; padding: 4px 14px; }
.btn-ghost { color: var(--ink) !important; border-radius: 12px; font-weight: 500; border: 1px solid var(--line); background: var(--card) !important; padding: 4px 14px; }
.hero { position: relative; border-radius: 28px; overflow: hidden; min-height: 340px; background-color: #1d2124; background-size: cover; background-position: center 35%; color: #fff; isolation: isolate; transition: background-image .4s ease; }
.hero::before { content: ''; position: absolute; inset: 0; z-index: -1; background: linear-gradient(95deg, rgba(9,12,14,.9) 0%, rgba(9,12,14,.64) 45%, rgba(9,12,14,.06) 100%); }
.hero-title { font-size: clamp(30px, 4.2vw, 46px); line-height: 1.04; font-weight: 600; letter-spacing: -.035em; }
.hero-sub { font-size: 15.5px; line-height: 1.55; color: rgba(255,255,255,.8); }
.glass { background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.2); backdrop-filter: blur(10px); border-radius: 999px; padding: 6px 12px; font-size: 12.5px; }
.credit { font-size: 11.5px; color: rgba(255,255,255,.72) !important; text-decoration: none; }
.credit:hover { color: #fff !important; }
.tile { padding: 18px 20px; min-width: 0; }
.tile-value { font-size: 28px; font-weight: 600; letter-spacing: -.03em; margin-top: 6px; line-height: 1.15; }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 500; color: var(--muted); background: var(--soft); border: 1px solid var(--line); cursor: pointer; user-select: none; transition: all .15s ease; }
.pill:hover { color: var(--ink); border-color: #d4d0c6; }
.pill.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.pill-count { font-family: 'Geist Mono', monospace; font-size: 11.5px; opacity: .55; }
.signal { border-top: 1px solid var(--line); transition: background .15s ease; }
.signal:hover { background: var(--soft); }
.signal-icon { width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center; flex-shrink: 0; }
.signal-text { font-size: 14.5px; line-height: 1.5; }
.meta { display: flex; flex-wrap: wrap; gap: 2px 8px; font-size: 12.5px; color: var(--muted); margin-top: 6px; }
.meta > *:not(:last-child)::after { content: '·'; margin-left: 8px; color: var(--faint); }
.signal-num { font-size: 15px; font-weight: 600; }
.sev { display: inline-block; margin-top: 6px; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.knob-value { font-family: 'Geist Mono', monospace; font-size: 12px; background: var(--soft); border: 1px solid var(--line); padding: 1px 8px; border-radius: 8px; }
.q-field--outlined .q-field__control { border-radius: 12px; }
.q-field--outlined .q-field__control:before { border-color: var(--line); }
.seg { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.seg .q-btn { font-weight: 500; font-size: 13px; }
.stat-grid > div { background: var(--soft); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; }
.note { font-size: 12.5px; line-height: 1.45; color: var(--muted); display: flex; gap: 8px; }
.fade { animation: fade .35s ease both; }
@keyframes fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.scroll-thin::-webkit-scrollbar { width: 8px; }
.scroll-thin::-webkit-scrollbar-thumb { background: #dcd8cf; border-radius: 8px; }
"""

AXIS = {"axisLine": {"lineStyle": {"color": LINE}}, "axisTick": {"show": False}, "axisLabel": {"color": MUTED, "fontSize": 11.5}}
TOOLTIP = {"backgroundColor": INK, "borderWidth": 0, "padding": [8, 12], "textStyle": {"color": "#fff", "fontSize": 12}}


def topic(indicator: str | None) -> str:
    return next((name for pattern, name in TOPICS if indicator and pattern.search(indicator)), "clinical")


def month_name(period: str) -> str:
    return pd.Timestamp(f"{period}-01").strftime("%b %Y")


def months_span(periods: list[str]) -> str:
    if not periods:
        return "No data"
    first, last = pd.Timestamp(f"{periods[0]}-01"), pd.Timestamp(f"{periods[-1]}-01")
    if first == last:
        return first.strftime("%b %Y")
    return f"{first:%b} – {last:%b %Y}" if first.year == last.year else f"{first:%b %Y} – {last:%b %Y}"


def pair_label(indicator: str) -> str:
    return " × ".join(eng.label(part) for part in indicator.split(":"))


def figure(row) -> str:
    if row.type == "correlation":
        return f"r {row.value:+.2f}"
    if pd.notna(row.change_pct):
        return f"{row.change_pct:+.1f}%"
    return f"{row.score:+.1f}"


@dataclass
class State:
    ds: eng.Dataset
    settings: eng.Settings = field(default_factory=eng.Settings)
    districts: list[str] = field(default_factory=list)
    month: str = ALL
    indicator: str = ALL
    kind: str = ALL
    matrix: str = "levels"
    photo: tuple[str, str, str] | None = None
    photo_topic: str = ""
    result: eng.Result | None = None

    def use(self, ds: eng.Dataset) -> None:
        self.ds = ds
        self.settings.lower_better = eng.lower_defaults(ds)
        self.districts, self.month, self.indicator, self.kind = list(ds.entities), ALL, ALL, ALL
        self.run()

    def run(self) -> None:
        self.result = eng.analyze(self.ds, self.settings)

    def view(self) -> pd.DataFrame:
        df = self.result.insights
        df = df[df["entity"].isin(self.districts)]
        if self.month != ALL:
            df = df[(df["period"] == self.month) | (df["type"] == "correlation")]
        if self.indicator != ALL:
            df = df[df["indicator"].str.split(":").map(lambda parts: self.indicator in parts)]
        return df

    def focus(self, view: pd.DataFrame) -> str:
        if self.indicator != ALL:
            return self.indicator
        single = view.loc[view["type"] != "correlation", "indicator"]
        return single.iloc[0] if len(single) else self.ds.indicators[0]

    def pick_photo(self, indicator: str, shuffle: bool = False) -> tuple[str, str, str]:
        name = topic(indicator)
        if shuffle or self.photo is None or name != self.photo_topic:
            pool = [p for p in PHOTOS[name] if p != self.photo] or PHOTOS[name]
            self.photo, self.photo_topic = random.choice(pool), name
        return self.photo


def card(extra: str = ""):
    return ui.element("div").classes(f"card {extra}")


def pill(text: str, active: bool, handler, count: int | None = None):
    with ui.element("div").classes("pill on" if active else "pill").on("click", handler) as element:
        ui.label(text)
        if count is not None:
            ui.label(str(count)).classes("pill-count")
    return element


def line_options(state: State, view: pd.DataFrame, column: str) -> dict:
    ds, s = state.ds, state.settings
    rate = eng.is_rate(ds, column, s.lower_better)
    unit = "%" if rate else ""
    touched = view["indicator"].str.split(":").map(lambda parts: column in parts)
    flagged = set(view.loc[touched & view["adverse"], "entity"])
    series = []
    for i, district in enumerate(ds.entities):
        if district not in state.districts:
            continue
        values = ds.frame[ds.frame[ds.entity] == district].set_index(ds.time)[column].reindex(ds.periods)
        hot, color = district in flagged, SERIES[i % len(SERIES)]
        series.append({
            "name": district, "type": "line", "connectNulls": True, "symbol": "circle",
            "symbolSize": 9 if hot else 6, "emphasis": {"focus": "series"},
            "data": [None if pd.isna(v) else round(float(v), 2) for v in values],
            "lineStyle": {"width": 3 if hot else 1.6, "opacity": 1 if hot else 0.35},
            "itemStyle": {"color": color, "opacity": 1 if hot else 0.5},
            "endLabel": {"show": hot, "formatter": "{a}", "color": color, "fontWeight": 600, "fontSize": 12},
        })
    if series and rate:
        series[0]["markLine"] = {
            "silent": True, "symbol": "none", "data": [{"yAxis": s.target}],
            "lineStyle": {"type": "dashed", "color": "#a3a6ad", "width": 1},
            "label": {"formatter": f"Target {s.target:g}%", "position": "insideEndTop", "color": MUTED, "fontSize": 11},
        }
    if series and state.month != ALL:
        series[0]["markArea"] = {"silent": True, "itemStyle": {"color": "rgba(13,110,95,.06)"},
                                 "data": [[{"xAxis": month_name(state.month)}, {"xAxis": month_name(state.month)}]]}
    return {
        "animationDuration": 600, "textStyle": {"fontFamily": "Geist, system-ui, sans-serif"},
        "grid": {"left": 8, "right": 96, "top": 44, "bottom": 8, "containLabel": True},
        "tooltip": {"trigger": "axis", **TOOLTIP},
        "legend": {"top": 0, "left": 0, "icon": "circle", "itemWidth": 8, "itemHeight": 8, "itemGap": 14,
                   "textStyle": {"color": MUTED, "fontSize": 12}},
        "xAxis": {"type": "category", "boundaryGap": False, "data": [month_name(p) for p in ds.periods], **AXIS},
        "yAxis": {"type": "value", "scale": True, "splitLine": {"lineStyle": {"color": "#f0eee9"}},
                  "axisLabel": {"color": MUTED, "fontSize": 11.5, "formatter": "{value}" + unit}},
        "series": series,
    }


def severity_options(view: pd.DataFrame) -> dict:
    counts = view["severity"].value_counts()
    return {
        "animationDuration": 500, "textStyle": {"fontFamily": "Geist, system-ui, sans-serif"},
        "grid": {"left": 4, "right": 4, "top": 28, "bottom": 4, "containLabel": True},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "none"}, **TOOLTIP},
        "xAxis": {"type": "category", "data": list(SEVERITY), **AXIS},
        "yAxis": {"type": "value", "minInterval": 1, "splitLine": {"lineStyle": {"color": "#f0eee9"}},
                  "axisLabel": {"color": MUTED, "fontSize": 11.5}},
        "series": [{
            "type": "bar", "barWidth": "44%", "name": "Signals",
            "label": {"show": True, "position": "top", "color": INK, "fontWeight": 600, "fontFamily": "Geist Mono"},
            "data": [{"value": int(counts.get(k, 0)), "itemStyle": {"color": c, "borderRadius": [10, 10, 4, 4]}}
                     for k, c in SEVERITY.items()],
        }],
    }


def heatmap_options(matrix: pd.DataFrame, threshold: float) -> dict:
    names = [eng.label(c).replace(" ", "\n") for c in matrix.columns]
    data = []
    for i in range(len(names)):
        for j in range(len(names)):
            r = matrix.iat[i, j]
            v = None if pd.isna(r) else round(float(r), 2)
            if i == j:
                data.append({"value": [j, i, v], "itemStyle": {"color": "#efede8"}, "label": {"color": "#a3a6ad"}})
                continue
            strong = v is not None and abs(v) >= 0.6
            hit = v is not None and abs(v) >= threshold
            data.append({"value": [j, i, v], "label": {"color": "#fff" if strong else INK, "fontWeight": 700 if hit else 400}})
    return {
        "animationDuration": 500, "textStyle": {"fontFamily": "Geist, system-ui, sans-serif"},
        "grid": {"left": 4, "right": 4, "top": 4, "bottom": 4, "containLabel": True},
        "tooltip": {**TOOLTIP, ":formatter": "p => p.value[2] == null ? 'n/a' : 'r = ' + p.value[2].toFixed(2)"},
        "xAxis": {"type": "category", "data": names, "position": "top", **AXIS, "axisLine": {"show": False}},
        "yAxis": {"type": "category", "data": names, "inverse": True, **AXIS, "axisLine": {"show": False}},
        "visualMap": {"show": False, "min": -1, "max": 1,
                      "inRange": {"color": ["#c8553d", "#f1d3c7", "#f7f6f2", "#cfe7e1", "#0d6e5f"]}},
        "series": [{
            "type": "heatmap", "data": data,
            "label": {"show": True, "fontFamily": "Geist Mono", "fontSize": 12,
                      ":formatter": "p => p.value[2] == null ? '–' : p.value[2].toFixed(2)"},
            "itemStyle": {"borderColor": "#fff", "borderWidth": 3, "borderRadius": 8},
        }],
    }


@ui.page("/")
def index() -> None:
    ui.add_head_html(FONTS)
    ui.add_css(CSS)
    ui.colors(primary="#0d6e5f", dark=INK)

    state = State(eng.load())
    state.use(state.ds)
    refs: dict[str, ui.element] = {}

    def redraw() -> None:
        summary.refresh()
        panels.refresh()

    def rerun() -> None:
        state.run()
        redraw()

    def set_setting(key: str, value) -> None:
        setattr(state.settings, key, value)
        rerun()

    def set_view(key: str, value) -> None:
        setattr(state, key, value)
        redraw()

    def toggle_district(name: str) -> None:
        chosen = set(state.districts)
        chosen = {name} if len(chosen) == len(state.ds.entities) else chosen ^ {name}
        state.districts = [d for d in state.ds.entities if d in chosen] or list(state.ds.entities)
        district_pills.refresh()
        redraw()

    def all_districts() -> None:
        state.districts = list(state.ds.entities)
        district_pills.refresh()
        redraw()

    def shuffle() -> None:
        pid = state.pick_photo(state.photo_topic, shuffle=True)[0]
        refs["hero"].style(f"background-image:url('{UNSPLASH.format(pid)}')")
        hero_image.refresh()

    def reload(ds: eng.Dataset, message: str) -> None:
        state.use(ds)
        controls.refresh()
        redraw()
        ui.notify(message, type="positive", position="top")

    async def handle_upload(e: events.UploadEventArguments) -> None:
        try:
            ds = eng.load(io.BytesIO(await e.file.read()), e.file.name)
        except ValueError as err:
            ui.notify(f"Couldn't read {e.file.name}: {err}", type="negative", position="top")
            return
        upload_dialog.close()
        e.sender.reset()
        reload(ds, f"Loaded {e.file.name}")

    def export(kind: str) -> None:
        r = state.result
        files = {
            "csv": (r.insights.to_csv(index=False), "insights.csv"),
            "json": (r.insights.to_json(orient="records", indent=2), "insights.json"),
            "matrix": (r.levels.round(4).to_csv(), "correlation_matrix.csv"),
        }
        ui.download.content(*files[kind])

    with ui.dialog() as upload_dialog, ui.card().classes("p-6 w-[440px] max-w-full rounded-[20px] gap-3"):
        ui.label("Load a CSV").classes("title")
        ui.label("A month column, a district column, any numeric indicators.").classes("muted text-[13px]")
        ui.upload(on_upload=handle_upload, auto_upload=True, max_files=1) \
            .props('accept=".csv" flat bordered color=dark').classes("w-full")
        ui.button("Use sample data", on_click=lambda: (upload_dialog.close(), reload(eng.load(), "Sample data restored"))) \
            .props("flat no-caps dense").classes("self-start muted")

    @ui.refreshable
    def hero_image() -> None:
        _, author, slug = state.photo
        with ui.element("div").classes("absolute right-4 bottom-4 flex items-center gap-1"):
            ui.link(f"Photo · {author} / Unsplash", f"https://unsplash.com/photos/{slug}?utm_source=pulse&utm_medium=referral",
                    new_tab=True).classes("credit")
            ui.button(icon="shuffle", on_click=shuffle).props("round flat dense size=sm color=white").tooltip("Another photo")

    @ui.refreshable
    def summary() -> None:
        ds, view = state.ds, state.view()
        state.pick_photo(state.focus(view))
        counts = view["severity"].value_counts()
        high, medium = int(counts.get("High", 0)), int(counts.get("Medium", 0))
        top = view.iloc[0] if len(view) else None

        hero = refs["hero"] = ui.element("section").classes("hero fade mt-6 p-7 md:p-10 flex flex-col justify-end")
        hero.style(f"background-image:url('{UNSPLASH.format(state.photo[0])}')")
        with hero:
            ui.label(f"{months_span(ds.periods)}  ·  {len(ds.entities)} districts  ·  {len(ds.indicators)} indicators") \
                .classes("glass self-start")
            ui.label(f"{high} high-severity signal{'' if high == 1 else 's'}" if high else "Nothing urgent") \
                .classes("hero-title mt-5 max-w-[680px]")
            ui.label(top.explanation if top is not None else "No signals at these thresholds.") \
                .classes("hero-sub mt-3 max-w-[600px] pb-6 md:pb-2")
            hero_image()

        adverse = view[view["adverse"]]
        moves = view[view["type"] == "trend"]
        sharp = moves.loc[moves["change_pct"].abs().idxmax()] if len(moves) else None
        hotspot = adverse["entity"].value_counts()
        tiles = [
            ("Signals", str(len(view)), f"{high} high · {medium} medium", None),
            ("Districts flagged", f"{adverse['entity'].nunique()}/{len(state.districts)}", "with adverse signals", None),
            ("Sharpest move", f"{sharp.change_pct:+.1f}%" if sharp is not None else "—",
             f"{sharp.entity} · {eng.label(sharp.indicator)}" if sharp is not None else "No trend flagged",
             SEVERITY["High"] if sharp is not None and sharp.adverse else None),
            ("Most flagged", hotspot.index[0] if len(hotspot) else "—",
             f"{hotspot.iloc[0]} adverse signals" if len(hotspot) else "All clear", None),
        ]
        with ui.element("div").classes("grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4 fade"):
            for eyebrow, value, caption, accent in tiles:
                with card("tile"):
                    ui.label(eyebrow).classes("eyebrow")
                    ui.label(value).classes("tile-value truncate").style(f"color:{accent}" if accent else "")
                    ui.label(caption).classes("muted text-[13px] mt-1 truncate")

    @ui.refreshable
    def district_pills() -> None:
        everyone = len(state.districts) == len(state.ds.entities)
        with ui.element("div").classes("flex flex-wrap gap-1.5"):
            pill("All", everyone, all_districts)
            for name in state.ds.entities:
                pill(name, not everyone and name in state.districts, lambda n=name: toggle_district(n))

    def knob(title: str, key: str, low: float, high: float, step: float, suffix: str = "", digits: int | None = None):
        with ui.element("div").classes("w-full") as box:
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                ui.label(title).classes("text-[13px] font-medium")
                readout = ui.label().classes("knob-value")
            slider = ui.slider(min=low, max=high, step=step, value=getattr(state.settings, key)) \
                .props('color=dark thumb-size="16px" track-size="4px"').classes("mt-1")
            slider.on("change", lambda e: set_setting(key, e.args))
            readout.bind_text_from(slider, "value", lambda v: (f"{v:.{digits}f}" if digits else f"{v:g}") + suffix)
        return box

    @ui.refreshable
    def controls() -> None:
        ds, s = state.ds, state.settings
        with card("p-5 flex flex-col gap-4"):
            ui.label("Filters").classes("eyebrow")
            district_pills()
            months = {ALL: "All months", **{p: month_name(p) for p in ds.periods}}
            ui.select(months, value=state.month, label="Month", on_change=lambda e: set_view("month", e.value)) \
                .props("outlined dense options-dense").classes("w-full")
            indicators = {ALL: "All indicators", **{c: eng.label(c) for c in ds.indicators}}
            ui.select(indicators, value=state.indicator, label="Indicator", on_change=lambda e: set_view("indicator", e.value)) \
                .props("outlined dense options-dense").classes("w-full")

        with card("p-5 flex flex-col gap-4 mt-4"):
            ui.label("Thresholds").classes("eyebrow")
            knob("Significant change", "trend_pct", 1, 50, 1, "%")
            method = ui.toggle(eng.METHODS, value=s.method, on_change=lambda e: set_setting("method", e.value)) \
                .props("no-caps unelevated spread toggle-color=dark color=white text-color=grey-8").classes("seg w-full")
            knob("IQR multiplier", "iqr_k", 0.5, 3, 0.1, "×").bind_visibility_from(method, "value", value="iqr")
            knob("Z-score cutoff", "z", 1, 4, 0.1, "σ").bind_visibility_from(method, "value", value="zscore")
            knob("Robust Z cutoff", "robust_z", 1, 6, 0.1, "σ").bind_visibility_from(method, "value", value="robust")
            knob("Correlation |r|", "corr_r", 0.3, 0.99, 0.01, digits=2)
            knob("Coverage target", "target", 50, 100, 1, "%")
            ui.select({c: eng.label(c) for c in ds.indicators}, value=list(s.lower_better), multiple=True,
                      label="Lower is better", on_change=lambda e: set_setting("lower_better", list(e.value or []))) \
                .props("outlined dense options-dense use-chips").classes("w-full")

        with ui.dialog() as inspect, ui.card().classes("p-6 w-[760px] max-w-full rounded-[20px] gap-4"):
            ui.label(ds.name).classes("title")
            ui.label("head()").classes("eyebrow")
            ui.table.from_pandas(ds.raw.head()).props("flat bordered dense").classes("w-full")
            ui.label("info() · missing").classes("eyebrow")
            info = pd.DataFrame({
                "column": ds.raw.columns, "dtype": [str(t) for t in ds.raw.dtypes],
                "non_null": ds.raw.notna().sum().values, "missing": ds.raw.isna().sum().values,
            })
            ui.table.from_pandas(info).props("flat bordered dense").classes("w-full")

        with card("p-5 flex flex-col gap-3 mt-4"):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                ui.label("Dataset").classes("eyebrow")
                ui.button("Inspect", icon="table_rows", on_click=inspect.open).props("flat dense no-caps size=sm color=dark")
            ui.label(ds.name).classes("font-medium truncate")
            with ui.element("div").classes("stat-grid grid grid-cols-3 gap-2"):
                for value, name in ((len(ds.raw), "rows"), (len(ds.entities), "districts"), (sum(ds.missing.values()), "missing")):
                    with ui.element("div"):
                        ui.label(str(value)).classes("num text-[17px] font-semibold")
                        ui.label(name).classes("muted text-[11.5px]")
            for note in ds.warnings:
                with ui.element("div").classes("note"):
                    ui.icon("info", size="16px").classes("mt-[1px]")
                    ui.label(note)

    @ui.refreshable
    def panels() -> None:
        view = state.view()
        column = state.focus(view)
        feed = view if state.kind == ALL else view[view["type"] == state.kind]

        with ui.element("div").classes("flex flex-col gap-6 fade"):
            with card("p-5"):
                with ui.row().classes("w-full items-end justify-between"):
                    with ui.element("div"):
                        ui.label("By district").classes("eyebrow")
                        ui.label(eng.label(column)).classes("title mt-1")
                    if state.indicator == ALL:
                        ui.label("Auto-focused on top signal").classes("muted text-[12.5px]")
                ui.echart(line_options(state, view, column)).classes("w-full h-[320px] mt-3")

            with card("overflow-hidden"):
                with ui.element("div").classes("flex flex-wrap items-center justify-between gap-3 px-5 pt-5 pb-4"):
                    with ui.row().classes("items-baseline gap-2"):
                        ui.label("Signals").classes("title")
                        ui.label(str(len(view))).classes("muted num text-[13px]")
                    with ui.element("div").classes("flex flex-wrap gap-1.5"):
                        pill("All", state.kind == ALL, lambda: set_view("kind", ALL), len(view))
                        for key, (name, _) in KINDS.items():
                            pill(name, state.kind == key, lambda k=key: set_view("kind", k), int((view["type"] == key).sum()))
                with ui.element("div").classes("max-h-[640px] overflow-y-auto scroll-thin"):
                    if feed.empty:
                        with ui.element("div").classes("signal flex flex-col items-center gap-2 py-14 muted"):
                            ui.icon("check_circle", size="28px")
                            ui.label("No signals at these thresholds")
                    for row in feed.itertuples():
                        color = SEVERITY[row.severity]
                        icon = KINDS[row.type][1]
                        if row.type == "trend":
                            icon = "trending_up" if row.change_pct > 0 else "trending_down"
                        with ui.element("div").classes("signal flex items-start gap-4 px-5 py-4"):
                            with ui.element("div").classes("signal-icon").style(f"color:{color};background:{color}17"):
                                ui.icon(icon, size="20px")
                            with ui.element("div").classes("flex-1 min-w-0"):
                                ui.label(row.explanation).classes("signal-text")
                                with ui.element("div").classes("meta"):
                                    for part in (row.entity, row.period, pair_label(row.indicator), KINDS[row.type][0], row.insight_id):
                                        ui.label(part)
                            with ui.element("div").classes("text-right shrink-0"):
                                ui.label(figure(row)).classes("num signal-num").style(f"color:{color if row.adverse else INK}")
                                ui.label(row.severity).classes("sev").style(f"color:{color};background:{color}1c")

            with ui.element("div").classes("grid gap-6 md:grid-cols-5"):
                with card("p-5 md:col-span-2"):
                    ui.label("Severity").classes("eyebrow")
                    ui.label(f"{len(view)} signals").classes("title mt-1")
                    ui.echart(severity_options(view)).classes("w-full h-[280px] mt-2")
                with card("p-5 md:col-span-3"):
                    with ui.row().classes("w-full items-start justify-between"):
                        with ui.element("div"):
                            ui.label("Pearson correlation").classes("eyebrow")
                            ui.label(f"|r| ≥ {state.settings.corr_r:.2f} in bold").classes("title mt-1")
                        with ui.element("div").classes("flex gap-1.5"):
                            pill("Levels", state.matrix == "levels", lambda: set_view("matrix", "levels"))
                            pill("Changes", state.matrix == "changes", lambda: set_view("matrix", "changes"))
                    matrix = state.result.levels if state.matrix == "levels" else state.result.changes
                    ui.echart(heatmap_options(matrix, state.settings.corr_r)).classes("w-full h-[300px] mt-3")

    with ui.element("div").classes("w-full max-w-[1320px] mx-auto px-4 md:px-8 pt-6 pb-16"):
        with ui.element("header").classes("flex items-center justify-between gap-4"):
            with ui.row().classes("items-center gap-2.5 no-wrap"):
                with ui.element("div").classes("brand-mark"):
                    ui.icon("monitor_heart", size="18px")
                ui.label("Pulse").classes("brand")
                ui.label("Insight Engine").classes("brand-sub hidden sm:block")
            with ui.row().classes("items-center gap-2 no-wrap"):
                ui.button("Upload", icon="upload_file", on_click=upload_dialog.open).props("flat no-caps color=dark").classes("btn-ghost")
                with ui.button("Export", icon="download").props("unelevated no-caps color=dark").classes("btn-dark"):
                    with ui.menu().props("auto-close"):
                        ui.menu_item("Insights · CSV", lambda: export("csv"))
                        ui.menu_item("Insights · JSON", lambda: export("json"))
                        ui.menu_item("Correlation matrix · CSV", lambda: export("matrix"))
        summary()
        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6"):
            with ui.element("aside").classes("lg:col-span-3 lg:sticky lg:top-6 self-start"):
                controls()
            with ui.element("main").classes("lg:col-span-9 min-w-0"):
                panels()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Pulse · Insight Engine", favicon="🩺", port=8080, reload=False,
           show="--no-browser" not in sys.argv)
