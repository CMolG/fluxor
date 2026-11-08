#!/usr/bin/env python3
"""Collect Product Hunt launch-readiness evidence from a live URL (stdlib only).

The script gathers facts; it does not decide severity. Map its output onto
references/audit-checklist.md and judge each item yourself.

Usage:
    python3 audit_url.py https://example.com --json evidence/url.json
    python3 audit_url.py https://example.com --html-file rendered.html   # SPA: use DOM rendered by a browser
    python3 audit_url.py https://example.com --no-links                   # skip link checking

What it checks: HTTP status/redirects/HTTPS/response time, <head> metadata
(title, description, robots, viewport, canonical, Open Graph, Twitter card),
the social preview image and icons (real pixel sizes), the web manifest,
hero copy and CTAs, waitlist / pricing / free-offer / credit-card / demo-only
/ "upvote" copy, hype words and placeholders, legal and contact links,
third-party analytics / error monitoring / chat / payments / consent / video
/ Product Hunt embeds, broken links, that `?ref=producthunt` (which Product
Hunt appends to outbound links) still loads, and robots.txt / sitemap.xml.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imgmeta import image_info_from_bytes  # noqa: E402

DEFAULT_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# --------------------------------------------------------------------------- patterns
def _rx(*parts):
    return [re.compile(p, re.I) for p in parts]

WAITLIST = _rx(r"\bwait[\s-]?list\b", r"\bcoming soon\b", r"\blaunching soon\b", r"\bearly access\b",
               r"\brequest (early )?access\b", r"\brequest an? invite\b", r"\bjoin (the|our) (beta|list)\b",
               r"\bprivate beta\b", r"\bclosed beta\b", r"\binvite[\s-]only\b", r"\bnotify me\b",
               r"\bget notified\b", r"\bbe the first to (know|try|get|hear)\b", r"\bpre[\s-]?order\b",
               r"\bsign up for (early access|updates|the beta)\b", r"\bstay tuned\b")
LIVE = _rx(r"\bsign[\s-]?up\b", r"\bget started\b", r"\bstart (for )?free\b", r"\btry (it )?(for )?free\b",
           r"\btry (it )?now\b", r"\bstart (your )?(free )?trial\b", r"\blog[\s-]?in\b", r"\bsign[\s-]?in\b",
           r"\bdownload\b", r"\binstall\b", r"\badd to (chrome|firefox|edge|safari|slack|arc)\b",
           r"\bopen (the )?app\b", r"\blaunch (the )?app\b", r"\bnpm (i|install)\b", r"\bpip install\b",
           r"\bbrew install\b", r"\bcreate (an? )?(free )?account\b", r"\bplayground\b", r"\bgo to (the )?app\b")
PRICING = _rx(r"\bpricing\b", r"\bper month\b", r"/\s?mo(nth)?\b", r"[$€£]\s?\d", r"\d\s?[$€£]",
              r"\bper (user|seat)\b", r"\blifetime (deal|access|license)\b", r"\bone[\s-]time (payment|purchase)\b")
FREE_OFFER = _rx(r"\bfree plan\b", r"\bfree tier\b", r"\bfree forever\b", r"\bfree trial\b", r"\btry (it )?(for )?free\b",
                 r"\bstart (for )?free\b", r"\bno credit card\b", r"\bno card required\b", r"\bfree to (use|start|try)\b",
                 r"\b100% free\b", r"\bopen[\s-]source\b", r"[$€£]\s?0(?![.,]?\d)")
CREDIT_CARD = _rx(r"\bcredit card (is )?required\b", r"\brequires? (a )?(credit )?card\b", r"\bcard required\b",
                  r"\benter (your )?(card|payment) (details|information|info)\b")
NO_CARD = _rx(r"\bno credit card\b", r"\bno card required\b", r"\bwithout a credit card\b")
DEMO_ONLY = _rx(r"\bbook a (demo|call)\b", r"\brequest a demo\b", r"\bschedule a (demo|call)\b", r"\bcontact sales\b",
                r"\btalk to sales\b", r"\bget a demo\b")
UPVOTE = _rx(r"\bup[\s-]?vot(e|es|ed|ing)\b", r"\bvote for us\b", r"\bgive us (a|your) vote\b", r"\bsupport us with (a|your) vote\b")
# Superlatives and rank claims: the same patterns as check_launch_kit.py and audit_repo.py.
SUPERLATIVES = (r"\b(?:best|smartest|greatest|fastest|easiest|simplest|finest|coolest|the\s+most\s+[\w-]+)\b.{0,40}\bever\b",
                r"\bever\s+(?:made|built|created|invented|designed|launched)\b",
                r"\b(?:world|industry|internet|planet)['’]?s\s+(?:first|best|most|leading|smartest|fastest|only|largest|"
                r"number[\s-]one|#1)(?!\w)", r"\b(?:smartest|greatest)\b",
                r"\bmost\s+(?:advanced|powerful|intelligent|innovative|revolutionary|amazing|incredible)\b",
                r"(?<![\w&#])#1(?!\w)", r"\bnumber[\s-]one\b", r"\bno\.\s?1\b")
HYPE = _rx(r"\brevolution(ary|i[sz]e|i[sz]ing)\b", r"\bgame[\s-]?chang(er|ing)\b", r"\bultimate\b", r"\bcutting[\s-]edge\b",
           r"\bnext[\s-]gen(eration)?\b", r"\bdisrupt(ive|ing|s)?\b", r"\bunparalleled\b", r"\bmind[\s-]?blowing\b",
           r"\b10x\b", r"\bgroundbreaking\b", r"\bstate[\s-]of[\s-]the[\s-]art\b", r"(?m)^\s*the best\b",
           r"\bunlike anything\b", *SUPERLATIVES)
PLACEHOLDER = _rx(r"\blorem ipsum\b", r"\bdolor sit amet\b", r"\bexample\.com\b", r"\byour (company|product|brand|app) name\b",
                  r"\bacme\b", r"\bTODO\b", r"\bplaceholder\b", r"\binsert (text|copy|link) here\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U0001F900-\U0001F9FF⭐⬆✨]")
CTA_TEXT = re.compile(r"(get started|sign ?up|start|try|download|install|join|request|book|demo|pricing|log ?in|sign ?in|"
                      r"buy|subscribe|get it|open app|launch app|add to|waitlist|early access|contact)", re.I)

THIRD_PARTY = {
    "analytics": [
        ("Google Analytics / Tag Manager", r"googletagmanager\.com|google-analytics\.com|\bgtag\("),
        ("Plausible", r"plausible\.io|next-plausible"), ("PostHog", r"posthog"), ("Mixpanel", r"mixpanel"),
        ("Segment", r"cdn\.segment\.(com|io)|segment\.com/analytics"), ("Amplitude", r"amplitude\.com|cdn\.amplitude"),
        ("Fathom", r"usefathom\.com"), ("Umami", r"umami"), ("Simple Analytics", r"simpleanalytics"),
        ("Vercel Web Analytics", r"/_vercel/insights|va\.vercel-scripts\.com"),
        ("Cloudflare Web Analytics", r"static\.cloudflareinsights\.com"), ("Microsoft Clarity", r"clarity\.ms"),
        ("Hotjar", r"hotjar"), ("Heap", r"heapanalytics|cdn\.heapanalytics|heap\.io"), ("Matomo", r"matomo|piwik"),
        ("Pirsch", r"pirsch"), ("GoatCounter", r"goatcounter"), ("Meta Pixel", r"connect\.facebook\.net|\bfbq\("),
        ("LinkedIn Insight", r"snap\.licdn\.com"), ("X/Twitter pixel", r"static\.ads-twitter\.com"),
    ],
    "error_monitoring": [
        ("Sentry", r"sentry"), ("Bugsnag", r"bugsnag"), ("LogRocket", r"logrocket|lr-ingest"),
        ("Datadog RUM", r"datadoghq|dd_rum|datadog-rum"), ("Rollbar", r"rollbar"), ("Highlight", r"highlight\.(io|run)"),
        ("New Relic", r"nr-data\.net|newrelic"), ("Raygun", r"raygun"), ("TrackJS", r"trackjs"),
    ],
    "chat_support": [
        ("Intercom", r"intercom"), ("Crisp", r"crisp\.chat"), ("Drift", r"driftt?\.com"),
        ("HubSpot", r"hs-scripts\.com|hs-analytics|hubspot"), ("Tawk.to", r"tawk\.to"), ("Zendesk", r"zdassets\.com|zopim"),
        ("Help Scout", r"helpscout"), ("Chatwoot", r"chatwoot"), ("Olark", r"olark"), ("Tidio", r"tidio"),
        ("LiveChat", r"livechatinc"), ("Freshchat", r"freshchat"),
    ],
    "payments": [
        ("Stripe", r"js\.stripe\.com|buy\.stripe\.com|checkout\.stripe\.com"), ("Paddle", r"paddle\.(com|js)"),
        ("Lemon Squeezy", r"lemonsqueezy|lmsqueezy"), ("Gumroad", r"gumroad"), ("Polar", r"polar\.sh"),
        ("Chargebee", r"chargebee"),
    ],
    "consent": [
        ("Cookiebot", r"cookiebot"), ("OneTrust", r"onetrust|cookielaw\.org"), ("Osano", r"osano"),
        ("Termly", r"termly"), ("iubenda", r"iubenda"), ("CookieYes", r"cookieyes"), ("Axeptio", r"axeptio"),
        ("Didomi", r"didomi"), ("Usercentrics", r"usercentrics"), ("Klaro", r"klaro"),
    ],
    "video_demo": [
        ("YouTube", r"youtube\.com/(embed|watch)|youtu\.be|youtube-nocookie"), ("Vimeo", r"player\.vimeo|vimeo\.com/\d"),
        ("Loom", r"loom\.com/(share|embed)"), ("Wistia", r"wistia"), ("Arcade", r"arcade\.software"),
        ("Storylane", r"storylane"), ("Supademo", r"supademo"), ("Navattic", r"navattic"), ("Hexus", r"hexus"),
    ],
    "product_hunt": [
        ("Product Hunt badge/embed", r"api\.producthunt\.com/widgets"), ("Product Hunt link", r"producthunt\.com/(posts|products|launches)"),
    ],
}
THIRD_PARTY = {k: [(n, re.compile(p, re.I)) for n, p in v] for k, v in THIRD_PARTY.items()}

LINK_KINDS = [
    ("app_store", r"apps\.apple\.com|itunes\.apple\.com"), ("google_play", r"play\.google\.com/store"),
    ("chrome_web_store", r"chromewebstore\.google\.com|chrome\.google\.com/webstore"),
    ("firefox_addons", r"addons\.mozilla\.org"), ("edge_addons", r"microsoftedge\.microsoft\.com/addons"),
    ("vscode_marketplace", r"marketplace\.visualstudio\.com"), ("jetbrains_marketplace", r"plugins\.jetbrains\.com"),
    ("microsoft_store", r"apps\.microsoft\.com"), ("npm", r"npmjs\.com/package"), ("pypi", r"pypi\.org/project"),
    ("github", r"github\.com/[^/]+/[^/?#]+"), ("x_twitter", r"(^|//)(www\.)?(x|twitter)\.com/"),
    ("linkedin", r"linkedin\.com/"), ("discord", r"discord\.(gg|com/invite)"), ("youtube", r"youtube\.com/|youtu\.be/"),
    ("reddit", r"reddit\.com/r/"), ("bluesky", r"bsky\.app/"), ("instagram", r"instagram\.com/"),
    ("tiktok", r"tiktok\.com/"), ("threads", r"threads\.net/"), ("product_hunt", r"producthunt\.com/"),
]
LINK_KINDS = [(k, re.compile(p, re.I)) for k, p in LINK_KINDS]
LEGAL = {
    "privacy": re.compile(r"privacy|datenschutz|privacidad|confidentialit", re.I),
    "terms": re.compile(r"\bterms\b|/terms|\btos\b|conditions|\bagb\b|condiciones", re.I),
    "cookies": re.compile(r"cookie", re.I),
    "imprint": re.compile(r"imprint|impressum|aviso[\s-]legal|legal[\s-]notice|mentions[\s-]l[ée]gales", re.I),  # lang:es: legal-page names are data
}
CONTACT = re.compile(r"^mailto:|contact|support|help|/docs|documentation|status\.|/status", re.I)
BOT_BLOCKING_HOSTS = re.compile(r"(^|\.)(linkedin\.com|x\.com|twitter\.com|instagram\.com|facebook\.com|tiktok\.com|"
                                r"reddit\.com|producthunt\.com|medium\.com|crunchbase\.com|g2\.com)$", re.I)
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg", "head"}


# --------------------------------------------------------------------------- HTTP
class _Recorder(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append({"status": code, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, method="GET", timeout=15.0, max_bytes=3_000_000, ua=DEFAULT_UA, accept="*/*"):
    rec = _Recorder()
    opener = urllib.request.build_opener(rec)
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": ua, "Accept": accept, "Accept-Language": "en-US,en;q=0.9"})
    t0 = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(max_bytes) if method != "HEAD" else b""
            return {"ok": 200 <= resp.status < 400, "status": resp.status, "url": resp.geturl(),
                    "headers": {k.lower(): v for k, v in resp.headers.items()}, "body": body,
                    "elapsed_ms": int((time.monotonic() - t0) * 1000), "redirects": rec.chain}
    except urllib.error.HTTPError as e:
        try:
            body = e.read(min(max_bytes, 200_000))
        except Exception:
            body = b""
        return {"ok": False, "status": e.code, "url": e.geturl() or url,
                "headers": {k.lower(): v for k, v in (e.headers or {}).items()}, "body": body,
                "elapsed_ms": int((time.monotonic() - t0) * 1000), "redirects": rec.chain}
    except Exception as e:  # DNS, TLS, timeout, proxy denial...
        return {"ok": False, "status": None, "url": url, "headers": {}, "body": b"", "error": f"{type(e).__name__}: {e}",
                "elapsed_ms": int((time.monotonic() - t0) * 1000), "redirects": rec.chain}


def decode_body(res):
    body = res.get("body") or b""
    ctype = res.get("headers", {}).get("content-type", "")
    m = re.search(r"charset=([\w-]+)", ctype, re.I)
    for enc in ([m.group(1)] if m else []) + ["utf-8", "latin-1"]:
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", "replace")


# --------------------------------------------------------------------------- HTML parsing
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.lang = "", None
        self.metas, self.links, self.anchors, self.images, self.iframes = [], [], [], [], []
        self.scripts, self.forms, self.headings, self.buttons, self.ids = [], [], [], [], set()
        self.text = []
        self._skip = []
        self._in_title = False
        self._anchor = None
        self._heading = None
        self._button = None
        self._form = None
        self._script = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "a":
            self._anchor = {"href": a.get("href", ""), "rel": a.get("rel", ""), "text": [], "aria": a.get("aria-label", "")}
        elif tag == "img":
            self.images.append({"src": a.get("src", "") or a.get("data-src", ""), "alt": a.get("alt")})
            if self._anchor is not None and a.get("alt"):
                self._anchor["text"].append(a["alt"])
        elif tag == "iframe":
            self.iframes.append(a.get("src", ""))
        elif tag == "script":
            self._script = {"src": a.get("src", ""), "attrs": " ".join(f"{k}={v}" for k, v in a.items()), "inline": []}
        elif tag in ("h1", "h2", "h3"):
            self._heading = {"level": int(tag[1]), "text": []}
        elif tag == "button":
            self._button = {"text": [], "aria": a.get("aria-label", "")}
        elif tag == "form":
            self._form = {"action": a.get("action", ""), "method": a.get("method", "get"), "inputs": []}
        elif tag in ("input", "textarea", "select") and self._form is not None:
            self._form["inputs"].append({"tag": tag, "type": a.get("type", "text" if tag == "input" else tag),
                                         "name": a.get("name", ""), "placeholder": a.get("placeholder", "")})
            if tag == "input" and a.get("type") in ("submit", "button") and a.get("value"):
                self.buttons.append(a["value"])
        if tag in SKIP_TEXT_TAGS and tag != "head":
            self._skip.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in ("script", "a", "button", "form", "h1", "h2", "h3", "title", "iframe") or tag in SKIP_TEXT_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self._skip and tag == self._skip[-1]:
            self._skip.pop()
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._anchor is not None:
            self._anchor["text"] = " ".join(" ".join(self._anchor["text"]).split())
            self.anchors.append(self._anchor)
            self._anchor = None
        elif tag in ("h1", "h2", "h3") and self._heading is not None:
            self.headings.append({"level": self._heading["level"], "text": " ".join(" ".join(self._heading["text"]).split())})
            self._heading = None
        elif tag == "button" and self._button is not None:
            txt = " ".join(" ".join(self._button["text"]).split()) or self._button["aria"]
            if txt:
                self.buttons.append(txt)
            self._button = None
        elif tag == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None
        elif tag == "script" and self._script is not None:
            self._script["inline"] = "".join(self._script["inline"])[:4000]
            self.scripts.append(self._script)
            self._script = None

    def handle_data(self, data):
        if self._script is not None:
            self._script["inline"].append(data)
            return
        if self._in_title:
            self.title += data
            return
        if self._skip:
            return
        self.text.append(data)
        for holder in (self._anchor, self._heading, self._button):
            if holder is not None:
                holder["text"].append(data)


# --------------------------------------------------------------------------- helpers
def norm(s):
    return " ".join((s or "").split())


def snippets(patterns, text, limit=8, width=60):
    """Matches of any pattern, clustered so nearby hits share one context snippet."""
    found = sorted({(m.start(), m.end(), m.group(0)) for rx in patterns for m in rx.finditer(text)})
    clusters = []
    for start, end, word in found:
        if clusters and start - clusters[-1]["end"] <= width:
            c = clusters[-1]
            c["end"] = max(c["end"], end)
            if word.lower() not in [w.lower() for w in c["words"]]:
                c["words"].append(word)
        else:
            clusters.append({"start": start, "end": end, "words": [word]})
    out = []
    for c in clusters[:limit]:
        out.append({"match": " | ".join(c["words"]),
                    "context": norm(text[max(0, c["start"] - width):c["end"] + width])})
    return out


def fetch_image(url, timeout):
    res = fetch(url, timeout=timeout, max_bytes=6_000_000, accept="image/avif,image/webp,image/*,*/*;q=0.8")
    info = image_info_from_bytes(res["body"], len(res["body"])) if res.get("body") else None
    return {"url": url, "status": res.get("status"), "error": res.get("error"),
            "content_type": res.get("headers", {}).get("content-type"), "info": info}


KEY_PAGE = re.compile(r"/(pricing|plans|prices|sign-?up|register|get-started|start|join|trial|free-trial|demo|download|"
                      r"install|login|log-in|sign-?in|app)/", re.I)


def same_site(a, b):
    """Same host, or same registrable-looking domain (app.example.com vs example.com)."""
    a, b = a.lower().split(":")[0], b.lower().split(":")[0]
    return a == b or a.split(".")[-2:] == b.split(".")[-2:] and "." in a


def add_query(url, key, value):
    parts = urllib.parse.urlsplit(url)
    q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True) + [(key, value)]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urllib.parse.urlencode(q), ""))


def robots_blocks_all(txt):
    """True when the `User-agent: *` group contains `Disallow: /`."""
    agents, group_has_rules, blocks = [], False, False
    for raw in txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, val = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if group_has_rules:
                agents, group_has_rules = [], False
            agents.append(val)
        elif key in ("disallow", "allow"):
            group_has_rules = True
            if key == "disallow" and val == "/" and "*" in agents:
                blocks = True
    return blocks


def classify_link(href):
    kinds = [k for k, rx in LINK_KINDS if rx.search(href)]
    return kinds


def check_one_link(url, timeout, ua):
    res = fetch(url, method="HEAD", timeout=timeout, ua=ua)
    if res.get("status") in (None, 403, 405, 501) or (res.get("status") or 0) >= 400:
        res = fetch(url, method="GET", timeout=timeout, max_bytes=65536, ua=ua)
    return {"url": url, "status": res.get("status"), "final_url": res.get("url"), "error": res.get("error")}


# --------------------------------------------------------------------------- main audit
def audit(url, html_file=None, check_links=True, max_links=40, timeout=15.0, ua=DEFAULT_UA, max_key_pages=6):
    report = {"input_url": url, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": []}
    main = fetch(url, timeout=timeout, ua=ua, accept="text/html,application/xhtml+xml,*/*;q=0.8")
    final = main.get("url") or url
    report.update({
        "final_url": final, "status": main.get("status"), "error": main.get("error"),
        "https": final.lower().startswith("https://"), "elapsed_ms": main.get("elapsed_ms"),
        "redirects": main.get("redirects"),
        "headers": {k: main["headers"][k] for k in ("content-type", "cache-control", "server", "x-robots-tag",
                                                     "strict-transport-security", "content-encoding", "x-vercel-cache",
                                                     "cf-cache-status", "age") if k in main.get("headers", {})},
    })
    if html_file:
        html = Path(html_file).read_text(encoding="utf-8", errors="replace")
        report["html_source"] = f"file:{html_file}"
    else:
        html = decode_body(main)
        report["html_source"] = "network"
    report["html_bytes"] = len(html.encode("utf-8", "ignore"))
    served_locally = bool(re.match(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:|/|$)", final, re.I))
    report["served_locally"] = served_locally
    if served_locally:
        report["notes"].append("This is a local/dev server: HTTPS, caching and hosting capacity cannot be judged here — "
                               "re-run against the production URL before launch.")
    if main.get("status") is None and not html_file:
        report["notes"].append("The page could not be fetched at all; every other check below is empty. "
                               "If the host is blocked by a network policy, do not work around it — ask the user.")
        return report

    p = PageParser()
    try:
        p.feed(html)
        p.close()
    except Exception as e:  # malformed HTML should not kill the audit
        report["notes"].append(f"HTML parser error: {e}")

    # ---------------- head
    meta = {}
    for m in p.metas:
        key = (m.get("property") or m.get("name") or m.get("itemprop") or "").strip().lower()
        if key and "content" in m and key not in meta:
            meta[key] = m.get("content", "")
    def links_with(rel_word):
        return [l for l in p.links if rel_word in (l.get("rel", "").lower().split())]
    canonical = next((l.get("href") for l in links_with("canonical")), None)
    title = norm(p.title)
    head = {
        "title": title, "title_length": len(title),
        "description": meta.get("description"), "description_length": len(meta.get("description") or ""),
        "lang": p.lang, "viewport": meta.get("viewport"), "canonical": canonical,
        "robots": meta.get("robots"), "theme_color": meta.get("theme-color"),
        "og": {k: v for k, v in meta.items() if k.startswith("og:")},
        "twitter": {k: v for k, v in meta.items() if k.startswith("twitter:")},
    }
    head["noindex"] = bool(re.search(r"noindex", (meta.get("robots") or "") + " " +
                                     report["headers"].get("x-robots-tag", ""), re.I))
    head["emoji_in_title"] = bool(EMOJI.search(title))
    report["head"] = head

    # ---------------- social preview image
    img_url = head["og"].get("og:image") or head["og"].get("og:image:url") or head["twitter"].get("twitter:image")
    social = {"declared": img_url, "issues": []}
    if img_url:
        if not re.match(r"https?://", img_url):
            social["issues"].append("og:image is not an absolute URL (many crawlers ignore relative URLs)")
        if re.search(r"//(localhost|127\.0\.0\.1|0\.0\.0\.0)(:|/|$)", img_url):
            if served_locally:
                report["notes"].append("Auditing a local server: og:image on localhost is expected here, but make sure the "
                                       "production build emits the real domain (check metadataBase / SITE_URL).")
            else:
                social["issues"].append("og:image points to localhost — broken for everyone else")
        resolved = urllib.parse.urljoin(final, img_url)
        social.update(fetch_image(resolved, timeout))
        info = social.get("info")
        if social.get("status") and social["status"] >= 400:
            social["issues"].append(f"og:image returns HTTP {social['status']}")
        elif not info:
            social["issues"].append("og:image did not return a recognisable image")
        else:
            if info.get("width") and info.get("height") and (info["width"] < 1200 or info["height"] < 600):
                social["issues"].append(f"og:image is {info['width']}x{info['height']}; 1200x630 is the usual target")
            if info.get("bytes", 0) > 5_000_000:
                social["issues"].append("og:image is larger than 5 MB; some platforms drop it")
    else:
        social["issues"].append("no og:image / twitter:image declared — shared links render without a preview")
    if not head["og"].get("og:title"):
        social["issues"].append("no og:title")
    if not head["og"].get("og:description"):
        social["issues"].append("no og:description")
    if not head["twitter"].get("twitter:card"):
        social["issues"].append("no twitter:card (use summary_large_image)")
    report["social_image"] = social

    # ---------------- icons & manifest (Product Hunt thumbnail source: 240x240)
    icons = []
    icon_links = [l for l in p.links if "icon" in l.get("rel", "").lower()]
    for l in icon_links[:8]:
        href = urllib.parse.urljoin(final, l.get("href", ""))
        entry = {"rel": l.get("rel"), "href": href, "sizes": l.get("sizes")}
        entry.update({k: v for k, v in fetch_image(href, timeout).items() if k in ("status", "info", "error")})
        icons.append(entry)
    if not any(i["rel"] and "apple" not in i["rel"].lower() for i in icons):
        fav = urllib.parse.urljoin(final, "/favicon.ico")
        entry = {"rel": "(implicit) /favicon.ico", "href": fav, "sizes": None}
        entry.update({k: v for k, v in fetch_image(fav, timeout).items() if k in ("status", "info", "error")})
        icons.append(entry)
    manifest = None
    man_link = next((l for l in p.links if "manifest" in l.get("rel", "").lower()), None)
    if man_link:
        murl = urllib.parse.urljoin(final, man_link.get("href", ""))
        mres = fetch(murl, timeout=timeout, ua=ua)
        manifest = {"url": murl, "status": mres.get("status")}
        try:
            mj = json.loads(decode_body(mres))
            manifest.update({"name": mj.get("name"), "short_name": mj.get("short_name"),
                             "icons": [{"src": i.get("src"), "sizes": i.get("sizes")} for i in mj.get("icons", [])][:12]})
            def _sz(i):
                try:
                    return max(int(s.split("x")[0]) for s in (i.get("sizes") or "0x0").split())
                except ValueError:
                    return 0
            for icon in sorted(mj.get("icons", []), key=_sz, reverse=True)[:2]:
                href = urllib.parse.urljoin(murl, icon.get("src", ""))
                entry = {"rel": "manifest", "href": href, "sizes": icon.get("sizes")}
                entry.update({k: v for k, v in fetch_image(href, timeout).items() if k in ("status", "info", "error")})
                icons.append(entry)
        except (ValueError, AttributeError):
            manifest["error"] = "manifest is not valid JSON"
    report["icons"] = icons
    report["manifest"] = manifest
    best = None
    for i in icons:
        inf = i.get("info") or {}
        if inf.get("vector"):
            best = {"href": i["href"], "width": inf.get("width"), "height": inf.get("height"), "vector": True}
            break
        w, h = inf.get("width") or 0, inf.get("height") or 0
        if w and h and (best is None or w * h > (best["width"] or 0) * (best["height"] or 0)):
            best = {"href": i["href"], "width": w, "height": h, "vector": False}
    report["best_icon"] = best
    report["thumbnail_source_ok"] = bool(best and (best.get("vector") or (min(best["width"], best["height"]) >= 240)))
    if best is None:
        report["notes"].append("No usable icon was found: the site has no favicon/app icon, and there is no obvious "
                               "source for Product Hunt's 240x240 thumbnail.")

    # ---------------- content
    body_text = norm(" ".join(p.text))
    cta_items = [{"text": a["text"] or a.get("aria", ""), "href": a["href"]} for a in p.anchors
                 if CTA_TEXT.search(a["text"] or a.get("aria", "") or "")]
    cta_items += [{"text": b, "href": None} for b in p.buttons if CTA_TEXT.search(b)]
    placeholders_text = " ".join(i["placeholder"] for f in p.forms for i in f["inputs"] if i.get("placeholder"))
    signal_text = " ".join([body_text, " ".join(p.buttons), placeholders_text])
    h1 = [h["text"] for h in p.headings if h["level"] == 1]
    h2 = [h["text"] for h in p.headings if h["level"] == 2][:12]
    headline_text = " \n ".join([title, meta.get("description") or "", head["og"].get("og:title", ""),
                                 head["og"].get("og:description", "")] + h1 + h2[:3])
    forms = []
    for f in p.forms:
        types = [i["type"] for i in f["inputs"] if i["type"] not in ("hidden", "submit", "button")]
        forms.append({"action": f["action"], "method": f["method"], "fields": types,
                      "email_only": types == ["email"] or (len(types) == 1 and "email" in (f["inputs"][0]["name"] or "").lower()),
                      "field_count": len(types)})
    words = len(body_text.split())
    spa = (words < 60 and bool(p.ids & {"root", "app", "__next", "__nuxt", "svelte", "___gatsby"})) or \
          (words < 25 and len(p.scripts) >= 2)
    report["content"] = {
        "h1": h1, "h2": h2, "word_count": len(body_text.split()),
        "hero_text": body_text[:700], "ctas": cta_items[:25], "buttons": p.buttons[:25], "forms": forms,
        "images": len(p.images), "images_missing_alt": sum(1 for i in p.images if i["alt"] is None),
        "spa_shell_suspected": spa,
    }
    if spa:
        report["notes"].append("Very little server-rendered text: this looks like a client-rendered app shell. "
                               "Render it in a browser (capture_screenshots.cjs --dump-html) and re-run with --html-file, "
                               "and note that crawlers/link previews may see an empty page.")

    report["signals"] = {
        "waitlist": snippets(WAITLIST, signal_text),
        "live_product": snippets(LIVE, signal_text),
        "pricing": snippets(PRICING, signal_text, limit=6),
        "free_offer": snippets(FREE_OFFER, signal_text, limit=6),
        "credit_card_required": snippets(CREDIT_CARD, signal_text),
        "no_card_required": snippets(NO_CARD, signal_text, limit=3),
        "demo_or_sales_only_ctas": snippets(DEMO_ONLY, signal_text),
        "upvote_asks": snippets(UPVOTE, signal_text + " " + " ".join(a["text"] for a in p.anchors)),
        "hype_in_headlines": snippets(HYPE, headline_text, width=40),
        "emoji_in_headlines": bool(EMOJI.search(" ".join([title] + h1))),
        "placeholders": snippets(PLACEHOLDER, signal_text + " " + " ".join(a["href"] for a in p.anchors)),
        "email_capture_forms": sum(1 for f in forms if f["email_only"]),
    }

    # ---------------- third parties
    scan_blob = "\n".join([s["src"] + " " + s["attrs"] + " " + s["inline"] for s in p.scripts] +
                          [l.get("href", "") for l in p.links] + p.iframes + [a["href"] for a in p.anchors] +
                          [i["src"] for i in p.images])
    report["third_party"] = {cat: sorted({name for name, rx in pats if rx.search(scan_blob)})
                             for cat, pats in THIRD_PARTY.items()}

    # ---------------- links
    base_host = urllib.parse.urlparse(final).netloc.lower()
    all_links, kinds = [], {}
    legal = {k: [] for k in LEGAL}
    contact, empty_hrefs = [], 0
    for a in p.anchors:
        href = a["href"].strip()
        if not href or href == "#" or href.lower().startswith("javascript:"):
            empty_hrefs += 1
            continue
        absu = urllib.parse.urljoin(final, href)
        label = a["text"] or a.get("aria", "")
        for k in classify_link(absu):
            kinds.setdefault(k, [])
            if absu not in kinds[k]:
                kinds[k].append(absu)
        for k, rx in LEGAL.items():
            if rx.search(href) or rx.search(label):
                legal[k].append(absu)
        if CONTACT.search(href) or re.search(r"contact|support|help", label, re.I):
            contact.append(absu)
        if absu.startswith(("http://", "https://")):
            all_links.append((absu, label))
    uniq, seen = [], set()
    for u, label in all_links:
        u_nofrag = u.split("#")[0]
        if u_nofrag not in seen:
            seen.add(u_nofrag)
            uniq.append((u_nofrag, label))
    uniq.sort(key=lambda t: (0 if CTA_TEXT.search(t[1] or "") else 1,
                             0 if urllib.parse.urlparse(t[0]).netloc.lower() == base_host else 1))
    links_report = {"total_unique": len(uniq), "empty_or_hash_hrefs": empty_hrefs, "kinds": kinds,
                    "legal": {k: sorted(set(v))[:3] for k, v in legal.items()}, "contact": sorted(set(contact))[:8],
                    "checked": 0, "broken": [], "unverified": []}
    if check_links and uniq:
        targets = uniq[:max_links]
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(lambda t: check_one_link(t[0], min(timeout, 12.0), ua), targets))
        links_report["checked"] = len(results)
        for (u, label), r in zip(targets, results):
            host = urllib.parse.urlparse(u).netloc.lower()
            st = r["status"]
            item = {"url": u, "text": label[:80], "status": st, "error": r.get("error")}
            if st is not None and st < 400:
                continue
            if BOT_BLOCKING_HOSTS.search(host) and st in (None, 400, 401, 403, 429, 999):
                links_report["unverified"].append(item)
            else:
                links_report["broken"].append(item)
        if len(uniq) > max_links:
            report["notes"].append(f"Only the first {max_links} of {len(uniq)} links were checked (CTAs first).")
    report["links"] = links_report

    # ---------------- key internal pages: pricing, sign-up, trial/demo, download
    key_pages, seen_paths = [], set()
    for u, label in uniq:
        pu = urllib.parse.urlparse(u)
        if not same_site(pu.netloc, base_host) or not KEY_PAGE.search(pu.path.rstrip("/") + "/"):
            continue
        k = (pu.netloc.lower(), pu.path.rstrip("/"))
        if k in seen_paths or k == (base_host, urllib.parse.urlparse(final).path.rstrip("/")):
            continue
        seen_paths.add(k)
        key_pages.append((u, label))
        if len(key_pages) >= max_key_pages:
            break
    pages = []
    for u, label in key_pages:
        res = fetch(u, timeout=timeout, ua=ua, accept="text/html,*/*;q=0.8")
        entry = {"url": u, "link_text": (label or "")[:60], "status": res.get("status"), "final_url": res.get("url"),
                 "error": res.get("error")}
        if res.get("status") and res["status"] < 400:
            pp = PageParser()
            try:
                pp.feed(decode_body(res))
                pp.close()
            except Exception:
                pass
            ph = " ".join(i["placeholder"] for f in pp.forms for i in f["inputs"] if i.get("placeholder"))
            txt = " ".join([norm(" ".join(pp.text)), " ".join(pp.buttons), ph])
            entry.update({
                "title": norm(pp.title), "h1": [h["text"] for h in pp.headings if h["level"] == 1][:3],
                "word_count": len(norm(" ".join(pp.text)).split()),
                "signals": {"pricing": snippets(PRICING, txt, limit=4), "free_offer": snippets(FREE_OFFER, txt, limit=4),
                            "credit_card_required": snippets(CREDIT_CARD, txt, limit=3),
                            "no_card_required": snippets(NO_CARD, txt, limit=2),
                            "demo_or_sales_only_ctas": snippets(DEMO_ONLY, txt, limit=3),
                            "waitlist": snippets(WAITLIST, txt, limit=3), "upvote_asks": snippets(UPVOTE, txt, limit=3)},
                "forms": [{"field_count": len([i for i in f["inputs"] if i["type"] not in ("hidden", "submit", "button")]),
                           "fields": [i["name"] or i["type"] for i in f["inputs"] if i["type"] not in ("hidden", "submit", "button")][:15]}
                          for f in pp.forms][:4],
                "oauth_buttons": [b for b in pp.buttons + [a["text"] for a in pp.anchors]
                                  if re.search(r"(continue|sign (in|up)|log in) with (google|github|apple|microsoft|x|twitter|linkedin)", b, re.I)][:4],
            })
        pages.append(entry)
    report["key_pages"] = pages

    # ---------------- ?ref=producthunt must still load
    ref_url = add_query(final, "ref", "producthunt")
    ref = fetch(ref_url, timeout=timeout, ua=ua, max_bytes=200_000)
    report["ref_param_check"] = {"url": ref_url, "status": ref.get("status"),
                                 "final_url": ref.get("url"), "error": ref.get("error"),
                                 "ok": ref.get("status") is not None and ref["status"] < 400}

    # ---------------- robots / sitemap
    origin = f"{urllib.parse.urlparse(final).scheme}://{base_host}"
    rb = fetch(origin + "/robots.txt", timeout=timeout, ua=ua, max_bytes=200_000)
    robots_txt = decode_body(rb) if rb.get("status") == 200 else ""
    report["robots_txt"] = {"status": rb.get("status"), "blocks_all_crawlers": robots_blocks_all(robots_txt),
                            "sitemap_declared": bool(re.search(r"^sitemap:", robots_txt, re.I | re.M))}
    sm = fetch(origin + "/sitemap.xml", method="GET", timeout=timeout, ua=ua, max_bytes=65536)
    report["sitemap"] = {"status": sm.get("status")}
    return report


# --------------------------------------------------------------------------- summary
def summarize(r):
    ok, bad, warn = "✓", "✗", "!"
    lines = [f"URL audit: {r['input_url']}  →  {r.get('final_url')}  (HTTP {r.get('status')}, {r.get('elapsed_ms')} ms)"]
    if r.get("status") is None and r.get("html_source") == "network":
        lines.append(f"{bad} could not fetch: {r.get('error')}")
        return "\n".join(lines + [f"{warn} {n}" for n in r.get("notes", [])])
    h, s, c, sig, l = r.get("head", {}), r.get("social_image", {}), r.get("content", {}), r.get("signals", {}), r.get("links", {})
    lines.append(f"{ok if r.get('https') else (warn if r.get('served_locally') else bad)} HTTPS"
                 + (" (local server — check production)" if r.get("served_locally") and not r.get("https") else ""))
    lines.append(f"{ok if h.get('title') else bad} <title>: {h.get('title')!r} ({h.get('title_length')} chars)")
    lines.append(f"{ok if h.get('description') else bad} meta description ({h.get('description_length')} chars)")
    lines.append(f"{ok if h.get('viewport') else bad} viewport meta (mobile)")
    if h.get("noindex"):
        lines.append(f"{bad} page is marked noindex")
    inf = s.get("info") or {}
    dims = f" {inf.get('width')}x{inf.get('height')}" if inf.get("width") else ""
    lines.append(f"{ok if not s.get('issues') else bad} social preview: {s.get('declared') or 'none'}{dims}"
                 + ("" if not s.get("issues") else "  — " + "; ".join(s["issues"])))
    b = r.get("best_icon")
    lines.append(f"{ok if r.get('thumbnail_source_ok') else warn} best icon for a 240x240 thumbnail: "
                 + (f"{b['href']} ({b['width']}x{b['height']}{', vector' if b.get('vector') else ''})" if b else "none found"))
    lines.append(f"  H1: {c.get('h1')}")
    lines.append(f"  CTAs: {[x['text'] for x in c.get('ctas', [])][:10]}")
    for key, label in (("waitlist", "waitlist/coming-soon copy"), ("upvote_asks", "asks for upvotes"),
                       ("credit_card_required", "credit card required"), ("demo_or_sales_only_ctas", "demo/sales CTAs"),
                       ("hype_in_headlines", "hype words in headlines"), ("placeholders", "placeholder copy")):
        if sig.get(key):
            lines.append(f"{warn} {label}: " + " | ".join(x["context"] for x in sig[key][:3]))
    lines.append(f"  live-product CTAs found: {len(sig.get('live_product', []))}; pricing mentions: {len(sig.get('pricing', []))};"
                 f" free offer mentions: {len(sig.get('free_offer', []))}")
    tp = r.get("third_party", {})
    for cat in ("analytics", "error_monitoring", "chat_support", "payments", "consent", "video_demo", "product_hunt"):
        miss = bad if cat == "analytics" else warn if cat in ("error_monitoring", "chat_support") else "·"
        lines.append(f"{ok if tp.get(cat) else miss} {cat}: {', '.join(tp.get(cat) or []) or 'none detected'}"
                     + (" (client-side only; server-side tools are invisible here)" if cat == "error_monitoring" and not tp.get(cat) else ""))
    lg = l.get("legal", {})
    lines.append(f"{ok if lg.get('privacy') else warn} privacy link   {ok if lg.get('terms') else warn} terms link   "
                 f"{ok if l.get('contact') else warn} contact/support link")
    lines.append(f"  links: {l.get('total_unique')} unique, {l.get('checked')} checked, {len(l.get('broken', []))} broken, "
                 f"{len(l.get('unverified', []))} unverified (bot-protected hosts), {l.get('empty_or_hash_hrefs')} empty/# hrefs")
    for x in l.get("broken", [])[:10]:
        lines.append(f"{bad} broken link [{x.get('status') or x.get('error')}]: {x['url']}  (text: {x['text']!r})")
    for kp in r.get("key_pages", []):
        sg = kp.get("signals", {})
        st = kp.get("status")
        flag = ok if st and st < 400 else bad
        extra = ""
        if st and st < 400:
            extra = (f" — title {kp.get('title')!r}; free offer: {len(sg.get('free_offer', []))}, prices: {len(sg.get('pricing', []))},"
                     f" card required: {len(sg.get('credit_card_required', []))}, no-card: {len(sg.get('no_card_required', []))},"
                     f" forms: {[f['field_count'] for f in kp.get('forms', [])]}, OAuth: {len(kp.get('oauth_buttons', []))}")
            for key in ("waitlist", "upvote_asks", "credit_card_required", "demo_or_sales_only_ctas"):
                if sg.get(key):
                    extra += f"\n    {warn} {key}: {sg[key][0]['context'][:140]}"
        lines.append(f"{flag} key page {kp['url']} (HTTP {st or kp.get('error')}){extra}")
    rp = r.get("ref_param_check", {})
    lines.append(f"{ok if rp.get('ok') else bad} ?ref=producthunt loads (HTTP {rp.get('status')})")
    rb = r.get("robots_txt", {})
    if rb.get("blocks_all_crawlers"):
        lines.append(f"{bad} robots.txt disallows all crawlers")
    for n in r.get("notes", []):
        lines.append(f"{warn} {n}")
    return "\n".join(lines)


def utf8_console():
    """Print non-ASCII (✓, ≥, —, emoji from the input) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--json", help="write the full evidence JSON here")
    ap.add_argument("--html-file", help="parse this (browser-rendered) HTML instead of the fetched body")
    ap.add_argument("--no-links", action="store_true", help="skip checking links")
    ap.add_argument("--max-links", type=int, default=40)
    ap.add_argument("--max-key-pages", type=int, default=6, help="pricing/sign-up/demo pages to fetch and analyse")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--user-agent", default=DEFAULT_UA)
    ap.add_argument("--quiet", action="store_true", help="do not print the summary")
    args = ap.parse_args()
    url = args.url if re.match(r"https?://", args.url) else "https://" + args.url
    r = audit(url, html_file=args.html_file, check_links=not args.no_links, max_links=args.max_links,
              timeout=args.timeout, ua=args.user_agent, max_key_pages=args.max_key_pages)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    if not args.quiet:
        print(summarize(r))
        if args.json:
            print(f"\nFull evidence: {args.json}")


if __name__ == "__main__":
    main()
