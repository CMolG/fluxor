#!/usr/bin/env python3
"""Extract the message hierarchy of a landing page as JSON.

Reads a live URL, a saved HTML file, or rendered HTML (from capture_page.cjs --dump-html) and
returns what a visitor actually gets, in page order:

  meta        title, meta description, Open Graph, lang, canonical
  hero        the H1 and everything before the second major heading: sub-headline, CTAs, proof
  sections    one entry per heading-led block: heading, level, text, CTAs, images, prices,
              quotes/testimonials, forms, list items, region (nav / main / footer)
  ctas        every button-like element with its text, target and position
  forms       field names/types and count (friction)
  prices      every price-looking string with context
  stats       word count, section count, images without alt, etc.

The script only extracts; judging the page is the model's job.

Usage:
  python3 extract_page.py https://example.com --json out/page.json
  python3 extract_page.py page.html            (prints a readable outline)
  python3 extract_page.py https://example.com --html-file rendered.html   (use JS-rendered DOM)

Standard library only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "iframe", "canvas", "head", "option"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BLOCK_TAGS = {"p", "div", "section", "article", "li", "ul", "ol", "header", "footer", "nav", "main", "aside",
              "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "figure", "figcaption", "table", "tr", "td", "th",
              "dd", "dt", "dl", "form", "label", "details", "summary", "br", "hr"}
BUTTONISH_CLASS = re.compile(r"\b(btn|button|cta|primary|signup|sign-up|get-started|pricing-cta)\b", re.I)
QUOTE_CLASS = re.compile(r"(testimonial|review|quote|customer-story|endorse)", re.I)
PRICE_RE = re.compile(
    r"(?:[$€£¥₹]\s?\d[\d.,]*(?:\s?(?:k|K|m|M))?|\d[\d.,]*\s?(?:€|EUR|USD|GBP|dollars|euros))"
    r"(?:\s*(?:/|per|a|al|por)\s*(?:mo|month|mes|yr|year|año|user|usuario|seat|week|day))?",  # lang:es: Spanish price units are data
    re.I,
)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 landing-page-marketing/1.0"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


class Page(HTMLParser):
    def __init__(self, base_url: str = ""):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.meta: dict = {}
        self.stack: list[tuple[str, dict, bool]] = []
        self.skip_depth = 0
        self.region_stack: list[str] = []
        self.sections: list[dict] = []
        self.cur = self._new_section(None, 0, "(before first heading)")
        self.in_title = False
        self.title_buf: list[str] = []
        self.heading_buf: list[str] | None = None
        self.heading_level = 0
        self.cta_buf: list[str] | None = None
        self.cta_attrs: dict = {}
        self.quote_depth = 0
        self.quote_buf: list[str] = []
        self.forms: list[dict] = []
        self.form_cur: dict | None = None
        self.li_buf: list[str] | None = None
        self.order = 0
        self.nav_text: list[str] = []

    # ---- helpers
    def _new_section(self, heading, level, label=None):
        sec = {"heading": heading, "label": label, "level": level, "region": self._region(),
               "text": [], "ctas": [], "images": [], "prices": [], "quotes": [], "list_items": [], "forms": 0}
        self.sections.append(sec)
        return sec

    def _region(self):
        return self.region_stack[-1] if getattr(self, "region_stack", None) else "main"

    def _attrs(self, attrs):
        return {k.lower(): (v or "") for k, v in attrs}

    # ---- parser callbacks
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = self._attrs(attrs)
        if tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name in ("description", "og:title", "og:description", "og:image", "twitter:card", "twitter:title",
                        "twitter:description", "twitter:image", "viewport", "robots"):
                self.meta[name] = a.get("content", "")
            return
        if tag == "link" and "canonical" in a.get("rel", "").lower():
            self.meta["canonical"] = a.get("href", "")
            return
        if tag == "html" and a.get("lang"):
            self.meta["lang"] = a["lang"]
        if tag == "title":
            self.in_title = True
            return
        if tag in SKIP_TAGS:
            if tag != "head":
                self.skip_depth += 1
            return
        hidden = "hidden" in a or re.search(r"display\s*:\s*none", a.get("style", ""), re.I) is not None
        if tag not in VOID_TAGS:
            self.stack.append((tag, a, hidden))
            if hidden:
                self.skip_depth += 1  # visitors don't see it (e.g. a slot waiting for real testimonials)
        if self.skip_depth:
            return
        if tag in ("nav", "footer", "header") or a.get("role") in ("navigation", "contentinfo"):
            region = {"nav": "nav", "footer": "footer", "header": "header"}.get(tag) or (
                "nav" if a.get("role") == "navigation" else "footer")
            self.region_stack.append(region)
        if tag in ("h1", "h2", "h3", "h4"):
            self.heading_buf = []
            self.heading_level = int(tag[1])
        if tag in ("button",) or (tag == "a" and (BUTTONISH_CLASS.search(a.get("class", "") + " " + a.get("id", ""))
                                                  or a.get("role") == "button")):
            self.cta_buf = []
            self.cta_attrs = {"tag": tag, "href": urljoin(self.base, a.get("href", "")) if a.get("href") else "",
                              "type": a.get("type", "")}
        if tag == "input" and a.get("type", "").lower() in ("submit", "button") and a.get("value"):
            self._add_cta(a.get("value"), {"tag": "input", "href": "", "type": a.get("type")})
        if tag == "input" and self.form_cur is not None and a.get("type", "text").lower() not in ("hidden", "submit", "button"):
            self.form_cur["fields"].append({"type": a.get("type", "text"), "name": a.get("name") or a.get("id") or a.get("placeholder", ""),
                                            "required": "required" in a})
        if tag in ("select", "textarea") and self.form_cur is not None:
            self.form_cur["fields"].append({"type": tag, "name": a.get("name") or a.get("id", ""), "required": "required" in a})
        if tag == "form":
            self.form_cur = {"action": a.get("action", ""), "fields": [], "section": self.cur.get("heading")}
        if tag == "img":
            self.cur["images"].append({"alt": a.get("alt"), "src": a.get("src", "")[:200]})
        if tag in ("blockquote", "q") or QUOTE_CLASS.search(a.get("class", "")):
            self.quote_depth += 1
            if self.quote_depth == 1:
                self.quote_buf = []
        if tag == "li":
            self.li_buf = []
        if tag in BLOCK_TAGS:
            self.cur["text"].append("\n")
        elif tag in ("a", "button"):
            self.cur["text"].append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
            self.meta["title"] = norm("".join(self.title_buf))
            return
        if tag in SKIP_TAGS:
            if tag != "head" and self.skip_depth:
                self.skip_depth -= 1
            return
        # pop to matching tag (tolerates sloppy HTML)
        attrs = {}
        was_hidden = False
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                attrs = self.stack[i][1]
                closed = self.stack[i:]
                self.skip_depth -= sum(1 for e in closed if e[2])
                was_hidden = bool(closed[0][2])
                del self.stack[i:]
                break
        if self.skip_depth or was_hidden:
            return
        if tag in ("h1", "h2", "h3", "h4") and self.heading_buf is not None:
            text = norm("".join(self.heading_buf))
            self.heading_buf = None
            if text:
                self.cur = self._new_section(text, int(tag[1]))
        if (tag == "button" or tag == "a") and self.cta_buf is not None:
            text = norm("".join(self.cta_buf))
            if not text:
                text = attrs.get("aria-label", "") or ""
            self._add_cta(text, self.cta_attrs)
            self.cta_buf = None
        if (tag in ("blockquote", "q") or QUOTE_CLASS.search(attrs.get("class", ""))) and self.quote_depth:
            self.quote_depth -= 1
            if self.quote_depth == 0:
                q = norm("".join(self.quote_buf))
                if q:
                    self.cur["quotes"].append(q[:600])
        if tag == "li" and self.li_buf is not None:
            t = norm("".join(self.li_buf))
            if t:
                self.cur["list_items"].append(t[:300])
            self.li_buf = None
        if tag == "form" and self.form_cur is not None:
            self.forms.append(self.form_cur)
            self.cur["forms"] += 1
            self.form_cur = None
        if tag in ("nav", "footer", "header") and self.region_stack:
            self.region_stack.pop()
        if tag in BLOCK_TAGS:
            self.cur["text"].append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.title_buf.append(data)
            return
        if self.skip_depth:
            return
        if self.heading_buf is not None:
            self.heading_buf.append(data)
            return  # heading text is stored as the section heading, not body text
        if self.cta_buf is not None:
            self.cta_buf.append(data)
        if self.quote_depth:
            self.quote_buf.append(data)
        if self.li_buf is not None:
            self.li_buf.append(data)
        if self._region() == "nav":
            self.nav_text.append(data)  # keep menus out of the section copy
            return
        self.cur["text"].append(data)

    def _add_cta(self, text, attrs):
        text = norm(text)
        if not text:
            return
        self.order += 1
        self.cur["ctas"].append({"text": text, "href": attrs.get("href", ""), "tag": attrs.get("tag"),
                                 "order": self.order, "region": self._region()})

    # ---- result
    def result(self) -> dict:
        sections = []
        for s in self.sections:
            body = "\n".join(norm(line) for line in "".join(s["text"]).split("\n"))
            body = re.sub(r"\n{2,}", "\n", body).strip()
            s = dict(s)
            s["text"] = body
            s["words"] = len(re.findall(r"\w+", body))
            s["prices"] = sorted({m.group(0).strip() for m in PRICE_RE.finditer(body)})
            if s["heading"] is None and not body and not s["ctas"] and not s["images"]:
                continue
            sections.append(s)
        main = [s for s in sections if s["region"] not in ("nav", "footer")]
        h1s = [s["heading"] for s in sections if s["level"] == 1]
        hero = self._hero(main)
        ctas = [dict(c, section=s["heading"]) for s in sections for c in s["ctas"]]
        all_text = "\n".join(s["text"] for s in main)
        prices = []
        for s in main:
            for p in s["prices"]:
                prices.append({"price": p, "section": s["heading"]})
        imgs = [i for s in sections for i in s["images"]]
        return {
            "meta": self.meta,
            "nav": norm(" ".join(self.nav_text))[:500],
            "h1": h1s,
            "hero": hero,
            "sections": sections,
            "ctas": ctas,
            "forms": [dict(f, field_count=len(f["fields"]), required=sum(1 for x in f["fields"] if x["required"]))
                      for f in self.forms],
            "prices": prices,
            "quotes": [{"quote": q, "section": s["heading"]} for s in main for q in s["quotes"]],
            "stats": {
                "words_main": len(re.findall(r"\w+", all_text)),
                "sections_main": len([s for s in main if s["heading"]]),
                "h1_count": len(h1s),
                "cta_count": len(ctas),
                "distinct_cta_texts": sorted({c["text"] for c in ctas if c["region"] not in ("nav", "footer")}),
                "images": len(imgs),
                "images_missing_alt": sum(1 for i in imgs if i["alt"] is None),
                "forms": len(self.forms),
            },
        }

    @staticmethod
    def _hero(main: list[dict]) -> dict:
        """The hero is the H1 block plus anything before it; ends at the next heading of level <= 2."""
        idx = next((i for i, s in enumerate(main) if s["level"] == 1), None)
        if idx is None:
            idx = next((i for i, s in enumerate(main) if s["heading"]), 0)
        blocks = [s for s in main[:idx] if s["heading"] is None] + [main[idx]] if main else []
        j = idx + 1
        while j < len(main) and main[j]["level"] >= 3:
            blocks.append(main[j])
            j += 1
        text = "\n".join(filter(None, [b["text"] for b in blocks]))
        return {
            "headline": main[idx]["heading"] if main else None,
            "text": text[:1500],
            "ctas": [c["text"] for b in blocks for c in b["ctas"] if c["region"] != "nav"],
            "images": [i.get("alt") for b in blocks for i in b["images"]],
            "words": len(re.findall(r"\w+", text)),
        }


def fetch(url: str, timeout: int = 20) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(6_000_000)
        charset = r.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, "replace"), r.geturl()


def load(source: str, html_file: str | None = None) -> tuple[str, str]:
    if html_file:
        with open(html_file, encoding="utf-8", errors="replace") as f:
            return f.read(), source if source.startswith("http") else ""
    if re.match(r"https?://", source):
        return fetch(source)
    with open(source, encoding="utf-8", errors="replace") as f:
        return f.read(), ""


def extract(source: str, html_file: str | None = None) -> dict:
    html, final_url = load(source, html_file)
    p = Page(final_url)
    p.feed(html)
    p.close()
    out = p.result()
    out["source"] = source
    if final_url and final_url != source:
        out["final_url"] = final_url
    if out["stats"]["words_main"] < 60 and re.search(r"<script", html, re.I):
        out["warning"] = ("Very little text in the static HTML: this looks client-rendered. Re-run with "
                          "--html-file <rendered.html> from capture_page.cjs --dump-html.")
    return out


def outline(d: dict) -> str:
    lines = []
    m = d["meta"]
    lines.append(f"TITLE: {m.get('title', '—')}")
    lines.append(f"META DESCRIPTION: {m.get('description', '—')}")
    lines.append(f"OG: title={m.get('og:title', '—')!r} image={m.get('og:image', '—')!r}")
    h = d["hero"]
    lines.append("")
    lines.append(f"HERO HEADLINE: {h['headline']}")
    lines.append(f"HERO TEXT ({h['words']} words): {h['text'][:600]}")
    lines.append(f"HERO CTAs: {h['ctas']}")
    lines.append("")
    lines.append("SECTIONS (page order):")
    for s in d["sections"]:
        if s["region"] in ("nav", "footer") and not s["heading"]:
            continue
        head = s["heading"] or s["label"]
        lines.append(f"  [{s['region']}] {'#' * max(s['level'], 1)} {head}  ({s['words']} words)")
        if s["ctas"]:
            lines.append(f"      CTAs: {[c['text'] for c in s['ctas']]}")
        if s["prices"]:
            lines.append(f"      prices: {s['prices']}")
        if s["quotes"]:
            lines.append(f"      quotes: {len(s['quotes'])} e.g. {s['quotes'][0][:120]!r}")
        if s["forms"]:
            lines.append(f"      forms: {s['forms']}")
    lines.append("")
    for f in d["forms"]:
        lines.append(f"FORM ({f['field_count']} fields, {f['required']} required) in {f['section']!r}: "
                     f"{[x['name'] or x['type'] for x in f['fields']]}")
    lines.append(f"STATS: {json.dumps(d['stats'], ensure_ascii=False)}")
    if d.get("warning"):
        lines.append(f"WARNING: {d['warning']}")
    return "\n".join(lines)


def utf8_console():
    """Print non-ASCII (✓, ≥, —, emoji from the input) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="URL or path to an .html file")
    ap.add_argument("--html-file", help="use this (rendered) HTML instead of fetching the URL")
    ap.add_argument("--json", help="write full JSON here")
    a = ap.parse_args()
    try:
        d = extract(a.source, a.html_file)
    except Exception as e:  # network errors, missing files
        print(f"error: could not read {a.source}: {e}", file=sys.stderr)
        sys.exit(1)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    print(outline(d))


if __name__ == "__main__":
    main()
