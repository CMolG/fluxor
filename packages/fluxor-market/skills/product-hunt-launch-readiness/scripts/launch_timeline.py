#!/usr/bin/env python3
"""Build a Product Hunt launch timeline in Pacific Time and the maker's own timezone.

A Product Hunt day runs from 12:01 AM to 11:59 PM Pacific Time, and PT switches
between PDT (UTC-7) and PST (UTC-8) on US dates that differ from Europe's, so
converting by hand is error-prone. This script does it with the tz database.

Usage:
    python3 launch_timeline.py --date 2026-10-06 --tz Europe/Madrid
    python3 launch_timeline.py --date 2026-10-06 --tz Asia/Kolkata --markdown
    python3 launch_timeline.py --next-days 14 --tz America/New_York   # list upcoming days with local go-live times
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None


def _nth_sunday(year, month, n):
    d = date(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def pacific():
    if ZoneInfo:
        try:
            return ZoneInfo("America/Los_Angeles")
        except Exception:
            pass
    return None


def to_utc_pacific(d: date, t: time) -> datetime:
    """Pacific local time -> aware UTC datetime (manual US DST rules if tzdata is missing)."""
    tz = pacific()
    if tz:
        return datetime.combine(d, t, tzinfo=tz).astimezone(timezone.utc)
    start = datetime.combine(_nth_sunday(d.year, 3, 2), time(2))
    end = datetime.combine(_nth_sunday(d.year, 11, 1), time(2))
    local = datetime.combine(d, t)
    offset = -7 if start <= local < end else -8
    return (local - timedelta(hours=offset)).replace(tzinfo=timezone.utc)


def fmt(dt_utc: datetime, tz):
    if tz is None:
        return None
    loc = dt_utc.astimezone(tz)
    return loc.strftime("%a %Y-%m-%d %H:%M %Z")


def pt_label(dt_utc: datetime):
    tz = pacific()
    if tz:
        return dt_utc.astimezone(tz).strftime("%a %Y-%m-%d %H:%M %Z")
    return dt_utc.strftime("%a %Y-%m-%d %H:%M UTC") + " (tzdata missing)"


def milestones(launch: date):
    D = launch
    return [
        (D - timedelta(days=30), time(9, 0), "T-30 days",
         "Every maker has a complete Product Hunt profile and is active in the community (comment on and support launches you "
         "genuinely like). Tell your own users/community a launch is coming; announce it in your Product Forum. Invite people "
         "who'd genuinely care to join Product Hunt and follow your Coming Soon page early, so they can take part in the "
         "conversation as real members (activity from brand-new accounts carries little weight and can be flagged as spam)."),
        (D - timedelta(days=14), time(9, 0), "T-14 days",
         "Listing assets final: name (≤40), tagline (≤60), description (≤500, core message in the first ~260), up to 3 launch "
         "tags, 240x240 thumbnail, 3+ gallery images at 1270x760, video/interactive demo, first comment, makers, up to 3 "
         "shoutouts, pricing, promo. Run the readiness audit and fix every blocker."),
        (D - timedelta(days=7), time(9, 0), "T-7 days",
         "Launch scheduled in advance (not scheduling ahead is one of Product Hunt's listed reasons launches don't get "
         "featured). The posting account must be at least a week old. Coming Soon page live so followers get notified."),
        (D - timedelta(days=3), time(9, 0), "T-3 days",
         "Traffic readiness: hosting/DB/API quotas and rate limits, spend caps on paid APIs, transactional-email daily limits, "
         "error monitoring, analytics that keeps ?ref=producthunt, support inbox/chat staffed. Draft social posts, emails and "
         "personal messages — asking people to check it out and share feedback, never to upvote."),
        (D - timedelta(days=1), time(12, 0), "T-1 day",
         "Final link check on the listing and site. Launch-day rota agreed so someone replies to comments at every hour of "
         "the Pacific day. Social posts scheduled. First comment ready to paste."),
        (D, time(0, 1), "GO LIVE (12:01 AM PT)",
         "Launch goes live for the full leaderboard day. Post the maker first comment immediately, then share the link with "
         "your users, community, social channels and personal contacts."),
        (D, time(0, 1), "Early hours",
         "For the first hours of the day Product Hunt hides upvote counts and shuffles the homepage order, so ignore rank and "
         "focus on conversations."),
        (D, time(12, 0), "All day",
         "Reply to every comment quickly and personally; watch the launch-day dashboard (add /launch-day to the post URL), "
         "uptime and error logs; share progress updates without asking for votes."),
        (D, time(23, 59), "Day ends (11:59 PM PT)", "The daily leaderboard closes; Product of the Day is decided."),
        (D + timedelta(days=1), time(9, 0), "T+1 day",
         "Thank supporters and commenters personally; follow up with new sign-ups; remind them of your Product Hunt offer."),
        (D + timedelta(days=7), time(9, 0), "T+7 days",
         "Keep answering late comments — Product of the Week and Month are still in play. Add the Product Hunt badge / "
         "award to your site. Ask happy users for Product Hunt reviews."),
        (D + timedelta(days=14), time(9, 0), "T+14 days",
         "Stop promoting the launch page; point links to your permanent Product Page. Post updates in your Product Forum; "
         "write the launch retrospective."),
        (D + timedelta(days=183), time(9, 0), "T+6 months",
         "Earliest normal relaunch for the same product (and it needs a significant update); sooner requires a relaunch request."),
    ]


def utf8_console():
    """Print non-ASCII (✓, ≥, —, emoji from the input) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="launch day (the Pacific-Time calendar date), YYYY-MM-DD")
    ap.add_argument("--tz", default="UTC", help="maker's IANA timezone, e.g. Europe/Madrid")
    ap.add_argument("--next-days", type=int, help="instead of a timeline, list the next N launch days")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    user_tz, note = None, None
    if args.tz.upper() in ("UTC", "ETC/UTC", "Z"):
        user_tz = timezone.utc  # needs no tz database
    elif ZoneInfo:
        try:
            user_tz = ZoneInfo(args.tz)
        except Exception:
            if pacific() is None:
                # zoneinfo found no tz database at all (Windows ships none), so no name would resolve.
                note = (f"No timezone database found, so {args.tz!r} can't be resolved: install the tzdata package "
                        "(pip install tzdata) and re-run. Showing Pacific (manual DST rules) and UTC only.")
            else:
                note = f"Unknown timezone {args.tz!r}; showing Pacific and UTC only."
    else:
        note = "zoneinfo unavailable; showing Pacific (manual DST rules) and UTC only."
    if note:
        print(note, file=sys.stderr if args.json else sys.stdout)  # keep --json output parseable

    if args.next_days:
        today = date.today()
        print(f"Upcoming Product Hunt days (go-live 12:01 AM PT) in {args.tz}:")
        for i in range(args.next_days):
            d = today + timedelta(days=i)
            go = to_utc_pacific(d, time(0, 1))
            kind = "weekend" if d.weekday() >= 5 else "weekday"
            print(f"  {d.isoformat()} {d.strftime('%a')} ({kind}): {fmt(go, user_tz) or go.strftime('%Y-%m-%d %H:%M UTC')}")
        return

    if not args.date:
        ap.error("--date is required (or use --next-days)")
    launch = date.fromisoformat(args.date)
    rows = []
    for d, t, label, what in milestones(launch):
        u = to_utc_pacific(d, t)
        rows.append({"milestone": label, "pacific": pt_label(u), "local": fmt(u, user_tz), "utc": u.strftime("%Y-%m-%d %H:%M UTC"),
                     "what": what})
    go = to_utc_pacific(launch, time(0, 1))
    end = to_utc_pacific(launch, time(23, 59))
    head = {"launch_day_pacific": launch.isoformat(), "weekday": launch.strftime("%A"),
            "weekend": launch.weekday() >= 5, "go_live_local": fmt(go, user_tz), "day_ends_local": fmt(end, user_tz),
            "go_live_utc": go.strftime("%Y-%m-%d %H:%M UTC"), "timezone": args.tz}
    if args.json:
        print(json.dumps({"summary": head, "timeline": rows}, indent=2))
        return
    if args.markdown:
        print(f"**Launch day:** {head['weekday']} {launch.isoformat()} (Pacific) — goes live **{head['go_live_local'] or head['go_live_utc']}**"
              f" and the day closes {head['day_ends_local'] or end.strftime('%Y-%m-%d %H:%M UTC')} ({args.tz}).\n")
        print(f"| When | Pacific | {args.tz} | What |")
        print("|---|---|---|---|")
        for r in rows:
            print(f"| {r['milestone']} | {r['pacific']} | {r['local'] or r['utc']} | {r['what']} |")
        return
    print(f"Launch day {head['weekday']} {launch.isoformat()} (Pacific){' — weekend: less competition, less traffic' if head['weekend'] else ''}")
    print(f"  goes live: {pt_label(go)}  =  {head['go_live_local'] or head['go_live_utc']}")
    print(f"  day ends:  {pt_label(end)}  =  {head['day_ends_local'] or end.strftime('%Y-%m-%d %H:%M UTC')}\n")
    for r in rows:
        print(f"{r['milestone']:<24} {r['pacific']:<26} {r['local'] or r['utc']:<28} {r['what']}")


if __name__ == "__main__":
    main()
