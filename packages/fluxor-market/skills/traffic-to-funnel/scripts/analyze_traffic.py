#!/usr/bin/env python3
"""
analyze_traffic.py — Rankings and signals from normalized CSV exports (stdlib only).

Usage:
  python analyze_traffic.py --pages pages.csv [--elements elements.csv] [--search search.csv]
                            [--min-impressions 100] [--json out.json] [--md out.md]

Schemas are documented in references/data-sources.md. Only `url` is required in each
file; every other column is used when present. Thresholds are percentiles of the site
itself (P25 / P75), never absolute internet figures. The script does NOT interpret:
it produces rankings and flags so the analysis starts from numbers, not impressions.
"""
import argparse
import csv
import json
import math
import re
import sys

# Column aliases -> canonical English names (covers common tool exports and Spanish headers)
ALIAS = {
    "page": "url", "pagina": "url", "página": "url", "path": "url", "landing_page": "url", "page_path": "url",  # lang:es: Spanish export headers are accepted on purpose
    "vistas": "views", "pageviews": "views", "screen_pageviews": "views", "page_views": "views",
    "sesiones": "sessions", "visits": "sessions",
    "entradas": "entrances", "entries": "entrances", "salidas": "exits",  # lang:es: Spanish export headers are accepted on purpose
    "tiempo_medio_s": "avg_time_s", "avg_time": "avg_time_s", "average_engagement_time": "avg_time_s",  # lang:es: Spanish export headers are accepted on purpose
    "time_on_page": "avg_time_s", "avg_time_on_page": "avg_time_s",
    "conversiones": "conversions", "key_events": "conversions", "goals": "conversions", "goal_completions": "conversions",
    "impresiones": "impressions", "clics": "clicks", "posicion": "position", "posición": "position",  # lang:es: Spanish export headers are accepted on purpose
    "consulta": "query", "keyword": "query", "search_query": "query",
    "elemento": "element", "selector": "element", "element_id": "element", "tipo": "type",  # lang:es: Spanish export headers are accepted on purpose
    "rebotes": "bounces", "quick_back": "quick_backs",
}

# Indicative organic CTR by position (rough curve, only used to spot anomalous CTR)
EXPECTED_CTR = {1: .28, 2: .15, 3: .10, 4: .07, 5: .06, 6: .05, 7: .04, 8: .035, 9: .03, 10: .025}


# Number formats found in real exports. A group separator never follows a leading zero, so
# "0,125" and "0.125" are always decimals.
COMMA_THOUSANDS = re.compile(r"^[1-9]\d{0,2}(,\d{3})+(\.\d+)?$")  # 12,500  1,234,567  1,234.56
DOT_THOUSANDS = re.compile(r"^[1-9]\d{0,2}(\.\d{3})+(,\d+)?$")    # 12.500  1.234.567  1.234,56
DECIMAL_COMMA = re.compile(r"^\d*,\d+$")                           # 12,5  0,25  ,5
# Blanks, NBSP, narrow NBSP, thin space and apostrophe are only ever group separators.
GROUP_CHARS = str.maketrans("", "", " \u00a0\u202f\u2009'\u2019")
NUMBERISH = re.compile(r"^[+-]?[\d.,]*\d[\d.,]*%?$")


def _decimal_evidence(cell):
    """The decimal separator a cell proves, or None when it is ambiguous ("12,500", "1234")."""
    v = cell.translate(GROUP_CHARS).replace("%", "").lstrip("+-")
    has_comma, has_dot = "," in v, "." in v
    if has_comma and has_dot:
        return "," if v.rfind(",") > v.rfind(".") else "."
    for sep in (",", "."):
        if sep in v:
            if v.count(sep) > 1:
                return "." if sep == "," else ","  # repeated, so it groups thousands
            head, tail = v.split(sep)
            if len(tail) != 3 or not head or len(head) > 3 or head.startswith("0"):
                return sep  # "12.5", "0,125", "3.1416": only a decimal separator fits
    return None


def decimal_hint(rows):
    """The file's decimal separator when its cells agree on one, else None.

    Only a single group like "12,500" or "12.500" is ambiguous: it means 12500 with the other
    separator as decimal, or 12.5 with this one. A file is written in one locale, so any cell that
    settles the question ("45.2", "0,75", "1.234.567") settles it for the whole file.
    """
    seen = set()
    for row in rows:
        for k, v in row.items():
            if not k.startswith("_") and v and NUMBERISH.match(v.translate(GROUP_CHARS)):
                sep = _decimal_evidence(v)
                if sep:
                    seen.add(sep)
    return seen.pop() if len(seen) == 1 else None


