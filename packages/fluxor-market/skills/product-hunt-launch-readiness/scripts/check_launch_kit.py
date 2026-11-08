#!/usr/bin/env python3
"""Validate a Product Hunt launch kit against the launch form's limits and rules.

Character counting and limit checks are exactly the kind of thing that goes
wrong when done by eye, so every drafted or user-supplied field goes through
this script.

Usage:
    # full kit (see assets/launch-kit.template.json for the shape)
    python3 check_launch_kit.py launch-kit.json --markdown launch-kit.md

    # quick check of candidate strings (repeat flags to compare options)
    python3 check_launch_kit.py --tagline "Invoices that chase themselves" --tagline "Another option" --name "Tallyfox"

Exit code 1 when any FAIL is found. Limits are from Product Hunt's launch guide
and submission form as of 2026 — see references/product-hunt-guide.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imgmeta import image_info  # noqa: E402

LIMITS = {"name": 40, "tagline": 60, "description": 500, "description_visible": 260, "first_comment_visible": 800,
          "launch_tags": 3, "shoutouts": 3, "gallery_min": 2, "gallery_recommended": 3}
PRICING = {"free": "Free", "paid": "Paid", "paid_with_free_trial_or_plan": "Paid (with a free trial or plan)"}
UPVOTE = re.compile(r"\bup[\s-]?vot(e|es|ed|ing)\b|\bvote for us\b|\bgive us (a|your) vote\b|\bsmash that\b", re.I)
REWARD = re.compile(r"\b(giveaway|raffle|prize|free month|discount|reward)\b.{0,60}\b(upvot|vote)|\b(upvot|vote).{0,60}\b(giveaway|raffle|prize|reward)", re.I)
# Superlatives and rank claims ("the smartest ... ever made", "world's first", "#1"). The same
# patterns are in audit_repo.py and audit_url.py; keep the three lists in step.
SUPERLATIVES = (r"\b(?:best|smartest|greatest|fastest|easiest|simplest|finest|coolest|the\s+most\s+[\w-]+)\b.{0,40}\bever\b",
                r"\bever\s+(?:made|built|created|invented|designed|launched)\b",
                r"\b(?:world|industry|internet|planet)['’]?s\s+(?:first|best|most|leading|smartest|fastest|only|largest|"
                r"number[\s-]one|#1)(?!\w)", r"\b(?:smartest|greatest)\b",
                r"\bmost\s+(?:advanced|powerful|intelligent|innovative|revolutionary|amazing|incredible)\b",
                r"(?<![\w&#])#1(?!\w)", r"\bnumber[\s-]one\b", r"\bno\.\s?1\b")
HYPE = re.compile("|".join((r"\brevolution(ary|i[sz]e|i[sz]ing)\b", r"\bgame[\s-]?chang(er|ing)\b", r"\bultimate\b",
                            r"\bcutting[\s-]edge\b", r"\bnext[\s-]gen(eration)?\b", r"\bunparalleled\b",
                            r"\bmind[\s-]?blowing\b", r"\bgroundbreaking\b", r"\bstate[\s-]of[\s-]the[\s-]art\b",
                            r"^\s*the best\b", r"\b10x\b", r"\bdisrupt") + SUPERLATIVES), re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF⭐⬆✨‼⁉]")
VIDEO_HOSTS = re.compile(r"(youtube\.com|youtu\.be|loom\.com)/", re.I)
DEMO_HOSTS = re.compile(r"arcade\.software|storylane|hexus|supademo|layerpath|screenspace|navattic", re.I)
IMG_FORMATS = {"png", "jpeg", "gif"}
TODO = re.compile(r"\[TODO|\bTODO:|\bTBD\b|<launch link>|\{\{", re.I)


def clen(s: str) -> int:
    """Characters as a person (and the launch form) counts them: NFC code points."""
    return len(unicodedata.normalize("NFC", s or ""))


class Report:
    def __init__(self):
        self.rows = []

    def add(self, level, field, msg):
        self.rows.append((level, field, msg))

    def ok(self, f, m):
        self.add("PASS", f, m)

    def warn(self, f, m):
        self.add("WARN", f, m)

    def fail(self, f, m):
        self.add("FAIL", f, m)

    @property
    def failed(self):
        return any(r[0] == "FAIL" for r in self.rows)

    def text(self):
        icon = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}
        out = [f"{icon[l]} {l:<4} {f:<16} {m}" for l, f, m in self.rows]
        c = {k: sum(1 for r in self.rows if r[0] == k) for k in ("PASS", "WARN", "FAIL")}
        out.append(f"\n{c['FAIL']} fail, {c['WARN']} warn, {c['PASS']} pass")
        if hasattr(self, "paste_ready"):
            out.append("Paste-ready: yes" if self.paste_ready else
                       "Paste-ready: NO — " + ", ".join((["fix the FAILs"] if self.failed else []) + self.blockers_to_paste))
        return "\n".join(out)


def check_text_field(rep, field, value, limit, required=True):
    if not value:
        (rep.fail if required else rep.warn)(field, "missing")
        return
    n = clen(value)
    if n > limit:
        rep.fail(field, f"{n}/{limit} chars — over the limit by {n - limit}: {value!r}")
    else:
        rep.ok(field, f"{n}/{limit} chars: {value!r}")


def check_tagline(rep, t, name=None, label="tagline"):
    check_text_field(rep, label, t, LIMITS["tagline"])
    if not t:
        return
    if EMOJI.search(t):
        rep.warn(label, "contains emoji — the guide asks for no gimmicks; say what the product does")
    if HYPE.search(t):
        rep.warn(label, f"hype wording ({HYPE.search(t).group(0)!r}) — Product Hunt: don't say 'the best ever', say how it helps")
    if name and name.lower() in t.lower():
        rep.warn(label, "repeats the product name, which is already shown right above the tagline")
    if t.strip().endswith("!") or len(re.findall(r"\b[A-Z]{4,}\b", t)) >= 2:
        rep.warn(label, "shouting (exclamation mark / ALL CAPS) reads as marketing, not description")
    if UPVOTE.search(t):
        rep.fail(label, "mentions upvotes")


def check_image(rep, field, path, kind, base: Path):
    if re.match(r"https?://", str(path)):
        rep.warn(field, f"{path}: remote file, dimensions not verified — download it and re-run to check")
        return
    p = (base / path) if not Path(path).is_absolute() else Path(path)
    if not p.exists():
        rep.fail(field, f"{path}: file not found")
        return
    info = image_info(p) or {}
    fmt, w, h, size = info.get("format"), info.get("width"), info.get("height"), info.get("bytes", 0)
    mb = size / 1_048_576 if size else 0
    desc = f"{path}: {fmt} {w}x{h}, {mb:.2f} MB" + (" animated" if info.get("animated") else "")
    problems = []
    if fmt not in IMG_FORMATS:
        problems.append(("FAIL", f"format {fmt} — upload JPG, PNG or GIF"))
    if kind == "thumbnail":
        if w and h and w != h:
            problems.append(("FAIL", "thumbnail must be square"))
        if w and w < 240:
            problems.append(("FAIL", "smaller than 240x240 — it will look blurry"))
        elif w and w != 240:
            problems.append(("WARN", "240x240 is the recommended size (larger square images are downscaled)"))
        if mb > 3:
            problems.append(("FAIL", "over 3 MB"))
        elif mb > 2:
            problems.append(("WARN", "over 2 MB — the form has capped thumbnails at 2 MB; compress it"))
    else:
        if w and h:
            if w < 1270 or h < 760:
                problems.append(("WARN", "smaller than the recommended 1270x760"))
            if abs((w / h) - (1270 / 760)) > 0.08:
                problems.append(("WARN", f"aspect {w / h:.2f} differs from 1270x760 (1.67) — it will be cropped or letterboxed"))
        if mb > 3:
            problems.append(("FAIL", "over 3 MB — the guide asks for gallery images under 3 MB"))
    if not problems:
        rep.ok(field, desc)
    for lvl, m in problems:
        rep.add(lvl, field, f"{desc} — {m}")


def check_kit(kit: dict, base: Path) -> Report:
    rep = Report()
    name = kit.get("name", "")
    check_text_field(rep, "name", name, LIMITS["name"])
    if name and EMOJI.search(name):
        rep.warn("name", "contains emoji")
    check_tagline(rep, kit.get("tagline", ""), name)
    for i, alt in enumerate(kit.get("tagline_alternatives") or [], 1):
        check_tagline(rep, alt, name, label=f"tagline_alt[{i}]")

    d = kit.get("description", "")
    check_text_field(rep, "description", d, LIMITS["description"])
    if d and clen(d) > LIMITS["description_visible"]:
        cut = unicodedata.normalize("NFC", d)[:LIMITS["description_visible"]]
        rep.warn("description", f"only about the first {LIMITS['description_visible']} chars show before truncation; "
                                f"make sure they carry the core message: {cut!r}…")
    if d and HYPE.search(d):
        rep.warn("description", f"hype wording ({HYPE.search(d).group(0)!r})")

    tags = kit.get("launch_tags") or []
    if not tags:
        rep.fail("launch_tags", "missing — pick up to 3 existing Product Hunt topics")
    elif len(tags) > LIMITS["launch_tags"]:
        rep.fail("launch_tags", f"{len(tags)} tags; the form allows up to {LIMITS['launch_tags']}: {tags}")
    else:
        rep.ok("launch_tags", f"{len(tags)}/3: {tags}")

    links = kit.get("links") or {}
    site = links.get("website") if isinstance(links, dict) else None
    if not site:
        rep.fail("links.website", "missing primary link")
    elif not str(site).startswith("https://"):
        rep.warn("links.website", f"{site} is not https")
    else:
        rep.ok("links.website", site)
    extra = (links.get("additional") or []) if isinstance(links, dict) else []
    if len(extra) > 3:
        rep.warn("links", f"{len(extra)} extra links — fewer choices convert better; keep the ones visitors need")

    thumb = kit.get("thumbnail")
    if not thumb:
        rep.fail("thumbnail", "missing (square, 240x240 recommended, JPG/PNG/GIF; GIFs animate on hover)")
    else:
        check_image(rep, "thumbnail", thumb, "thumbnail", base)

    gallery = kit.get("gallery") or []
    produced = [g for g in gallery if (g.get("file") if isinstance(g, dict) else g)]
    planned_only = len(gallery) - len(produced)
    if len(gallery) < LIMITS["gallery_min"]:
        rep.fail("gallery", f"{len(gallery)} image(s); at least {LIMITS['gallery_min']} are required "
                            f"(3+ recommended, 1270x760)")
    elif len(produced) < LIMITS["gallery_min"]:
        rep.warn("gallery", f"{len(gallery)} planned but only {len(produced)} produced — the form needs at least "
                            f"{LIMITS['gallery_min']} real images before you can submit")
    elif len(gallery) < LIMITS["gallery_recommended"]:
        rep.warn("gallery", f"{len(gallery)} images; 3 or more are recommended")
    else:
        rep.ok("gallery", f"{len(gallery)} images" + (f" ({planned_only} still to produce)" if planned_only else ""))
    for i, g in enumerate(gallery, 1):
        path = g.get("file") if isinstance(g, dict) else g
        if path:
            check_image(rep, f"gallery[{i}]", path, "gallery", base)
        else:
            rep.warn(f"gallery[{i}]", f"planned, not produced yet: {g.get('title') if isinstance(g, dict) else g}")

    video = kit.get("video")
    if video and not VIDEO_HOSTS.search(video):
        rep.warn("video", f"{video} — the form takes YouTube or Loom links")
    elif video:
        rep.ok("video", video)
    else:
        rep.warn("video", "none — optional, but a short demo video helps people understand the product fast")
    demo = kit.get("interactive_demo")
    if demo:
        (rep.ok if DEMO_HOSTS.search(demo) else rep.warn)("interactive_demo", demo)

    makers = kit.get("makers") or []
    (rep.ok if makers else rep.warn)("makers", f"{makers}" if makers else "no makers listed — tag everyone who built it")

    fc = kit.get("first_comment", "")
    if not fc:
        rep.fail("first_comment", "missing — Product Hunt lists 'no maker comment' among the ways to not get featured")
    else:
        n = clen(fc)
        rep.ok("first_comment", f"{n} chars")
        if n > LIMITS["first_comment_visible"]:
            cut = unicodedata.normalize("NFC", fc)[:LIMITS["first_comment_visible"]]
            rep.warn("first_comment", f"only the first ~{LIMITS['first_comment_visible']} chars show before 'see more'; "
                                      f"visible part ends: …{cut[-120:]!r}")
        if UPVOTE.search(fc):
            rep.fail("first_comment", f"asks for upvotes ({UPVOTE.search(fc).group(0)!r}) — against Product Hunt's rules; "
                                      "ask for feedback, questions or a try instead")
        if not re.search(r"\?", fc):
            rep.warn("first_comment", "no question to the community — invite specific feedback")

    shout = kit.get("shoutouts") or []
    if len(shout) > LIMITS["shoutouts"]:
        rep.fail("shoutouts", f"{len(shout)} shoutouts; the launch allows {LIMITS['shoutouts']}: {shout}")
    elif shout:
        rep.ok("shoutouts", f"{len(shout)}/3: {shout}")

    pricing = kit.get("pricing")
    if not pricing:
        rep.warn("pricing", f"not set — choose one of {list(PRICING.values())}")
    elif pricing not in PRICING:
        rep.fail("pricing", f"{pricing!r} is not a form option; use one of {list(PRICING)}")
    else:
        rep.ok("pricing", PRICING[pricing])

    promo = kit.get("promo") or {}
    if promo:
        missing = [k for k in ("offer", "code", "expiration") if not promo.get(k)]
        if missing:
            rep.fail("promo", f"incomplete — missing {missing}; all fields are needed for a valid offer")
        else:
            rep.ok("promo", f"{promo['offer']} / code {promo['code']} / expires {promo['expiration']}")

    ld = kit.get("launch_date")
    if ld:
        try:
            dd = date.fromisoformat(ld)
            days = (dd - date.today()).days
            wd = dd.strftime("%A")
            msg = f"{ld} ({wd}), launches 12:01 AM Pacific Time"
            if days < 0:
                rep.warn("launch_date", msg + " — date is in the past")
            elif days < 7:
                rep.warn("launch_date", msg + f" — only {days} day(s) away: schedule it now; new accounts must wait a week to post")
            else:
                rep.ok("launch_date", msg + f", {days} days away")
        except ValueError:
            rep.fail("launch_date", f"{ld!r} is not YYYY-MM-DD")

    for key in ("social_posts", "outreach_messages", "community_messages", "email_announcement"):
        items = kit.get(key) or []
        if isinstance(items, str):
            items = [items]
        for i, txt in enumerate(items, 1):
            if UPVOTE.search(txt or ""):
                rep.fail(f"{key}[{i}]", f"asks for upvotes ({UPVOTE.search(txt).group(0)!r}) — ask people to check it out, "
                                        "try it and share feedback instead")
            elif REWARD.search(txt or ""):
                rep.fail(f"{key}[{i}]", "offers a reward tied to voting — not allowed")
    # Anything still marked TODO means the kit can't be pasted yet — say so plainly.
    todos = []
    def walk(v, path):
        if isinstance(v, str) and TODO.search(v):
            todos.append(path)
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                walk(v2, f"{path}.{k2}" if path else k2)
        elif isinstance(v, list):
            for i, v2 in enumerate(v, 1):
                walk(v2, f"{path}[{i}]")
    walk(kit, "")
    for t in todos:
        rep.warn(t, "contains a TODO placeholder — fill it in before pasting")
    rep.paste_ready = not rep.failed and not todos and planned_only == 0
    rep.blockers_to_paste = ([f"{len(todos)} field(s) with TODOs"] if todos else []) + \
        ([f"{planned_only} gallery image(s) not produced yet"] if planned_only else [])
    return rep


def render_markdown(kit: dict, rep: Report) -> str:
    def c(s):
        return f"`{clen(s or '')} chars`"
    L = [f"# Product Hunt launch kit — {kit.get('name', '')}", ""]
    if kit.get("launch_date"):
        L += [f"**Launch date:** {kit['launch_date']} · goes live 12:01 AM Pacific Time", ""]
    L += ["## Main info", "", f"**Name** ({c(kit.get('name'))} / 40)", "", f"> {kit.get('name', '')}", "",
          f"**Tagline** ({c(kit.get('tagline'))} / 60)", "", f"> {kit.get('tagline', '')}", ""]
    for i, alt in enumerate(kit.get("tagline_alternatives") or [], 1):
        L.append(f"- Alternative {i} ({c(alt)}): {alt}")
    if kit.get("tagline_alternatives"):
        L.append("")
    links = kit.get("links") or {}
    L += ["**Links**", "", f"- Website: {links.get('website', '')}"] + [f"- {u}" for u in links.get("additional") or []] + [""]
    L += [f"**Description** ({c(kit.get('description'))} / 500 — first ~260 visible)", "", f"> {kit.get('description', '')}", "",
          "**Launch tags** (up to 3): " + ", ".join(kit.get("launch_tags") or []), ""]
    L += ["## Media", "", f"**Thumbnail** (square, 240x240): {kit.get('thumbnail') or 'TODO'}", "", "**Gallery** (1270x760, 3+ images; the first one is the social preview):", ""]
    for i, g in enumerate(kit.get("gallery") or [], 1):
        if isinstance(g, dict):
            L.append(f"{i}. **{g.get('title', '')}** — {g.get('description', '')}" + (f" (`{g['file']}`)" if g.get("file") else " *(to produce)*"))
        else:
            L.append(f"{i}. `{g}`")
    L += ["", f"**Video:** {kit.get('video') or '—'}  ", f"**Interactive demo:** {kit.get('interactive_demo') or '—'}", ""]
    L += ["## People", "", "**Makers:** " + (", ".join(kit.get("makers") or []) or "TODO"), "",
          "**Shoutouts** (up to 3): " + (", ".join(kit.get("shoutouts") or []) or "—"), ""]
    L += [f"## First comment ({c(kit.get('first_comment'))}; first ~800 visible)", "", kit.get("first_comment", ""), ""]
    L += ["## Extras", "", f"**Pricing:** {PRICING.get(kit.get('pricing'), kit.get('pricing') or 'TODO')}"]
    promo = kit.get("promo") or {}
    if promo:
        L += ["", "| Offer | Code | Expiration |", "|---|---|---|",
              f"| {promo.get('offer', '')} | {promo.get('code', '')} | {promo.get('expiration', '')} |"]
    for key, title in (("social_posts", "Social posts"), ("outreach_messages", "Personal outreach messages"),
                       ("community_messages", "Community messages"), ("email_announcement", "Email announcement")):
        items = kit.get(key) or []
        if isinstance(items, str):
            items = [items]
        if items:
            L += ["", f"## {title}", ""]
            for i, t in enumerate(items, 1):
                L += [f"**{i}.**", "", t, ""]
    L += ["", "## Validation", "", "```", rep.text(), "```", ""]
    return "\n".join(L)


def utf8_console():
    """Print non-ASCII (✓, ≥, —, emoji from the input) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit", nargs="?", help="launch-kit JSON file")
    ap.add_argument("--markdown", help="also render the kit as Markdown to this path")
    ap.add_argument("--name", action="append", default=[])
    ap.add_argument("--tagline", action="append", default=[])
    ap.add_argument("--description", action="append", default=[])
    ap.add_argument("--first-comment", action="append", default=[])
    args = ap.parse_args()

    if args.kit:
        kp = Path(args.kit)
        kit = json.loads(kp.read_text(encoding="utf-8"))
        rep = check_kit(kit, kp.parent)
        print(rep.text())
        if args.markdown:
            Path(args.markdown).write_text(render_markdown(kit, rep), encoding="utf-8")
            print(f"\nRendered: {args.markdown}")
        sys.exit(1 if rep.failed else 0)

    rep = Report()
    for n in args.name:
        check_text_field(rep, "name", n, LIMITS["name"])
    for t in args.tagline:
        check_tagline(rep, t, args.name[0] if args.name else None)
    for d in args.description:
        check_text_field(rep, "description", d, LIMITS["description"])
        if clen(d) > LIMITS["description_visible"]:
            rep.warn("description", f"over {LIMITS['description_visible']} chars: the tail is hidden behind 'see more'")
    for fc in args.first_comment:
        n = clen(fc)
        (rep.warn if n > LIMITS["first_comment_visible"] else rep.ok)("first_comment", f"{n} chars (first ~800 visible)")
        if UPVOTE.search(fc):
            rep.fail("first_comment", "asks for upvotes")
    if not rep.rows:
        ap.print_help()
        sys.exit(2)
    print(rep.text())
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
