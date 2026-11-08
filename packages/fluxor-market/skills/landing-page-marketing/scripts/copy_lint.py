#!/usr/bin/env python3
"""Lint landing-page copy for the mechanical problems that erode perceived value.

It flags, with the location of each hit:

  unsourced   numbers in the copy that don't appear in your facts file(s) (--facts). This is the
              "did we invent this?" guard: every figure on a page should trace back to evidence.
  claim       superlatives and comparative/quantified claims that need proof on the page
              ("best", "#1", "fastest", "trusted by 10,000+", "3x", "up to 50%", "guaranteed")
  urgency     scarcity/deadline language ("only 3 left", "ends in", "limited time"): legal only if true
  hype        empty or cliché words that make copy sound like every other page ("revolutionary",
              "seamless", "leverage", "all-in-one", "next-generation", ...)
  cta         generic call-to-action labels ("Submit", "Learn more", "Click here")
  placeholder lorem ipsum, TODO, TBD, XX%, [Company name] left in the copy
  style       exclamation marks, emoji in headings, very long sentences, filler intensifiers

and reports stats: words, readability (Flesch-Kincaid grade for English, Szigriszt-Pazos/INFLESZ
for Spanish), "you" vs "we" focus, and numbers per 100 words (a rough specificity signal).

The linter finds signals; it does not decide. A flagged claim that is true and proven on the page
is fine, and a clean lint does not make copy persuasive.

Input: a Markdown/text copy deck, an HTML file, or a URL.
Usage:
  python3 copy_lint.py copy.md --facts value-brief.md
  python3 copy_lint.py https://example.com --json lint.json
  python3 copy_lint.py page.html --lang es

In Markdown copy decks, lines starting with "CTA:" (or "Button:") and link texts [like this](...)
are treated as calls to action. HTML comments and lines starting with "Note:", "Visual:", "Evidence:", "Source:" or "Page goal:" are ignored.

Standard library only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HYPE = {
    "en": [
        # hype and superlative fog
        "revolutionary", "revolutionize", "revolutionizing", "revolutionise", "game-changing", "game changer",
        "game-changer", "groundbreaking", "cutting-edge", "cutting edge", "state-of-the-art", "next-generation",
        "next-gen", "world-class", "best-in-class", "industry-leading", "unparalleled", "unprecedented",
        "unmatched", "ultimate", "incredible", "amazing", "awesome", "magical", "mind-blowing", "disruptive",
        "innovative", "reimagine", "reimagined", "the future of", "transformative", "transform your",
        # corporate filler
        "leverage", "leverages", "leveraging", "synergy", "synergies", "empower", "empowers", "empowering",
        "seamless", "seamlessly", "robust", "powerful", "streamline", "streamlines", "supercharge",
        "supercharges", "unlock", "unlocks", "unleash", "holistic", "ecosystem", "solution", "solutions",
        "utilize", "utilizes", "all-in-one", "one-stop", "end-to-end", "turnkey", "paradigm", "best practices",
        "actionable insights", "take it to the next level", "next level", "elevate", "effortless", "effortlessly",
        "enterprise-grade", "mission-critical", "scalable", "optimize", "optimise", "world's most",
        "passionate", "commitment to excellence", "we believe", "our mission", "tools you love",
    ],
    "es": [
        "revolucionario", "revolucionaria", "revolucionar", "revolucionando", "innovador", "innovadora",
        "de vanguardia", "vanguardista", "líder del sector", "líderes del sector", "el futuro de",
        "de última generación", "de clase mundial", "increíble", "increíbles", "asombroso", "mágico",
        "disruptivo", "disruptiva", "transformador", "transforma tu", "potente", "potentes", "robusto",
        "robusta", "sin fisuras", "sin esfuerzo", "todo en uno", "todo-en-uno", "soluciones", "solución integral",
        "sinergia", "sinergias", "empoderar", "potenciar", "potencia tu", "optimizar", "optimiza", "ecosistema",
        "llevar al siguiente nivel", "siguiente nivel", "apasionados", "nuestra misión", "creemos que",
        "compromiso con la excelencia", "escalable", "holístico", "holística",
    ],
}

CLAIM_PATTERNS = {
    "en": [
        (r"\b(the\s+)?best\b", "superlative"),
        (r"#\s?1\b|\bnumber\s+one\b|\bno\.\s?1\b", "rank claim"),
        (r"\b(leading|market[- ]leading|top[- ]rated|award[- ]winning)\b", "status claim"),
        (r"\b(fastest|easiest|cheapest|simplest|smartest|safest|most\s+\w+)\b", "superlative"),
        (r"\bthe\s+only\b|\bonly\s+(tool|app|platform|product|one|solution|company|service)\b", "uniqueness claim"),
        (r"\bguarantee[ds]?\b", "guarantee (state its terms)"),
        (r"\b(proven|clinically|scientifically|certified|approved)\b", "proof claim"),
        (r"\btrusted\s+by\b|\bjoin\s+[\d,.]+|\b[\d,.]+\s?\+?\s?(k\s)?(customers|users|businesses|teams|companies|people|members|clients)\b",
         "social-proof number"),
        (r"\b\d+(\.\d+)?\s?x\b|\b\d+(\.\d+)?\s?%", "quantified result"),
        (r"\bup\s+to\b|\bas\s+(much|many|little)\s+as\b", "'up to' claim (must be typical, not best case)"),
        (r"\b(save|saves|saved)\s+\$?\d", "savings claim"),
    ],
    "es": [
        (r"\b(el|la|los|las)\s+mejor(es)?\b|\bmejor\b", "superlative"),
        (r"n[º°o]\.?\s?1\b|#\s?1\b|\bnúmero\s+uno\b", "rank claim"),
        (r"\b(líder|líderes|premiad[oa]s?)\b", "status claim"),
        (r"\b(el|la)\s+más\s+\w+|\bmás\s+(rápido|fácil|barato|seguro)\b", "superlative"),
        (r"\bel\s+único\b|\bla\s+única\b|\búnico\b", "uniqueness claim"),
        (r"\bgaranti(a|za|zado|zada|zamos)\b|\bgarantía\b", "guarantee (state its terms)"),
        (r"\b(probado|demostrado|certificado|clínicamente|científicamente)\b", "proof claim"),
        (r"\bconfían\s+en\b|\bmás\s+de\s+[\d.,]+|\b[\d.,]+\s?\+?\s?(clientes|usuarios|empresas|equipos|personas)\b",
         "social-proof number"),
        (r"\b\d+(,\d+)?\s?x\b|\b\d+(,\d+)?\s?%", "quantified result"),
        (r"\bhasta\s+(un\s+)?\d", "'hasta' ('up to') claim (must be typical, not best case)"),
        (r"\bahorr(a|as|e|ar)\s+\d", "savings claim"),
    ],
}

URGENCY = {
    "en": r"\b(limited[- ]time|only\s+\d+\s+(left|spots?|seats?|remaining)|ends?\s+(in|today|tonight|soon)|"
          r"hurry|last\s+chance|today\s+only|while\s+(stocks?|supplies)\s+last|act\s+now|don'?t\s+miss|"
          r"before\s+it'?s\s+gone|selling\s+fast|almost\s+(gone|sold\s+out)|expires?\s+in|countdown|"
          r"\d+\s+people\s+(are\s+)?(viewing|looking)|spots?\s+left)\b",
    "es": r"\b(tiempo\s+limitado|solo\s+quedan|últimas?\s+(plazas|unidades)|termina\s+(en|hoy)|date\s+prisa|"
          r"última\s+oportunidad|solo\s+hoy|hasta\s+agotar|no\s+te\s+lo\s+pierdas|oferta\s+limitada|"
          r"quedan\s+\d+|expira\s+en|cuenta\s+atrás)\b",
}

GENERIC_CTA = {
    "en": {"submit", "send", "click here", "learn more", "read more", "more", "go", "continue", "next", "here",
           "find out more", "discover more", "explore", "details", "ok", "enter", "apply", "request", "contact",
           "contact us", "get in touch", "sign up", "register", "buy", "buy now", "subscribe", "get started"},
    "es": {"enviar", "haz clic aquí", "clic aquí", "más información", "saber más", "leer más", "ver más", "continuar",
           "siguiente", "aquí", "descubre más", "contacto", "contactar", "contáctanos", "registrarse", "regístrate",
           "comprar", "suscribirse", "empezar", "comenzar"},
}
# Weak but not always wrong: say what the visitor gets instead.
SOFT_CTA = {"sign up", "register", "buy", "buy now", "subscribe", "get started", "registrarse", "regístrate",
            "comprar", "suscribirse", "empezar", "comenzar", "contact", "contact us", "get in touch", "contacto",
            "contactar", "contáctanos", "request", "apply"}

# Case-sensitive markers (so Spanish "todo" = "all" isn't flagged) plus case-insensitive generic ones.
PLACEHOLDER_CS = re.compile(r"\bTODO\b|\bTBD\b|\bXX+%?|\[TODO[^\]]*\]")
PLACEHOLDER_CI = re.compile(r"lorem ipsum|\[(company|product|name|brand|nombre|empresa)[^\]]*\]|\{\{.*?\}\}|\bplaceholder\b", re.I)
FILLER = {"en": r"\b(very|really|extremely|truly|literally|simply|just|actually|incredibly|super)\b",
          "es": r"\b(muy|realmente|súper|super|literalmente|simplemente|verdaderamente|increíblemente)\b"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅]")

YOU = {"en": r"\b(you|your|yours|yourself|you're|you'll|you've)\b",
       "es": r"\b(tú|tu|tus|te|ti|contigo|usted|ustedes|vosotros|vuestro|vuestra|tuyo|tuya)\b"}
WE = {"en": r"\b(we|our|ours|us|we're|we've|we'll|ourselves)\b",
      "es": r"\b(nosotros|nosotras|nuestro|nuestra|nuestros|nuestras|somos|hemos|creemos)\b"}


# --------------------------------------------------------------------------- input

class Block:
    def __init__(self, kind: str, text: str, where: str):
        self.kind, self.text, self.where = kind, text, where  # kind: heading | body | cta | quote


def blocks_from_markdown(text: str) -> list[Block]:
    out: list[Block] = []
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    in_code = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if line.startswith(">") and not in_code:
            out.append(Block("quote", line.lstrip("> ").strip(), f"line {n}"))
            continue
        if in_code or not line or re.match(r"(?i)^(note|nota|internal|evidence|evidencia|source|fuente|visual|job|page goal|objetivo)\s*:", line):
            continue
        if re.match(r"^\|?\s*:?-{3,}", line):
            continue
        where = f"line {n}"
        m = re.match(r"(?i)^[-*]?\s*\**\s*(cta|button|botón|boton)\s*\**\s*:\s*\**(.+?)\**\s*$", line)
        if m:
            label = re.sub(r"\s*[—–(].*$", "", m.group(2)).strip(" *\"'“”[]")
            out.append(Block("cta", label, where))
            continue
        for lm in re.finditer(r"\[([^\]]+)\]\([^)]+\)", line):
            out.append(Block("cta", lm.group(1), where))
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            out.append(Block("heading", h.group(2).strip(), where))
            continue
        clean = re.sub(r"[*_`#|]", " ", re.sub(r"\]\([^)]+\)", "]", line)).replace("[", "").replace("]", "")
        clean = re.sub(r"^\s*[-+]\s+|^\s*\d+\.\s+", "", clean)
        out.append(Block("body", clean.strip(), where))
    return out


def blocks_from_html(source: str, html_file: str | None = None) -> list[Block]:
    from extract_page import extract  # same folder
    d = extract(source, html_file)
    out: list[Block] = []
    for s in d["sections"]:
        if s["region"] in ("nav", "footer"):
            continue
        where = f"section '{(s['heading'] or s['label'] or '')[:50]}'"
        if s["heading"]:
            out.append(Block("heading", s["heading"], where))
        for para in s["text"].split("\n"):
            if para.strip():
                out.append(Block("body", para.strip(), where))
    for c in d["ctas"]:
        if c.get("region") in ("nav", "footer"):
            continue
        out.append(Block("cta", c["text"], f"CTA in '{(c.get('section') or '')[:50]}'"))
    return out


def load_blocks(source: str, html_file: str | None) -> list[Block]:
    if html_file or re.match(r"https?://", source) or source.lower().endswith((".html", ".htm")):
        return blocks_from_html(source, html_file)
    with open(source, encoding="utf-8", errors="replace") as f:
        return blocks_from_markdown(f.read())


# --------------------------------------------------------------------------- analysis

def detect_lang(text: str) -> str:
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    es = sum(w in {"el", "la", "los", "las", "de", "que", "y", "en", "para", "con", "tu", "por", "una", "es", "más"} for w in words)
    en = sum(w in {"the", "and", "of", "to", "your", "for", "with", "you", "is", "in", "a", "that", "it", "on"} for w in words)
    return "es" if es > en else "en"


def syllables_en(word: str) -> int:
    w = word.lower()
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def syllables_es(word: str) -> int:
    w = word.lower()
    # diphthongs/triphthongs collapse into one nucleus; hiatus with strong vowels splits
    groups = re.findall(r"[iuü]?[aeoáéó][iuy]?|[iuüíú]+", w)
    return max(1, len(groups))


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?¡¿])\s+|\n+", text)
    return [p.strip() for p in parts if len(re.findall(r"\w+", p)) >= 2]


def readability(body: str, lang: str) -> dict:
    sents = sentences(body)
    words = re.findall(r"[A-Za-zÀ-ÿ']+", body)
    if len(words) < 30 or not sents:
        return {"note": "too little text to score"}
    if lang == "es":
        syl = sum(syllables_es(w) for w in words)
        inflesz = 206.835 - 62.3 * (syl / len(words)) - (len(words) / len(sents))
        band = ("very difficult" if inflesz < 40 else "somewhat difficult" if inflesz < 55 else "normal"
                if inflesz < 65 else "fairly easy" if inflesz < 80 else "very easy")
        return {"index": "Szigriszt-Pazos (INFLESZ)", "score": round(inflesz, 1), "band": band,
                "words_per_sentence": round(len(words) / len(sents), 1)}
    syl = sum(syllables_en(w) for w in words)
    wps = len(words) / len(sents)
    spw = syl / len(words)
    return {"index": "Flesch-Kincaid", "grade": round(0.39 * wps + 11.8 * spw - 15.59, 1),
            "reading_ease": round(206.835 - 1.015 * wps - 84.6 * spw, 1), "words_per_sentence": round(wps, 1)}


NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s?(%|x|k|K|\+)?")


def number_key(tok: str) -> str:
    t = tok.replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", t):
        return t.replace(",", "").replace(".", "")
    return t.replace(",", ".")


def fact_numbers(paths: list[str]) -> set[str]:
    nums: set[str] = set()
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            txt = f.read()
        for m in NUM_RE.finditer(txt):
            k = number_key(m.group(1))
            nums.add(k)
            if m.group(2) in ("k", "K"):
                try:
                    nums.add(str(int(float(k) * 1000)))
                except ValueError:
                    pass
            if k.isdigit() and len(k) >= 4:
                nums.add(k)
    return nums


def lint(blocks: list[Block], lang: str, facts: list[str]) -> dict:
    findings: list[dict] = []

    def add(cat, sev, b: Block, match, why):
        findings.append({"category": cat, "severity": sev, "where": b.where, "kind": b.kind,
                         "match": match, "text": b.text[:160], "why": why})

    hype_re = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in sorted(HYPE[lang], key=len, reverse=True))
                         + r")(?![\w-])", re.I)
    claim_res = [(re.compile(p, re.I), label) for p, label in CLAIM_PATTERNS[lang]]
    urg_re = re.compile(URGENCY[lang], re.I)
    fill_re = re.compile(FILLER[lang], re.I)
    known = fact_numbers(facts) if facts else None

    def check_cta(b: Block):
        label = b.text.lower().strip(" !.→›»")
        if label in GENERIC_CTA[lang]:
            soft = label in SOFT_CTA
            add("cta", "minor" if soft else "major", b, b.text,
                "Acceptable but flat. Consider naming what they get and removing the risk ('Start free, no card')."
                if soft else "Says what the visitor must do, not what they get. Name the outcome or the next "
                "step's value (e.g. 'Build my first rota free', 'Start my 30-day trial').")

    def check_copy(b: Block, t: str):
        for m in hype_re.finditer(t):
            add("hype", "minor", b, m.group(0), "Empty or cliché word: says nothing another company couldn't say. "
                "Replace with the specific fact or outcome it stands for, or cut it.")
        for rx, label in claim_res:
            for m in rx.finditer(t):
                add("claim", "check", b, m.group(0), f"{label}: keep only if true, typical, and proven on the page "
                    "(source, number, name). Unproven claims lower trust and can be deceptive advertising.")
        for m in urg_re.finditer(t):
            add("urgency", "major", b, m.group(0), "Scarcity/deadline language. Legal and persuasive only if it is "
                "real and verifiable (fixed deadline, true stock). Fake or resetting timers are a dark pattern "
                "(FTC, EU UCPD/DSA).")
        if b.kind == "heading":
            e = EMOJI.search(t)
            if e:
                add("style", "minor", b, e.group(0), "Emoji in a headline reads as hype; keep the headline for the promise.")
            if "!" in t:
                add("style", "minor", b, "!", "Exclamation mark in a headline: excitement you have to announce "
                    "isn't felt. Let the specific promise carry it.")
        else:
            for sent in sentences(t):
                n = len(re.findall(r"\w+", sent))
                if n > 30:
                    add("style", "minor", b, f"{n}-word sentence", "Long sentence: split it. Scanners skip dense text.")
            if t.count("!") >= 2:
                add("style", "minor", b, f"{t.count('!')}×'!'", "Several exclamation marks read as shouting or hype.")
        fills = fill_re.findall(t)
        if len(fills) >= 2:
            add("style", "minor", b, ", ".join(fills[:4]), "Filler intensifiers: cut them or use a number instead.")

    def check_numbers(b: Block, t: str):
        for m in NUM_RE.finditer(t):
            if re.match(r"\d{1,2}:\d{2}", t[m.start():m.start() + 5]) or t[max(0, m.start() - 1):m.start()] == ":":
                continue  # clock times
            if m.start() == 0 and t[m.end(1):m.end(1) + 2] == ". ":
                continue  # section numbering ("4. How it works")
            k = number_key(m.group(1))
            if k in known or re.fullmatch(r"(19|20)\d\d", k) or k in {"24", "365", "100"}:
                continue  # sourced, a year, or an everyday number ("24/7", "100%")
            if k.isdigit() and int(k) <= 10 and not m.group(2):
                continue  # small counts ("3 steps", "rated 4.8 of 5"); "3x"/"5%" still need a source
            add("unsourced", "major", b, m.group(0), "Number not found in the facts file(s). Source it, or remove "
                "it. Never let a figure on the page be invented or rounded up.")

    for b in blocks:
        if b.kind == "cta":
            check_cta(b)
            continue
        if b.kind != "quote":  # testimonials are the customer's words: don't lint their style
            check_copy(b, b.text)
        for m in list(PLACEHOLDER_CS.finditer(b.text)) + list(PLACEHOLDER_CI.finditer(b.text)):
            add("placeholder", "blocker", b, m.group(0), "Placeholder left in the copy.")
        if known is not None:
            check_numbers(b, b.text)

    body = "\n".join(b.text for b in blocks if b.kind in ("body", "heading"))
    words = re.findall(r"\w+", body)
    you = len(re.findall(YOU[lang], body, re.I))
    we = len(re.findall(WE[lang], body, re.I))
    nums = len(NUM_RE.findall(body))
    headings = [b.text for b in blocks if b.kind == "heading"]
    stats = {
        "language": lang,
        "words": len(words),
        "headline": headings[0] if headings else None,
        "headline_words": len(re.findall(r"\w+", headings[0])) if headings else 0,
        "you_count": you, "we_count": we,
        "you_we_ratio": round(you / we, 2) if we else None,
        "numbers_per_100_words": round(100 * nums / len(words), 1) if words else 0,
        "ctas": [b.text for b in blocks if b.kind == "cta"],
        "readability": readability("\n".join(b.text for b in blocks if b.kind == "body"), lang),
    }
    if we > you and len(words) > 80:
        findings.append({"category": "focus", "severity": "major", "where": "whole page", "kind": "stat",
                         "match": f"you={you} we={we}", "text": "",
                         "why": "The copy talks about the company more than the customer. Rewrite around what the "
                                "reader gets ('you'), keeping 'we' for promises and proof."})
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["category"]] = counts.get(f["category"], 0) + 1
    return {"stats": stats, "counts": counts, "findings": findings}


def report(res: dict) -> str:
    s = res["stats"]
    lines = [f"COPY LINT · {s['words']} words · language={s['language']}"]
    r = s["readability"]
    if "grade" in r:
        lines.append(f"Readability: Flesch-Kincaid grade {r['grade']} (reading ease {r['reading_ease']}), "
                     f"{r['words_per_sentence']} words/sentence")
    elif "score" in r:
        lines.append(f"Readability: INFLESZ {r['score']} ({r['band']}), {r['words_per_sentence']} words/sentence")
    else:
        lines.append(f"Readability: {r.get('note')}")
    lines.append(f"Headline ({s['headline_words']} words): {s['headline']!r}")
    lines.append(f"You/we: {s['you_count']}/{s['we_count']} · numbers per 100 words: {s['numbers_per_100_words']}")
    lines.append(f"CTAs: {s['ctas']}")
    lines.append("Counts: " + (", ".join(f"{k}={v}" for k, v in sorted(res["counts"].items())) or "none"))
    order = {"blocker": 0, "major": 1, "check": 2, "minor": 3}
    grouped: dict[tuple, list] = {}
    for f in sorted(res["findings"], key=lambda f: (order.get(f["severity"], 9), f["category"])):
        grouped.setdefault((f["severity"], f["category"], f["why"]), []).append(f)
    for (sev, cat, why), fs in grouped.items():
        lines.append("")
        lines.append(f"[{sev.upper()}] {cat}: {why}")
        for f in fs[:25]:
            ctx = f" | {f['text'][:110]}" if f["text"] and f["text"] != f["match"] else ""
            lines.append(f"   - {f['where']}: «{f['match']}»{ctx}")
        if len(fs) > 25:
            lines.append(f"   … {len(fs) - 25} more")
    return "\n".join(lines)


def utf8_console():
    """Print non-ASCII (✓, ≥, —, emoji from the input) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="copy deck (.md/.txt), .html file, or URL")
    ap.add_argument("--html-file", help="rendered HTML to use instead of fetching the URL")
    ap.add_argument("--facts", action="append", default=[], help="facts/value-brief file(s); numbers in the copy must appear here")
    ap.add_argument("--lang", choices=["auto", "en", "es"], default="auto")
    ap.add_argument("--json", help="write findings as JSON")
    a = ap.parse_args()
    try:
        blocks = load_blocks(a.source, a.html_file)
    except Exception as e:
        print(f"error: could not read {a.source}: {e}", file=sys.stderr)
        sys.exit(1)
    lang = a.lang if a.lang != "auto" else detect_lang(" ".join(b.text for b in blocks))
    res = lint(blocks, lang, a.facts)
    res["source"] = a.source
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    print(report(res))


if __name__ == "__main__":
    main()