def parse_number(value, decimal=None):
    """Parse an exported number: "12,500", "1.234.567", "1,234.56", "1.234,56", "12,5", "45%".

    `decimal` is the file's decimal separator from decimal_hint(); it only decides a single
    ambiguous group. Without it, a single group of three digits is read as thousands, which is
    what analytics exports mean by "12,500" or "12.500".
    """
    v = value.translate(GROUP_CHARS).replace("%", "")
    sign = ""
    if v[:1] in "+-":
        sign, v = v[:1], v[1:]
    if COMMA_THOUSANDS.match(v):
        if decimal == "," and v.count(",") == 1 and "." not in v:
            v = v.replace(",", ".")
        else:
            v = v.replace(",", "")
    elif DOT_THOUSANDS.match(v):
        if not (decimal == "." and v.count(".") == 1 and "," not in v):
            v = v.replace(".", "").replace(",", ".")
    elif DECIMAL_COMMA.match(v):
        v = v.replace(",", ".")
    elif "," in v and "." in v:
        # irregular grouping ("1234,567.8"): the last separator is the decimal one
        v = v.replace(".", "").replace(",", ".") if v.rfind(",") > v.rfind(".") else v.replace(",", "")
    try:
        return float(sign + v)
    except ValueError:
        return None


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        # Spreadsheets in decimal-comma locales export with ";" (or tabs): use what the header uses.
        header = f.readline()
        f.seek(0)
        delimiter = max((",", ";", "\t"), key=header.count)
        rows = []
        for row in csv.DictReader(f, delimiter=delimiter):
            clean = {}
            for k, v in row.items():
                if k is None:
                    continue
                k = k.strip().lower().replace(" ", "_")
                k = ALIAS.get(k, k)
                clean[k] = (v or "").strip()
            rows.append(clean)
    hint = decimal_hint(rows)
    for row in rows:
        row["_decimal"] = hint
    return rows


def num(row, key, default=None):
    v = row.get(key, "")
    if v == "":
        return default
    n = parse_number(v, row.get("_decimal"))
    return default if n is None else n


