#!/usr/bin/env python3
"""Collect Product Hunt launch-readiness evidence from a code repository (stdlib only).

The script gathers facts with file:line evidence; it does not decide severity.
Map its output onto references/audit-checklist.md and judge each item yourself.

Usage:
    python3 audit_repo.py /path/to/repo --json evidence/repo.json

It never prints secrets: from env files it only reads variable NAMES, and only
from example/template env files (.env.example, .env.sample, .env.template).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imgmeta import image_info  # noqa: E402

SKIP_DIRS = {".git", "node_modules", ".next", ".nuxt", ".svelte-kit", ".output", "dist", "build", "out", ".turbo",
             ".vercel", ".netlify", "coverage", "vendor", "venv", ".venv", "env", "__pycache__", ".pytest_cache",
             ".mypy_cache", "target", "Pods", ".gradle", ".idea", ".vscode", "bower_components", ".cache",
             ".parcel-cache", "storybook-static", ".expo", ".dart_tool", "DerivedData", ".terraform", "tmp",
             "logs", ".yarn", ".pnpm-store", "site-packages", ".docusaurus", ".astro", "public/build",
             "product-hunt-launch"}
TEXT_EXT = {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".md",
            ".mdx", ".json", ".yml", ".yaml", ".toml", ".py", ".rb", ".erb", ".php", ".twig", ".liquid", ".hbs",
            ".njk", ".ejs", ".pug", ".go", ".rs", ".dart", ".swift", ".kt", ".java", ".xml", ".plist", ".txt",
            ".cfg", ".ini", ".webmanifest", ".gradle", ".kts", ".example", ".sample", ".template"}
UI_EXT = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx", ".erb", ".php", ".twig",
          ".liquid", ".hbs", ".njk", ".ejs", ".pug", ".js", ".ts", ".mjs", ".py", ".rb", ".dart", ".swift", ".kt"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".avif"}
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|e2e|cypress|playwright|fixtures?|mocks?|__mocks__|stories|"
                       r"\.storybook|examples?|samples?|docs/examples)(/|$)|\.(test|spec|stories)\.", re.I)
MAX_FILE_BYTES = 512_000
MAX_FILES = 25_000


def _rx(*parts):
    return [re.compile(p, re.I) for p in parts]

# Copy signals (same vocabulary as audit_url.py)
WAITLIST = _rx(r"\bwait[\s-]?list\b", r"\bcoming soon\b", r"\blaunching soon\b", r"\bearly access\b",
               r"\brequest (early )?access\b", r"\brequest an? invite\b", r"\bprivate beta\b", r"\bclosed beta\b",
               r"\binvite[\s-]only\b", r"\bnotify me\b", r"\bget notified\b", r"\bbe the first to (know|try|get)\b")
UPVOTE = _rx(r"\bup[\s-]?vot(e|es|ed|ing)\b", r"\bvote for us\b", r"\bgive us (a|your) vote\b")
# Superlatives and rank claims: the same patterns as check_launch_kit.py and audit_url.py.
SUPERLATIVES = (r"\b(?:best|smartest|greatest|fastest|easiest|simplest|finest|coolest|the\s+most\s+[\w-]+)\b.{0,40}\bever\b",
                r"\bever\s+(?:made|built|created|invented|designed|launched)\b",
                r"\b(?:world|industry|internet|planet)['’]?s\s+(?:first|best|most|leading|smartest|fastest|only|largest|"
                r"number[\s-]one|#1)(?!\w)", r"\b(?:smartest|greatest)\b",
                r"\bmost\s+(?:advanced|powerful|intelligent|innovative|revolutionary|amazing|incredible)\b",
                r"(?<![\w&#])#1(?!\w)", r"\bnumber[\s-]one\b", r"\bno\.\s?1\b")
HYPE = _rx(r"\brevolution(ary|i[sz]e|i[sz]ing)\b", r"\bgame[\s-]?chang(er|ing)\b", r"\bultimate\b", r"\bcutting[\s-]edge\b",
           r"\bnext[\s-]gen(eration)?\b", r"\bunparalleled\b", r"\bmind[\s-]?blowing\b", r"\bgroundbreaking\b",
           r"\bstate[\s-]of[\s-]the[\s-]art\b", *SUPERLATIVES)
PLACEHOLDER = _rx(r"\blorem ipsum\b", r"\bdolor sit amet\b", r"\byour (company|product|brand|app) name\b",
                  r"\bacme (inc|corp|co)\b", r"\binsert (text|copy|link) here\b",
                  r"create-next-app|bootstrapped with \W*create react app|getting started with create react app|"
                  r"this template should help get you started|#\s*react \+ (typescript \+ )?vite|edit src/app\.(t|j)sx|"
                  r"welcome to remix|astro starter kit|everything you need to build a svelte project|"
                  r"welcome to your new tanstack app|this is a \W*next\.js\W*(\([^)]*\))?\s*project")
CREDIT_CARD = _rx(r"\bcredit card (is )?required\b", r"\brequires? (a )?(credit )?card\b", r"\bcard required\b",
                  r"\benter (your )?(card|payment) (details|information|info)\b")
NO_CARD = _rx(r"\bno credit card\b", r"\bno card required\b", r"\bwithout a credit card\b")
FREE_OFFER = _rx(r"\bfree plan\b", r"\bfree tier\b", r"\bfree forever\b", r"\bfree trial\b", r"\btry (it )?(for )?free\b",
                 r"\bstart (for )?free\b", r"\bfree to (use|start|try)\b")
DEMO_ONLY = _rx(r"\bbook a (demo|call)\b", r"\brequest a demo\b", r"\bschedule a (demo|call)\b", r"\bcontact sales\b",
                r"\btalk to sales\b")
PRICE = re.compile(r"[$€£]\s?\d+(?:[.,]\d{2})?\s*(?:/|per\s)(?:mo|month|yr|year|user|seat)", re.I)
LOCALHOST = re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?[^\s'\"`)]*", re.I)
PH_REF = re.compile(r"producthunt\.com|product hunt|api\.producthunt\.com/widgets", re.I)
REF_HANDLING = re.compile(r"ref=producthunt|utm_source|searchParams\.get\(\s*['\"](ref|utm_source)['\"]|"
                          r"query\.(ref|utm_source)\b|params\[['\"](ref|utm_source)['\"]\]|getQueryParam", re.I)
HEAD_FILE_HINT = re.compile(r"<head[\s>]|<Head[\s>]|export\s+const\s+metadata\b|generateMetadata|useSeoMeta|useHead\(|"
                            r"svelte:head|DefaultSeo|NextSeo|export\s+(const|function)\s+meta\b|siteMetadata|"
                            r"<Helmet|og:title|og:image", re.I)
OG_IMAGE = re.compile(r"og:image|openGraph\s*[:=]\s*\{|opengraph-image|ogImage|og_image|og-image", re.I)
OG_TITLE = re.compile(r"og:title|openGraph\s*[:=]\s*\{[^}]*title", re.I | re.S)
TWITTER_CARD = re.compile(r"twitter:card|twitter\s*:\s*\{|summary_large_image", re.I)
META_DESC = re.compile(r"<meta\s+[^>]*name=[\"']description[\"']|^\s*description\s*:\s*['\"`]", re.I | re.M)
VIEWPORT = re.compile(r"name=[\"']viewport[\"']|export\s+const\s+viewport\b", re.I)
METADATA_BASE = re.compile(r"metadataBase\s*:\s*new\s+URL\(\s*([^)]+)\)", re.I)
ASSET_REF = re.compile(r"['\"`](/[\w./-]+\.(?:png|jpe?g|gif|webp|svg|ico))['\"`]", re.I)
SITE_URL_ENV = re.compile(r"^\s*([A-Z0-9_]*(SITE_URL|BASE_URL|APP_URL|PUBLIC_URL|NEXTAUTH_URL|VERCEL_URL|DOMAIN)[A-Z0-9_]*)\s*=\s*(.*)$")

KNOWN_DEPS = {
    "analytics": ["@vercel/analytics", "posthog-js", "posthog-node", "mixpanel-browser", "mixpanel", "@segment/analytics-next",
                  "analytics-node", "plausible-tracker", "next-plausible", "@amplitude/analytics-browser", "amplitude-js",
                  "react-ga4", "react-ga", "@next/third-parties", "vue-gtag", "@nuxtjs/google-analytics", "umami",
                  "@umami/node", "fathom-client", "@fathom/node", "@vercel/speed-insights", "@analytics/google-analytics",
                  "posthog", "mixpanel-python", "django-google-analytics-app", "ahoy_matey", "@june-so/analytics-next",
                  "@openpanel/nextjs", "@openpanel/web", "pirsch-sdk"],
    "error_monitoring": ["@sentry/nextjs", "@sentry/react", "@sentry/node", "@sentry/browser", "@sentry/vue",
                         "@sentry/sveltekit", "@sentry/astro", "@sentry/remix", "@sentry/react-native", "sentry-sdk",
                         "sentry-ruby", "sentry-rails", "@bugsnag/js", "@bugsnag/react", "logrocket", "@datadog/browser-rum",
                         "dd-trace", "rollbar", "@highlight-run/next", "highlight.run", "newrelic", "@sentry/electron",
                         "sentry_flutter", "raygun4js", "@axiomhq/js", "next-axiom", "@logtail/next"],
    "rate_limiting": ["@upstash/ratelimit", "express-rate-limit", "rate-limiter-flexible", "slowapi", "django-ratelimit",
                      "rack-attack", "flask-limiter", "@nestjs/throttler", "hono-rate-limiter", "limiter", "@arcjet/next",
                      "arcjet", "@unkey/ratelimit", "koa-ratelimit", "fastify-rate-limit", "@fastify/rate-limit"],
    "bot_protection": ["@hcaptcha/react-hcaptcha", "react-google-recaptcha", "react-google-recaptcha-v3",
                       "@marsidev/react-turnstile", "react-turnstile", "@cloudflare/turnstile", "django-recaptcha",
                       "botid", "@arcjet/next"],
    "ai_apis": ["openai", "@anthropic-ai/sdk", "anthropic", "@ai-sdk/openai", "@ai-sdk/anthropic", "ai", "langchain",
                "@langchain/openai", "@langchain/core", "replicate", "together-ai", "groq-sdk", "@mistralai/mistralai",
                "mistralai", "cohere-ai", "cohere", "@google/generative-ai", "@google/genai", "google-generativeai",
                "elevenlabs", "@elevenlabs/elevenlabs-js", "@fal-ai/client", "@fal-ai/serverless-client", "llamaindex",
                "@huggingface/inference", "litellm", "@openrouter/ai-sdk-provider"],
    "email": ["resend", "@sendgrid/mail", "postmark", "nodemailer", "mailgun.js", "mailgun-js", "@aws-sdk/client-ses",
              "@react-email/components", "loops", "@mailchimp/mailchimp_transactional", "brevo", "@getbrevo/brevo",
              "plunk", "sendgrid", "django-anymail", "letter_opener"],
    "auth": ["next-auth", "@auth/core", "@clerk/nextjs", "@clerk/clerk-react", "@supabase/auth-helpers-nextjs",
             "@supabase/ssr", "firebase", "lucia", "better-auth", "@auth0/nextjs-auth0", "passport", "@kinde-oss/kinde-auth-nextjs",
             "@workos-inc/authkit-nextjs", "devise", "django-allauth", "@stackframe/stack", "@privy-io/react-auth"],
    "payments": ["stripe", "@stripe/stripe-js", "@stripe/react-stripe-js", "@paddle/paddle-js", "@paddle/paddle-node-sdk",
                 "@lemonsqueezy/lemonsqueezy.js", "@polar-sh/sdk", "@polar-sh/nextjs", "chargebee", "pay", "dj-stripe",
                 "purchases-js", "react-native-purchases", "@revenuecat/purchases-js"],
    "database": ["@supabase/supabase-js", "prisma", "@prisma/client", "drizzle-orm", "mongoose", "mongodb", "pg", "mysql2",
                 "@neondatabase/serverless", "@planetscale/database", "@vercel/postgres", "firebase-admin", "convex",
                 "@libsql/client", "redis", "ioredis", "@upstash/redis", "sqlalchemy", "psycopg2", "psycopg"],
    "chat_support": ["@intercom/messenger-js-sdk", "react-use-intercom", "crisp-sdk-web", "@chatwoot/sdk", "react-live-chat-loader"],
    "product_hunt": ["react-product-hunt-badge", "producthunt-badge"],
}
AI_CALL = re.compile(r"\b(openai|anthropic|chat\.completions|messages\.create|generateText|streamText|generateObject|"
                     r"streamObject|ChatOpenAI|ChatAnthropic|replicate\.run|fal\.subscribe)\b")
AUTH_GUARD = re.compile(r"\b(auth\(\)|getServerSession|currentUser\(|getUser\(|requireAuth|withAuth|clerkClient|"
                        r"supabase\.auth\.getUser|getSession\(|isAuthenticated|login_required|authenticate_user!|"
                        r"ratelimit|rateLimit|rate_limit|limiter)", re.I)
PROMO_SUPPORT = re.compile(r"allow_promotion_codes|promotion_code|promotionCode|coupon|discount_code|promo[_ ]?code", re.I)
TRIAL = re.compile(r"trial_period_days|trial_end|trialPeriodDays|trial_days", re.I)
CARD_OPTIONAL = re.compile(r"payment_method_collection\s*[:=]\s*['\"]if_required['\"]", re.I)
DEV_CONFIG = re.compile(r"(playwright|cypress|vitest|jest|karma|webpack\.dev|docker-compose)[\w.-]*$|\.test\.", re.I)
SECRETY = re.compile(r"secret|credential|service[-_]?account|\.pem$|\.key$|\.p12$|\.keystore$|id_rsa", re.I)
STORE_LINK = re.compile(r"apps\.apple\.com/[^\s'\"`)]+|play\.google\.com/store/[^\s'\"`)]+|chromewebstore\.google\.com/[^\s'\"`)]+|"
                        r"chrome\.google\.com/webstore/[^\s'\"`)]+|addons\.mozilla\.org/[^\s'\"`)]+|"
                        r"marketplace\.visualstudio\.com/[^\s'\"`)]+|apps\.microsoft\.com/[^\s'\"`)]+", re.I)
CONTACT_LINK = re.compile(r"mailto:[^\s'\"`)>]+|discord\.(gg|com/invite)/\w+|['\"`]/(contact|support|help)\b", re.I)
SIGNING = re.compile(r"notariz|osxSign|osxNotarize|\bidentity\b|signingIdentity|certificateFile|certificateThumbprint|"
                     r"azureSignOptions|signtool|CSC_LINK|APPLE_TEAM_ID", re.I)


def rel(root, p):
    return str(Path(p).relative_to(root)).replace(os.sep, "/")


def read_text(p):
    try:
        if p.stat().st_size > MAX_FILE_BYTES:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def find_hits(patterns, text, relpath, limit, bucket):
    if len(bucket) >= limit:
        return
    lines = None
    for rx in patterns:
        for m in rx.finditer(text):
            if lines is None:
                lines = text.splitlines()
            ln = text.count("\n", 0, m.start()) + 1
            dup = next((h for h in bucket if h["file"] == relpath and h["line"] == ln), None)
            if dup:  # one entry per line; remember every phrase that matched on it
                if m.group(0).lower() not in dup["match"].lower():
                    dup["match"] += f" | {m.group(0)}"
                continue
            snippet = lines[ln - 1].strip() if ln - 1 < len(lines) else m.group(0)
            bucket.append({"file": relpath, "line": ln, "match": m.group(0), "text": snippet[:200]})
            if len(bucket) >= limit:
                return


def classify_image(name):
    n = name.lower()
    if re.search(r"(^|[-_./])(og|opengraph|open-graph|social|twitter|share|card)([-_.]|image|$)", n):
        return "social"
    if re.search(r"logo|icon|favicon|apple-touch|brand|mark|avatar|appicon|app-icon", n):
        return "logo_icon"
    if re.search(r"screen|shot|demo|preview|hero|gallery|feature|product|dashboard|mockup|ui", n):
        return "screenshot"
    return "other"


def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None


def audit(root: Path):
    r = {"root": str(root), "notes": []}
    files, n = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        rd = rel(root, dirpath) if Path(dirpath) != root else ""
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and f"{rd}/{d}".strip("/") not in SKIP_DIRS
                       and not d.startswith(".") or d in (".github", ".well-known")]
        for f in filenames:
            files.append(Path(dirpath) / f)
            n += 1
            if n >= MAX_FILES:
                break
        if n >= MAX_FILES:
            r["notes"].append(f"Stopped after {MAX_FILES} files; results are partial.")
            break
    relpaths = {rel(root, f): f for f in files}
    r["file_count"] = len(files)

    # ------------------------------------------------ manifests & dependencies
    deps, stack = {}, set()
    pkg_path = root / "package.json"
    pkg = load_json(pkg_path) if pkg_path.exists() else None
    for rp, fp in relpaths.items():
        if rp.endswith("package.json") and rp.count("/") <= 2:
            j = load_json(fp) or {}
            for sec in ("dependencies", "devDependencies", "peerDependencies"):
                for d, v in (j.get(sec) or {}).items():
                    deps.setdefault(d, {"version": v, "where": rp})
    for rp, fp in relpaths.items():
        base = rp.rsplit("/", 1)[-1]
        if re.match(r"requirements.*\.txt$", base) or base in ("Pipfile",):
            for line in (read_text(fp) or "").splitlines():
                m = re.match(r"\s*([A-Za-z0-9_.\-\[\]]+)", line)
                if m and not line.strip().startswith("#"):
                    deps.setdefault(m.group(1).split("[")[0].lower(), {"version": line.strip(), "where": rp})
        elif base == "pyproject.toml":
            txt = read_text(fp) or ""
            for m in re.finditer(r"^\s*['\"]?([A-Za-z0-9_.\-]+)\s*(\[[^\]]*\])?\s*[<>=~!]", txt, re.M):
                deps.setdefault(m.group(1).lower(), {"version": "", "where": rp})
            for m in re.finditer(r"['\"]([A-Za-z0-9_.\-]+)(\[[^\]]*\])?\s*[<>=~!]", txt):
                deps.setdefault(m.group(1).lower(), {"version": "", "where": rp})
        elif base == "Gemfile":
            for m in re.finditer(r"^\s*gem\s+['\"]([^'\"]+)", read_text(fp) or "", re.M):
                deps.setdefault(m.group(1), {"version": "", "where": rp})
        elif base == "composer.json":
            j = load_json(fp) or {}
            for d in list((j.get("require") or {}).keys()) + list((j.get("require-dev") or {}).keys()):
                deps.setdefault(d, {"version": "", "where": rp})
        elif base == "pubspec.yaml":
            stack.add("flutter")
    dep_names = set(deps)
    fw_map = {"next": "nextjs", "react": "react", "vue": "vue", "nuxt": "nuxt", "svelte": "svelte",
              "@sveltejs/kit": "sveltekit", "astro": "astro", "@remix-run/react": "remix", "react-router": "react-router",
              "gatsby": "gatsby", "@angular/core": "angular", "solid-js": "solid", "vite": "vite", "electron": "electron",
              "react-native": "react-native", "expo": "expo", "@capacitor/core": "capacitor", "@tauri-apps/api": "tauri",
              "express": "express", "fastify": "fastify", "hono": "hono", "@nestjs/core": "nestjs", "django": "django",
              "flask": "flask", "fastapi": "fastapi", "streamlit": "streamlit", "gradio": "gradio", "rails": "rails",
              "laravel/framework": "laravel", "wxt": "browser-extension", "plasmo": "browser-extension",
              "@crxjs/vite-plugin": "browser-extension", "vscode": "vscode-extension", "@types/vscode": "vscode-extension"}
    for d, s in fw_map.items():
        if d in dep_names:
            stack.add(s)
    for rp in relpaths:
        base = rp.rsplit("/", 1)[-1]
        if base in ("go.mod",):
            stack.add("go")
        elif base == "Cargo.toml":
            stack.add("rust")
        elif base.endswith(".xcodeproj") or base in ("Podfile", "Package.swift"):
            stack.add("ios/swift")
        elif base == "AndroidManifest.xml":
            stack.add("android")
        elif base == "tauri.conf.json":
            stack.add("tauri")
        elif base in ("app.json", "app.config.js", "app.config.ts") and "expo" in dep_names:
            stack.add("expo")
    ext_manifest = None
    for rp, fp in relpaths.items():
        if rp.rsplit("/", 1)[-1] == "manifest.json" and "public/" not in rp:
            j = load_json(fp)
            if isinstance(j, dict) and "manifest_version" in j:
                ext_manifest = {"file": rp, "name": j.get("name"), "version": j.get("version"),
                                "description": j.get("description"), "icons": j.get("icons")}
                stack.add("browser-extension")
    r["stack"] = sorted(stack)
    r["dependencies_detected"] = {cat: sorted(d for d in names if d in dep_names) for cat, names in KNOWN_DEPS.items()}

    # product type guess
    types = []
    if {"react-native", "expo", "flutter", "ios/swift", "android", "capacitor"} & stack:
        types.append("mobile-app")
    if {"electron", "tauri"} & stack:
        types.append("desktop-app")
    if {"browser-extension"} & stack:
        types.append("browser-extension")
    if "vscode-extension" in stack:
        types.append("ide-extension")
    if {"nextjs", "nuxt", "sveltekit", "astro", "remix", "gatsby", "angular", "vite", "vue", "react", "django", "flask",
        "fastapi", "rails", "laravel", "streamlit", "gradio", "express", "hono", "nestjs", "fastify"} & stack:
        types.append("web-app")
    if pkg and (pkg.get("bin") or (not pkg.get("private") and pkg.get("main") and "web-app" not in types)):
        types.append("cli-or-library")
    if (root / "pyproject.toml").exists() and re.search(r"\[project\.scripts\]|console_scripts",
                                                       read_text(root / "pyproject.toml") or ""):
        types.append("cli-or-library")
    if not types and any(rp.endswith((".html", ".htm")) for rp in relpaths):
        types.append("static-site")
    r["product_type_guess"] = types or ["unknown"]
    r["package"] = {k: pkg.get(k) for k in ("name", "version", "description", "homepage", "repository", "bin", "private",
                                           "license", "keywords")} if pkg else None
    r["package_scripts"] = sorted((pkg or {}).get("scripts", {}).keys())
    r["browser_extension_manifest"] = ext_manifest

    # ------------------------------------------------ docs, license, changelog, git
    readme = next((relpaths[p] for p in sorted(relpaths) if re.match(r"readme(\.\w+)?$", p, re.I)), None)
    if readme:
        txt = read_text(readme) or ""
        r["readme"] = {
            "file": rel(root, readme), "words": len(txt.split()),
            "headings": [h.strip() for h in re.findall(r"^#{1,3}\s+(.+)$", txt, re.M)][:25],
            "images": len(re.findall(r"!\[[^\]]*\]\([^)]+\)|<img\s", txt, re.I)),
            "gifs_or_videos": len(re.findall(r"\.(gif|mp4|webm|mov)\b|youtube\.com|youtu\.be|loom\.com", txt, re.I)),
            "has_install_or_quickstart": bool(re.search(r"^#{1,3}\s*(install|installation|quick ?start|getting started|usage|setup)",
                                                        txt, re.I | re.M)),
            "links": re.findall(r"https?://[^\s)>\]\"']+", txt)[:15],
            "is_framework_boilerplate": bool(PLACEHOLDER[-1].search(txt)),
            "first_lines": "\n".join(txt.strip().splitlines()[:8])[:600],
        }
    else:
        r["readme"] = None
    lic = next((p for p in sorted(relpaths) if re.match(r"(licen[cs]e|copying)(\.\w+)?$", p, re.I)), None)
    lic_type = None
    if lic:
        lt = (read_text(relpaths[lic]) or "")[:3000]
        for name, rx in (("MIT", r"\bMIT License\b|Permission is hereby granted, free of charge"),
                         ("Apache-2.0", r"Apache License"), ("GPL", r"GNU GENERAL PUBLIC LICENSE"),
                         ("AGPL", r"GNU AFFERO"), ("BSD", r"\bBSD\b|Redistribution and use in source"),
                         ("MPL-2.0", r"Mozilla Public License"), ("BSL/FSL (source-available)", r"Business Source License|Functional Source License"),
                         ("ISC", r"\bISC\b")):
            if re.search(rx, lt, re.I):
                lic_type = name
                break
    r["license"] = {"file": lic, "type": lic_type} if lic else None
    ch = next((p for p in sorted(relpaths) if re.match(r"(changelog|changes|history|releases)(\.\w+)?$", p, re.I)), None)
    r["changelog"] = None
    if ch:
        ct = read_text(relpaths[ch]) or ""
        r["changelog"] = {"file": ch, "latest_entries": [h.strip() for h in re.findall(r"^#{1,3}\s+(.+)$", ct, re.M)][:5]}
    r["community_files"] = sorted(p for p in relpaths if re.match(
        r"(\.github/)?(contributing|code_of_conduct|security|support)(\.\w+)?$", p, re.I))
    r["ci_workflows"] = sorted(p for p in relpaths if p.startswith(".github/workflows/"))[:10]
    r["git"] = None
    if (root / ".git").exists():
        r["git"] = {
            "last_commit": git(root, "log", "-1", "--format=%cI %s"),
            "commit_count": git(root, "rev-list", "--count", "HEAD"),
            "recent_tags": (git(root, "tag", "--sort=-creatordate", "--format=%(refname:short) %(creatordate:short)") or "").splitlines()[:6],
            "remote": git(root, "remote", "get-url", "origin"),
        }

    # ------------------------------------------------ images
    images = []
    for rp, fp in relpaths.items():
        if Path(rp).suffix.lower() in IMG_EXT and not TEST_PATH.search(rp):
            info = image_info(fp) or {}
            images.append({"file": rp, "kind": classify_image(rp), "format": info.get("format"),
                           "width": info.get("width"), "height": info.get("height"), "bytes": info.get("bytes"),
                           "animated": info.get("animated"), "vector": info.get("vector", False)})
            if len(images) >= 3000:
                break
    def area(i):
        return (i["width"] or 0) * (i["height"] or 0)
    logos = sorted([i for i in images if i["kind"] == "logo_icon"], key=lambda i: (i["vector"], area(i)), reverse=True)
    square_logos = [i for i in logos if i["vector"] or (i["width"] and i["height"] and abs(i["width"] - i["height"]) <= 2)]
    shots = sorted([i for i in images if i["kind"] == "screenshot" or
                    (i["width"] and i["height"] and i["width"] >= 1000 and 1.2 <= i["width"] / i["height"] <= 2.1
                     and i["kind"] != "social")], key=area, reverse=True)
    r["images"] = {
        "total": len(images),
        "logo_icon_candidates": logos[:10],
        "best_square_logo": square_logos[0] if square_logos else None,
        "thumbnail_source_ok": bool(square_logos and (square_logos[0]["vector"] or (square_logos[0]["width"] or 0) >= 240)),
        "social_images": [i for i in images if i["kind"] == "social"][:10],
        "screenshot_candidates": shots[:12],
        "gallery_ready_count": sum(1 for i in shots if (i["width"] or 0) >= 1270 and (i["height"] or 0) >= 760),
    }

    # ------------------------------------------------ text scanning
    hits = {k: [] for k in ("waitlist", "upvote_asks", "hype_in_headlines", "placeholders", "credit_card_required",
                            "no_card_required", "free_offer", "demo_or_sales_only_ctas", "prices", "localhost_urls",
                            "product_hunt_refs", "ref_or_utm_handling", "promo_code_support", "trial_config",
                            "card_optional_config", "store_links", "desktop_signing_config", "contact_links")}
    head_files, meta = [], {"og_image": [], "og_title": [], "twitter_card": [], "meta_description": [], "viewport": [],
                            "metadata_base": [], "missing_local_assets": []}
    ai_routes = []
    env_vars = []
    site_urls = []
    routes = {"pricing": [], "signup": [], "login": [], "privacy": [], "terms": [], "cookies": [], "docs": [],
              "changelog": [], "status": [], "contact": []}
    route_rx = {k: re.compile(v, re.I) for k, v in {
        "pricing": r"(^|/)(pricing|plans|prices)(/|\.|$)", "signup": r"(^|/)(sign-?up|register|join|get-started|onboarding)(/|\.|$)",
        "login": r"(^|/)(log-?in|sign-?in|auth)(/|\.|$)", "privacy": r"(^|/)(privacy|privacy-policy|datenschutz)(/|\.|$)",
        "terms": r"(^|/)(terms|tos|terms-of-service|terms-and-conditions|legal)(/|\.|$)", "cookies": r"(^|/)cookies?(-policy)?(/|\.|$)",
        "docs": r"(^|/)docs?(/|\.|$)", "changelog": r"(^|/)(changelog|releases|whats-new)(/|\.|$)",
        "status": r"(^|/)status(/|\.|$)", "contact": r"(^|/)(contact|support|help)(/|\.|$)"}.items()}
    for rp in relpaths:
        if TEST_PATH.search(rp):
            continue
        for k, rx in route_rx.items():
            if rx.search(rp) and Path(rp).suffix.lower() in UI_EXT | {".html", ".md", ".mdx"} and len(routes[k]) < 5:
                routes[k].append(rp)
    route_literal = re.compile(r"['\"`]/(pricing|privacy|terms|signup|sign-up|register|login|contact|docs|changelog)['\"`/]", re.I)
    route_literals = {}

    for rp, fp in relpaths.items():
        suffix = Path(rp).suffix.lower()
        base = rp.rsplit("/", 1)[-1]
        is_env_example = bool(re.match(r"\.env(\.[\w-]+)?\.(example|sample|template)$|\.env\.(example|sample|template)$", base))
        if (base.startswith(".env") and not is_env_example) or SECRETY.search(base):
            continue  # never read real env files or anything that looks like a credential
        if suffix not in TEXT_EXT and not is_env_example:
            continue
        if rp.endswith(("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "composer.lock", "Gemfile.lock", "poetry.lock")):
            continue
        txt = read_text(fp)
        if txt is None:
            continue
        test_file = bool(TEST_PATH.search(rp))
        if is_env_example:
            for line in txt.splitlines():
                m = re.match(r"\s*([A-Z][A-Z0-9_]+)\s*=", line)
                if m:
                    env_vars.append(m.group(1))
                    su = SITE_URL_ENV.match(line)
                    if su:
                        site_urls.append({"file": rp, "var": su.group(1), "example_value": su.group(3).strip()[:120]})
            continue
        if test_file:
            continue
        if re.search(r"electron-builder|forge\.config|tauri\.conf|^package\.json$", base):
            find_hits([SIGNING], txt, rp, 10, hits["desktop_signing_config"])
        ui = suffix in UI_EXT
        if ui or suffix in (".json", ".yml", ".yaml", ".toml", ".xml"):
            if suffix not in (".md", ".mdx") and not DEV_CONFIG.search(base):
                find_hits([LOCALHOST], txt, rp, 25, hits["localhost_urls"])
        if ui:
            find_hits(WAITLIST, txt, rp, 25, hits["waitlist"])
            find_hits(UPVOTE, txt, rp, 25, hits["upvote_asks"])
            find_hits(PLACEHOLDER, txt, rp, 25, hits["placeholders"])
            find_hits(CREDIT_CARD, txt, rp, 15, hits["credit_card_required"])
            find_hits(NO_CARD, txt, rp, 10, hits["no_card_required"])
            find_hits(FREE_OFFER, txt, rp, 15, hits["free_offer"])
            find_hits(DEMO_ONLY, txt, rp, 15, hits["demo_or_sales_only_ctas"])
            find_hits([PRICE], txt, rp, 15, hits["prices"])
            find_hits([PH_REF], txt, rp, 20, hits["product_hunt_refs"])
            find_hits([REF_HANDLING], txt, rp, 15, hits["ref_or_utm_handling"])
            find_hits([PROMO_SUPPORT], txt, rp, 10, hits["promo_code_support"])
            find_hits([TRIAL], txt, rp, 10, hits["trial_config"])
            find_hits([CARD_OPTIONAL], txt, rp, 5, hits["card_optional_config"])
            find_hits([STORE_LINK], txt, rp, 10, hits["store_links"])
            find_hits([CONTACT_LINK], txt, rp, 10, hits["contact_links"])
            for m in route_literal.finditer(txt):
                route_literals.setdefault(m.group(1).lower(), set()).add(rp)
            is_head = bool(HEAD_FILE_HINT.search(txt)) or base.lower() in ("index.html", "app.html", "base.html",
                                                                         "_document.tsx", "_document.jsx", "layout.tsx",
                                                                         "layout.jsx", "application.html.erb")
            heroish = re.search(r"(^|/)(page|index|home|landing|hero|header|app|layout|root)\.[\w]+$|hero|landing", rp, re.I)
            if is_head or heroish:
                find_hits(HYPE, txt, rp, 20, hits["hype_in_headlines"])
            if is_head:
                head_files.append(rp)
                for key, rx in (("og_image", OG_IMAGE), ("og_title", OG_TITLE), ("twitter_card", TWITTER_CARD),
                                ("meta_description", META_DESC), ("viewport", VIEWPORT)):
                    find_hits([rx], txt, rp, 10, meta[key])
                for m in METADATA_BASE.finditer(txt):
                    ln = txt.count("\n", 0, m.start()) + 1
                    meta["metadata_base"].append({"file": rp, "line": ln, "value": m.group(1).strip()[:160]})
                for m in ASSET_REF.finditer(txt):
                    ref = m.group(1)
                    cands = [root / "public" / ref.lstrip("/"), root / "static" / ref.lstrip("/"),
                             root / ref.lstrip("/"), fp.parent / ref.lstrip("/"),
                             root / "app" / ref.lstrip("/"), root / "src" / "assets" / ref.lstrip("/")]
                    if not any(c.exists() for c in cands):
                        ln = txt.count("\n", 0, m.start()) + 1
                        meta["missing_local_assets"].append({"file": rp, "line": ln, "ref": ref})
            if AI_CALL.search(txt) and re.search(r"(^|/)(api|routes?|server|functions|actions?)/|route\.(t|j)s$|\+server\.|"
                                                 r"actions?\.(t|j)s$|views?\.py$|controllers?/", rp, re.I):
                ai_routes.append({"file": rp, "has_auth_or_rate_limit_guard": bool(AUTH_GUARD.search(txt))})
    # Next.js / framework file conventions for metadata images
    conv = {"opengraph_image_files": [p for p in relpaths if re.search(r"(^|/)opengraph-image\.\w+$", p)],
            "twitter_image_files": [p for p in relpaths if re.search(r"(^|/)twitter-image\.\w+$", p)],
            "icon_files": [p for p in relpaths if re.search(r"(^|/)(icon|apple-icon|favicon)(\d*)\.\w+$|apple-touch-icon", p, re.I)
                           and not TEST_PATH.search(p)][:12],
            "web_manifest_files": [p for p in relpaths if re.search(r"(site\.webmanifest|manifest\.webmanifest|/manifest\.json)$", p)
                                   and "node_modules" not in p][:5],
            "robots": [p for p in relpaths if re.search(r"(^|/)robots\.(txt|ts|js)$", p)][:3],
            "sitemap": [p for p in relpaths if re.search(r"(^|/)sitemap(\.xml|\.ts|\.js|-index\.xml)$", p)][:3]}
    r["metadata"] = {"head_files": head_files[:20], **meta, **conv,
                     "viewport_framework_default": bool({"nextjs", "nuxt"} & stack),
                     # Next.js fills twitter:card/title/description/image from openGraph when `twitter` is unset.
                     "twitter_from_opengraph_default": "nextjs" in stack and bool(meta["og_image"] or conv["opengraph_image_files"])}
    r["copy_signals"] = hits
    r["routes"] = routes
    r["route_links_in_code"] = {k: sorted(v)[:5] for k, v in route_literals.items()}
    r["ai_endpoints"] = ai_routes[:20]
    r["env_example_vars"] = sorted(set(env_vars))[:80]
    r["site_url_hints"] = site_urls[:10]

    # deployment / hosting hints
    host_files = {"vercel": ["vercel.json"], "netlify": ["netlify.toml"], "cloudflare": ["wrangler.toml", "wrangler.json", "wrangler.jsonc"],
                  "fly.io": ["fly.toml"], "render": ["render.yaml"], "railway": ["railway.json", "railway.toml"],
                  "heroku": ["Procfile", "app.json"], "docker": ["Dockerfile", "docker-compose.yml", "compose.yaml"],
                  "firebase": ["firebase.json"], "aws/sst": ["sst.config.ts", "serverless.yml", "amplify.yml"],
                  "github-pages": ["CNAME"]}
    r["hosting_hints"] = sorted({h for h, names in host_files.items() for n in names if n in relpaths})
    cname = root / "CNAME"
    homepage_candidates = []
    if cname.exists():
        homepage_candidates.append("https://" + (read_text(cname) or "").strip())
    if pkg and pkg.get("homepage"):
        homepage_candidates.append(pkg["homepage"])
    for mb in meta["metadata_base"]:
        v = re.sub(r"^['\"`]|['\"`]$", "", mb["value"])
        if v.startswith("http"):
            homepage_candidates.append(v)
    for s in site_urls:
        v = s["example_value"].strip("'\"")
        if v.startswith("http"):
            homepage_candidates.append(v)
    if r.get("readme"):
        homepage_candidates += [u for u in r["readme"]["links"] if not re.search(
            r"github\.com|shields\.io|badge|npmjs|vercel\.com|nextjs\.org|react\.dev|vitejs\.dev|tailwindcss\.com|"
            r"fonts\.google|developer\.mozilla|localhost|img\.|\.(png|svg|gif)", u)][:3]
    r["homepage_candidates"] = [u for u in dict.fromkeys(homepage_candidates) if not LOCALHOST.match(u)][:8]
    return r


def summarize(r):
    ok, bad, warn = "✓", "✗", "!"
    L = [f"Repo audit: {r['root']}  ({r['file_count']} files)",
         f"  stack: {', '.join(r['stack']) or 'unknown'}   product type guess: {', '.join(r['product_type_guess'])}"]
    if r.get("homepage_candidates"):
        L.append(f"  production URL candidates (audit these with audit_url.py): {r['homepage_candidates']}")
    rd = r.get("readme")
    L.append(f"{ok if rd else bad} README" + (f": {rd['words']} words, {rd['images']} images, install/quickstart: "
                                                f"{rd['has_install_or_quickstart']}" + (" — framework boilerplate!" if rd['is_framework_boilerplate'] else "")
                                                if rd else ""))
    L.append(f"{ok if r.get('license') else warn} LICENSE" + (f": {r['license']['type']}" if r.get("license") else " (fine for closed-source; required for open source)"))
    im = r["images"]
    b = im["best_square_logo"]
    L.append(f"{ok if im['thumbnail_source_ok'] else bad} square logo for 240x240 thumbnail: "
             + (f"{b['file']} ({b['width']}x{b['height']}{', vector' if b['vector'] else ''})" if b else "none found"))
    L.append(f"{ok if im['gallery_ready_count'] >= 2 else bad} gallery-ready screenshots (>=1270x760): {im['gallery_ready_count']}"
             f"  (screenshot-like images: {len(im['screenshot_candidates'])})")
    md = r["metadata"]
    L.append(f"  head/metadata files: {md['head_files'][:6]}")
    for key, label in (("og_image", "og:image / openGraph images"), ("twitter_card", "twitter card"),
                       ("meta_description", "meta description"), ("viewport", "viewport")):
        present = bool(md[key]) or (key == "og_image" and md["opengraph_image_files"]) or \
            (key == "twitter_card" and (md["twitter_image_files"] or md["twitter_from_opengraph_default"])) or \
            (key == "viewport" and md["viewport_framework_default"])
        note = ""
        if key == "twitter_card" and not md[key] and md["twitter_from_opengraph_default"]:
            note = " (Next.js derives it from openGraph)"
        elif key == "viewport" and not md[key] and md["viewport_framework_default"]:
            note = " (framework default)"
        L.append(f"{ok if present else bad} {label}{note}")
    for mb in md["metadata_base"]:
        flag = bad if "localhost" in mb["value"] or "127.0.0.1" in mb["value"] else ok
        L.append(f"{flag} metadataBase = {mb['value']}  ({mb['file']}:{mb['line']})")
    for a in md["missing_local_assets"][:8]:
        L.append(f"{bad} referenced asset missing: {a['ref']}  ({a['file']}:{a['line']})")
    L.append(f"{ok if md['icon_files'] else warn} icon files: {md['icon_files'][:6]}")
    cs = r["copy_signals"]
    for key, label in (("upvote_asks", "asks for upvotes (Product Hunt rule violation)"), ("waitlist", "waitlist / coming-soon copy"),
                       ("localhost_urls", "hard-coded localhost URLs"), ("placeholders", "placeholder / boilerplate copy"),
                       ("hype_in_headlines", "hype words in headline/hero files"), ("credit_card_required", "credit card required copy"),
                       ("demo_or_sales_only_ctas", "demo/sales-only CTAs")):
        if cs[key]:
            L.append(f"{warn} {label}: " + "; ".join(f"{h['file']}:{h['line']} {h['text'][:90]!r}" for h in cs[key][:4]))
    L.append(f"  free-offer mentions: {len(cs['free_offer'])}, price mentions: {len(cs['prices'])}, trial config: {len(cs['trial_config'])},"
             f" card-optional config: {len(cs['card_optional_config'])}, promo-code support: {len(cs['promo_code_support'])}")
    rt = r["routes"]
    for k in ("pricing", "signup", "privacy", "terms", "contact"):
        found = rt[k] or r["route_links_in_code"].get(k) or (k == "signup" and r["route_links_in_code"].get("sign-up")) or \
            (k == "contact" and cs["contact_links"])
        L.append(f"{ok if found else warn} {k} page: {(rt[k] or ['(link only)'] if found else ['not found'])[:3]}")
    dd = r["dependencies_detected"]
    for cat in ("analytics", "error_monitoring", "rate_limiting", "bot_protection", "ai_apis", "email", "auth", "payments", "database"):
        L.append(f"{ok if dd[cat] else warn if cat in ('analytics', 'error_monitoring') else ' '} {cat}: {', '.join(dd[cat]) or 'none'}")
    for e in r["ai_endpoints"][:8]:
        L.append(f"{ok if e['has_auth_or_rate_limit_guard'] else bad} AI endpoint {e['file']} — auth/rate-limit guard: {e['has_auth_or_rate_limit_guard']}")
    L.append(f"{ok if cs['ref_or_utm_handling'] else warn} ref/UTM attribution handling in code: {len(cs['ref_or_utm_handling'])} hits")
    L.append(f"  Product Hunt references in code: {len(cs['product_hunt_refs'])}")
    L.append(f"  hosting hints: {r['hosting_hints'] or 'none'}   CI workflows: {len(r['ci_workflows'])}   scripts: {r['package_scripts'][:8]}")
    if r.get("git"):
        L.append(f"  git: last commit {r['git']['last_commit']}, {r['git']['commit_count']} commits, tags: {r['git']['recent_tags'][:3]}")
    for n in r["notes"]:
        L.append(f"{warn} {n}")
    return "\n".join(L)


def utf8_console():
    """Print non-ASCII (✓, ≥, —, emoji from the input) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", help="write the full evidence JSON here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    root = Path(args.path).resolve()
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")
    r = audit(root)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    if not args.quiet:
        print(summarize(r))
        if args.json:
            print(f"\nFull evidence: {args.json}")


if __name__ == "__main__":
    main()