def percentile(values, p):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = (len(vals) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    return vals[int(k)] if f == c else vals[f] + (vals[c] - vals[f]) * (k - f)


def pct_rank(value, values):
    vals = [v for v in values if v is not None]
    if value is None or len(vals) < 2:
        return None
    return sum(1 for v in vals if v < value) / (len(vals) - 1)


def level(value, p25, p75):
    if value is None or p25 is None:
        return "no_data"
    if value >= p75:
        return "high"
    if value <= p25:
        return "low"
    return "medium"


def ratio(a, b):
    return (a / b) if (a is not None and b) else None


def r(x, d=3):
    return None if x is None else round(x, d)


# ---------------------------------------------------------------- pages
def analyze_pages(rows, min_sample):
    pages = []
    for row in rows:
        views, sess = num(row, "views"), num(row, "sessions")
        ent, ex = num(row, "entrances"), num(row, "exits")
        p = {
            "url": row.get("url", ""),
            "views": views, "sessions": sess, "entrances": ent, "exits": ex,
            "avg_time_s": num(row, "avg_time_s"),
            "scroll_50_pct": num(row, "scroll_50_pct"), "scroll_90_pct": num(row, "scroll_90_pct"),
            "conversions": num(row, "conversions"),
            "exit_rate": ratio(ex, views),
            "bounce_rate": ratio(num(row, "bounces"), ent),
            "quick_back_rate": ratio(num(row, "quick_backs"), ent),
            "conversion_rate": ratio(num(row, "conversions"), sess or views),
            "signals": [],
        }
        pages.append(p)

    # consumption score = mean of percentile ranks of views, time and scroll_90
    metrics = ("views", "avg_time_s", "scroll_90_pct")
    for m in metrics:
        col = [p[m] for p in pages]
        for p in pages:
            p["_r_" + m] = pct_rank(p[m], col)
    for p in pages:
        rs = [p["_r_" + m] for m in metrics if p["_r_" + m] is not None]
        p["consumption_score"] = r(sum(rs) / len(rs), 3) if rs else None

    def pc(col, q):
        return percentile([p[col] for p in pages], q)

    p25_s, p75_s = pc("consumption_score", .25), pc("consumption_score", .75)
    p75_exit, med_exit, med_conv = pc("exit_rate", .75), pc("exit_rate", .5), pc("conversion_rate", .5)
    p75_qb, p25_scroll, p75_scroll = pc("quick_back_rate", .75), pc("scroll_90_pct", .25), pc("scroll_90_pct", .75)
    p75_views = pc("views", .75)

    for p in pages:
        p["consumption"] = level(p["consumption_score"], p25_s, p75_s)
        if (p["views"] or 0) < min_sample:
            p["signals"].append("insufficient_sample")
            for k in list(p):
                if k.startswith("_r_"):
                    del p[k]
            continue
        low_conv = p["conversion_rate"] is None or (med_conv is not None and p["conversion_rate"] < med_conv)
        if p["exit_rate"] is not None and p75_exit is not None and p["exit_rate"] >= p75_exit and low_conv:
            p["signals"].append("leak")
        if p["quick_back_rate"] is not None and p75_qb and p["quick_back_rate"] >= p75_qb:
            p["signals"].append("high_quick_back")
        if p75_views is not None and (p["views"] or 0) >= p75_views and p["scroll_90_pct"] is not None \
                and p25_scroll is not None and p["scroll_90_pct"] <= p25_scroll:
            p["signals"].append("shallow_read")
        if p["scroll_90_pct"] is not None and p75_scroll is not None and p["scroll_90_pct"] >= p75_scroll \
                and p["exit_rate"] is not None and med_exit is not None and p["exit_rate"] >= med_exit and low_conv:
            p["signals"].append("no_next_step")
        for k in list(p):
            if k.startswith("_r_"):
                del p[k]
    pages.sort(key=lambda p: (p["consumption_score"] or 0), reverse=True)
    return pages, {"p25_score": r(p25_s), "p75_score": r(p75_s), "p75_exit_rate": r(p75_exit), "median_conversion": r(med_conv)}


# ---------------------------------------------------------------- elements
def analyze_elements(rows, min_impressions):
    els = []
    for row in rows:
        imp, cl = num(row, "impressions"), num(row, "clicks")
        e = {
            "url": row.get("url", ""), "element": row.get("element", ""), "type": row.get("type", ""),
            "impressions": imp, "clicks": cl,
            "rage_clicks": num(row, "rage_clicks", 0.0), "dead_clicks": num(row, "dead_clicks", 0.0),
            "error_clicks": num(row, "error_clicks", 0.0), "conversions": num(row, "conversions"),
            "ctr": ratio(cl, imp),
            "signals": [],
        }
        e["rage_rate"] = ratio(e["rage_clicks"], imp)
        e["dead_rate"] = ratio(e["dead_clicks"], imp)
        e["conv_per_click"] = ratio(e["conversions"], cl)
        els.append(e)

    valid = [e for e in els if (e["impressions"] or 0) >= min_impressions]
    p25_ctr, p75_ctr = percentile([e["ctr"] for e in valid], .25), percentile([e["ctr"] for e in valid], .75)
    p75_imp = percentile([e["impressions"] for e in valid], .75)
    p75_rage = percentile([e["rage_rate"] for e in valid if e["rage_rate"]], .75)
    p75_dead = percentile([e["dead_rate"] for e in valid if e["dead_rate"]], .75)

    for e in els:
        if (e["impressions"] or 0) < min_impressions:
            e["classification"] = "insufficient_sample"
            continue
        e["classification"] = {"high": "strong", "low": "weak", "medium": "medium", "no_data": "no_data"}[level(e["ctr"], p25_ctr, p75_ctr)]
        if e["classification"] == "weak" and p75_imp is not None and e["impressions"] >= p75_imp:
            e["signals"].append("high_exposure_low_interaction")
        if e["rage_clicks"] >= 5 and e["rage_rate"] and (e["rage_rate"] >= .01 or (p75_rage and e["rage_rate"] >= p75_rage)):
            e["signals"].append("rage_click")
        if e["dead_clicks"] >= 5 and e["dead_rate"] and (e["dead_rate"] >= .02 or (p75_dead and e["dead_rate"] >= p75_dead)):
            e["signals"].append("dead_click")
        if e["error_clicks"] >= 3:
            e["signals"].append("error_click")
        if e["classification"] == "strong" and e["conv_per_click"] is not None and e["conv_per_click"] == 0:
            e["signals"].append("attracts_but_no_conversion")
    els.sort(key=lambda e: (e["ctr"] or 0), reverse=True)
    return els, {"p25_ctr": r(p25_ctr), "p75_ctr": r(p75_ctr), "p75_impressions": r(p75_imp, 0)}


# ---------------------------------------------------------------- search
def expected_ctr(pos):
    if pos is None:
        return None
    p = int(round(pos))
    if p <= 0:
        return None
    if p in EXPECTED_CTR:
        return EXPECTED_CTR[p]
    return .015 if p <= 20 else .005


def analyze_search(rows, min_impressions):
    qs = []
    for row in rows:
        imp, cl, pos = num(row, "impressions"), num(row, "clicks"), num(row, "position")
        ctr = num(row, "ctr")
        if ctr is not None and ("%" in row.get("ctr", "") or ctr > 1):
            ctr = ctr / 100  # came as a percentage
        if ctr is None:
            ctr = ratio(cl, imp)
        q = {"url": row.get("url", ""), "query": row.get("query", ""), "impressions": imp, "clicks": cl,
             "position": pos, "ctr": r(ctr), "expected_ctr": expected_ctr(pos), "signals": []}
        if (imp or 0) >= min_impressions and pos is not None:
            if 4 <= pos <= 20:
                q["signals"].append("striking_distance")
            if q["expected_ctr"] and ctr is not None and ctr < q["expected_ctr"] * .5:
                q["signals"].append("low_ctr_for_position")
            if pos <= 3 and (imp or 0) >= min_impressions * 5:
                q["signals"].append("asset_to_defend")
        q["opportunity"] = r((imp or 0) * max((q["expected_ctr"] or 0) - (ctr or 0), 0), 1)
        qs.append(q)
    qs.sort(key=lambda q: q["opportunity"] or 0, reverse=True)
    by_url = {}
    for q in qs:
        u = by_url.setdefault(q["url"], {"url": q["url"], "impressions": 0, "clicks": 0, "queries": 0})
        u["impressions"] += q["impressions"] or 0
        u["clicks"] += q["clicks"] or 0
        u["queries"] += 1
    return qs, sorted(by_url.values(), key=lambda u: u["clicks"], reverse=True)


# ---------------------------------------------------------------- output
def fmt(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) >= 1 else f"{v:.3f}".rstrip("0").rstrip(".")
    return str(v)


def table(rows, cols, n=10):
    if not rows:
        return "_(no data)_\n"
    out = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for row in rows[:n]:
        out += "| " + " | ".join(fmt(row.get(c)) for c in cols) + " |\n"
    return out


def markdown(res):
    md = "# Automated traffic analysis\n\n"
    if "pages" in res:
        p = res["pages"]
        md += "## Pages: consumption (score = mean rank of views, time and 90% scroll)\n\n"
        md += table(p["ranking"], ["url", "views", "avg_time_s", "scroll_90_pct", "consumption_score", "consumption", "exit_rate", "conversion_rate", "signals"], 15)
        leaks = [x for x in p["ranking"] if "leak" in x["signals"]]
        md += "\n## Leaking pages (exit rate ≥ P75 and conversion below median)\n\n"
        md += table(sorted(leaks, key=lambda x: x["views"] or 0, reverse=True), ["url", "views", "exit_rate", "scroll_90_pct", "signals"])
    if "elements" in res:
        e = res["elements"]
        md += "\n## Strong elements (CTR ≥ P75)\n\n"
        md += table([x for x in e["ranking"] if x["classification"] == "strong"], ["url", "element", "type", "impressions", "clicks", "ctr", "conv_per_click", "signals"])
        md += "\n## Weak elements (CTR ≤ P25) and friction signals\n\n"
        weak = [x for x in e["ranking"] if x["classification"] == "weak" or x["signals"]]
        md += table(sorted(weak, key=lambda x: x["impressions"] or 0, reverse=True), ["url", "element", "type", "impressions", "ctr", "rage_clicks", "dead_clicks", "error_clicks", "signals"], 15)
        insuf = sum(1 for x in e["ranking"] if x["classification"] == "insufficient_sample")
        md += f"\n_{insuf} elements below the minimum sample (not classified)._\n"
    if "search" in res:
        b = res["search"]
        md += "\n## Organic search: largest opportunity (impressions × lost CTR)\n\n"
        md += table([q for q in b["queries"] if q["signals"]], ["url", "query", "impressions", "clicks", "position", "ctr", "expected_ctr", "signals"], 15)
        md += "\n## URLs by organic clicks\n\n"
        md += table(b["by_url"], ["url", "clicks", "impressions", "queries"])
    md += "\n## Thresholds used\n\n```json\n" + json.dumps(res.get("thresholds", {}), ensure_ascii=False, indent=2) + "\n```\n"
    return md


def utf8_console():
    """Print non-ASCII (≥, ×, emoji in page titles) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages")
    ap.add_argument("--elements")
    ap.add_argument("--search")
    ap.add_argument("--min-impressions", type=int, default=100, help="minimum impressions/views to classify (default 100)")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--md", dest="md_out")
    a = ap.parse_args()
    if not (a.pages or a.elements or a.search):
        ap.error("provide at least one of --pages, --elements or --search")

    res = {"thresholds": {"min_impressions": a.min_impressions}}
    if a.pages:
        rk, th = analyze_pages(read_csv(a.pages), a.min_impressions)
        res["pages"] = {"ranking": rk}
        res["thresholds"]["pages"] = th
    if a.elements:
        rk, th = analyze_elements(read_csv(a.elements), a.min_impressions)
        res["elements"] = {"ranking": rk}
        res["thresholds"]["elements"] = th
    if a.search:
        qs, by_url = analyze_search(read_csv(a.search), a.min_impressions)
        res["search"] = {"queries": qs, "by_url": by_url}

    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    md = markdown(res)
    if a.md_out:
        with open(a.md_out, "w", encoding="utf-8") as f:
            f.write(md)
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
