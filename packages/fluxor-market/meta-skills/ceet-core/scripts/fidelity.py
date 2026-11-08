#!/usr/bin/env python3
"""Measure how well a pack decides like its person (references/fidelity.md).

  fidelity.py add --pack-id <id> --situation "..." --option "..." --option "..." --choice 1 [--domain ...]
  fidelity.py retest-sheet --pack-id <id> [--n 10] [--seed 7]    the blind redo, two weeks later
  fidelity.py retest --pack-id <id> --answer H3=1 --answer H7=0 ...
  fidelity.py prompts --pack-id <id> --pack <pack> --out <dir> [--arm base|persona|context|raw|pack]...
  fidelity.py score --pack-id <id> --responses <dir> [--baseline raw] [--defects labels.json]
  fidelity.py pairwise-sheet --a <dir> --b <dir> --out <sheet.md> [--seed 7]
  fidelity.py pairwise-score --key <sheet.key.json> --pick H1=A --pick H2=B ...

The held-out set lives in `.harness/fidelity/<pack-id>/heldout.json` (schemas/heldout.schema.json),
outside the pack, so nothing that loads the pack sees it. Agreement is the share of held-out items
where an arm picks the option the person picked; the ceiling is the person's agreement with
themselves on the blind retest; the reported fidelity is agreement divided by that ceiling. Arms
are compared on the same items with a paired bootstrap that resamples items (the clusters), so
several samples of one item never count as independent evidence.

Standard library only (Python 3.9+). It never calls a model: `prompts` writes one prompt per item
and arm, whoever runs the evaluation collects the replies as `<dir>/<arm>/<item>[.<sample>].txt`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ceet_common as cc  # noqa: E402
import examples as ex  # noqa: E402

ARMS = ["base", "persona", "context", "raw", "pack"]
BOOTSTRAP = 2000


def store_path(args) -> Path:
    return cc.fidelity_dir(cc.project_root(args.project), args.pack_id) / "heldout.json"


def load_store(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"error: {path} does not exist; add held-out decisions first (`fidelity.py add`)")
    data = cc.read_json(path)
    errors = cc.validate_schema(data, "heldout.schema.json")
    if errors:
        raise SystemExit("error: heldout.json is invalid:\n  " + "\n  ".join(errors[:10]))
    return data


def save_store(path: Path, data: dict) -> None:
    errors = cc.validate_schema(data, "heldout.schema.json")
    if errors:
        raise SystemExit("error: heldout.json would be invalid:\n  " + "\n  ".join(errors[:10]))
    cc.write_json(path, data)
    ignore = path.parent / ".gitignore"
    if not ignore.is_file():
        cc.write_text(ignore, "# Held-out decisions are personal data and must stay unseen by synthesis.\n*\n")


# ─── Collecting ─────────────────────────────────────────────────────────────────────────────────

def cmd_add(args) -> int:
    path = store_path(args)
    data = cc.read_json(path) if path.is_file() else {"schemaVersion": "1.0.0", "packId": args.pack_id,
                                                      "createdAt": dt.date.today().isoformat(), "items": []}
    if data.get("retest"):
        print("error: the retest has been recorded; adding items now would bias the ceiling", file=sys.stderr)
        return 2
    if not 0 <= args.choice < len(args.option):
        print("error: --choice is the index of one of the --option values", file=sys.stderr)
        return 2
    item = {"id": f"H{len(data['items']) + 1}", "situation": args.situation, "options": args.option,
            "choice": args.choice}
    for key in ("domain", "rationale", "when", "defect"):
        if getattr(args, key):
            item[key] = getattr(args, key)
    data["items"].append(item)
    save_store(path, data)
    print(f"added {item['id']} ({len(data['items'])} held-out decisions; aim for 20–40)")
    return 0


def cmd_retest_sheet(args) -> int:
    data = load_store(store_path(args))
    rng = random.Random(args.seed)
    items = rng.sample(data["items"], min(args.n, len(data["items"])))
    lines = ["# Retest", "", "Choose one option for each situation. Answer from how you would decide today; do not look",
             "up what you chose before.", ""]
    for item in items:
        lines += [f"## {item['id']}", "", item["situation"], ""]
        lines += [f"{i}. {option}" for i, option in enumerate(item["options"])]
        lines += ["", "Your choice: ", ""]
    print("\n".join(lines))
    return 0


def cmd_retest(args) -> int:
    path = store_path(args)
    data = load_store(path)
    ids = {item["id"]: item for item in data["items"]}
    answers = {}
    for pair in args.answer:
        key, _, value = pair.partition("=")
        if key not in ids or not value.isdigit() or int(value) >= len(ids[key]["options"]):
            print(f"error: {pair!r} is not <item>=<option index>", file=sys.stderr)
            return 2
        answers[key] = int(value)
    data["retest"] = {"date": dt.date.today().isoformat(), "answers": answers}
    save_store(path, data)
    print(f"recorded the retest of {len(answers)} item(s); ceiling = {ceiling(data):.2f}")
    return 0


def ceiling(data: dict) -> float | None:
    retest = data.get("retest", {}).get("answers", {})
    if not retest:
        return None
    by_id = {item["id"]: item for item in data["items"]}
    same = [1.0 if by_id[k]["choice"] == v else 0.0 for k, v in retest.items() if k in by_id]
    return sum(same) / len(same) if same else None


# ─── Prompts per arm ────────────────────────────────────────────────────────────────────────────

def question_block(item: dict) -> str:
    options = "\n".join(f"{i}. {option}" for i, option in enumerate(item["options"]))
    return (f"Situation:\n{item['situation']}\n\nOptions:\n{options}\n\n"
            "Reply with the number of the option you choose on the first line, then one sentence on why.")


def arm_context(arm: str, pack: Path, profile: dict, role: cc.Role, item: dict) -> str:
    title = role.title
    if arm == "base":
        return ""
    if arm == "persona":
        return f"You are a senior {title}."
    answers = cc.read_json(pack / "private" / "answers.json").get("answers", {}) if (pack / "private" / "answers.json").is_file() else {}
    if arm == "context":
        first = role.form["modules"][0]["sections"][0]
        stated = "\n".join(f"{q['prompt']}\n{answers[q['id']]['text']}" for q in first["questions"] if q["id"] in answers)
        return f"You are a senior {title}. About the person you are deciding as:\n{stated}"
    decisions = ex.load(pack) if (pack / "examples" / "decisions.json").is_file() else []
    if arm == "raw":
        raw = "\n\n".join(f"{qid}: {a['text']}" for qid, a in sorted(answers.items(), key=lambda kv: int(kv[0][1:])))
        shown = "\n".join(ex.render(d) for d in decisions[:10])
        return (f"You are deciding as {profile['name']}, a {title}. Their interview answers, verbatim:\n\n{raw}\n\n"
                f"Some of their real decisions:\n{shown}")
    if arm == "pack":
        core = (pack / "core.md").read_text(encoding="utf-8")
        closest = "\n".join(ex.render(d) for _, d in ex.rank(decisions, item["situation"], 5))
        return core + ("\n\nDecisions they made in similar cases:\n" + closest if closest else "")
    raise SystemExit(f"error: unknown arm {arm!r}")


def leaks(items: list[dict], decisions: list[dict]) -> list[str]:
    """Held-out situations that look like a decision the pack already holds (word overlap)."""
    found = []
    for item in items:
        words = set(ex.tokens(item["situation"]))
        for d in decisions:
            other = set(ex.tokens(d["situation"]))
            if words and other and len(words & other) / len(words | other) > 0.5:
                found.append(f"{item['id']} resembles {d['id']}")
    return found


def cmd_prompts(args) -> int:
    data = load_store(store_path(args))
    pack = Path(args.pack).resolve()
    profile = cc.read_json(pack / "cognitive-profile.json")
    role = cc.Role(cc.role_dir(profile["role"], args.role_dir))
    decisions = ex.load(pack) if (pack / "examples" / "decisions.json").is_file() else []
    for warning in leaks(data["items"], decisions):
        print(f"warning: possible leak: {warning}; drop the item or the decision")
    out = Path(args.out)
    arms = args.arm or ARMS
    for arm in arms:
        for item in data["items"]:
            context = arm_context(arm, pack, profile, role, item)
            text = (context + "\n\n" if context else "") + question_block(item)
            cc.write_text(out / arm / f"{item['id']}.prompt.md", text + "\n")
    print(f"wrote {len(arms) * len(data['items'])} prompts under {out}; save replies as <arm>/<item>.txt "
          "(or <item>.<n>.txt for several samples)")
    return 0


# ─── Scoring ────────────────────────────────────────────────────────────────────────────────────

def parse_choice(text: str) -> int | None:
    match = re.search(r"\d+", text.strip().splitlines()[0] if text.strip() else "")
    return int(match.group(0)) if match else None


def collect(responses: Path, arm: str, items: list[dict]) -> dict[str, list[float]]:
    """item id → agreement of each sample (1 or 0)."""
    by_item: dict[str, list[float]] = {}
    for item in items:
        for path in sorted((responses / arm).glob(f"{item['id']}.txt")) + sorted((responses / arm).glob(f"{item['id']}.*.txt")):
            choice = parse_choice(path.read_text(encoding="utf-8"))
            by_item.setdefault(item["id"], []).append(1.0 if choice == item["choice"] else 0.0)
    return by_item


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def bootstrap_diff(a: dict[str, list[float]], b: dict[str, list[float]], seed: int) -> tuple[float, float, float, int]:
    """Paired, item-clustered bootstrap of mean agreement a − b over the items both arms answered."""
    shared = sorted(set(a) & set(b))
    if not shared:
        return float("nan"), float("nan"), float("nan"), 0
    per_item = [mean(a[i]) - mean(b[i]) for i in shared]
    rng = random.Random(seed)
    draws = sorted(mean([per_item[rng.randrange(len(shared))] for _ in shared]) for _ in range(BOOTSTRAP))
    return mean(per_item), draws[int(0.025 * BOOTSTRAP)], draws[int(0.975 * BOOTSTRAP) - 1], len(shared)


def cmd_score(args) -> int:
    path = store_path(args)
    data = load_store(path)
    items = [i for i in data["items"] if "defect" not in i]
    responses = Path(args.responses)
    top = ceiling(data)
    arms = [a for a in ARMS if (responses / a).is_dir()]
    per_arm = {arm: collect(responses, arm, items) for arm in arms}
    report = {"packId": args.pack_id, "date": dt.date.today().isoformat(), "items": len(items),
              "ceiling": top, "arms": {}, "comparisons": [], "defects": {}}
    for arm, by_item in per_arm.items():
        agreement = mean([mean(v) for v in by_item.values()]) if by_item else float("nan")
        report["arms"][arm] = {"itemsAnswered": len(by_item), "agreement": round(agreement, 4),
                               "fidelity": round(agreement / top, 4) if top else None}
    baseline = args.baseline if args.baseline in per_arm else None
    for arm in arms:
        if baseline and arm != baseline:
            diff, low, high, n = bootstrap_diff(per_arm[arm], per_arm[baseline], args.seed)
            report["comparisons"].append({"arm": arm, "versus": baseline, "items": n, "difference": round(diff, 4),
                                          "ci95": [round(low, 4), round(high, 4)]})
    if args.defects:
        labels = cc.read_json(Path(args.defects))
        for arm, found in labels.items():
            hits = [1.0 if v else 0.0 for v in found.values()]
            report["defects"][arm] = {"items": len(hits), "recall": round(mean(hits), 4) if hits else None}
    out = path.parent / f"report-{report['date']}.json"
    cc.write_json(out, report)
    print(f"ceiling (person vs themselves): {top if top is not None else 'not measured: run the retest'}")
    for arm, r in report["arms"].items():
        print(f"{arm:8} agreement {r['agreement']:.2f}" + (f", fidelity {r['fidelity']:.2f}" if r["fidelity"] else "")
              + f" over {r['itemsAnswered']} item(s)")
    for c in report["comparisons"]:
        verdict = "better" if c["ci95"][0] > 0 else "worse" if c["ci95"][1] < 0 else "not distinguishable"
        print(f"{c['arm']} − {c['versus']}: {c['difference']:+.2f} (95% CI {c['ci95'][0]:+.2f} … {c['ci95'][1]:+.2f}, "
              f"{c['items']} items): {verdict}")
    if baseline == "raw" and "pack" in report["arms"]:
        pack_vs_raw = next((c for c in report["comparisons"] if c["arm"] == "pack"), None)
        if pack_vs_raw and pack_vs_raw["ci95"][0] <= 0:
            print("the pack does not beat the raw answers plus examples: synthesis adds nothing measurable yet")
    print(f"wrote {out}")
    return 0


# ─── Blind pairwise judgment ────────────────────────────────────────────────────────────────────

def cmd_pairwise_sheet(args) -> int:
    a_dir, b_dir = Path(args.a), Path(args.b)
    rng = random.Random(args.seed)
    key, lines = {}, ["# Which reply is more like you?", "",
                      "For each case, pick A or B: the reply you would be likelier to have written.", ""]
    for a_path in sorted(a_dir.glob("*.txt")):
        b_path = b_dir / a_path.name
        if not b_path.is_file():
            continue
        item = a_path.name.split(".")[0]
        flip = rng.random() < 0.5
        first, second = (b_path, a_path) if flip else (a_path, b_path)
        key[item] = {"A": str(first), "B": str(second), "aIs": "b" if flip else "a"}
        lines += [f"## {item}", "", "**A**", "", first.read_text(encoding="utf-8").strip(), "",
                  "**B**", "", second.read_text(encoding="utf-8").strip(), "", "Your pick (A/B): ", ""]
    cc.write_text(Path(args.out), "\n".join(lines))
    cc.write_json(Path(args.out).with_suffix(".key.json"), {"a": str(a_dir), "b": str(b_dir), "items": key})
    print(f"wrote {args.out} ({len(key)} pairs) and its key; keep the key away from the person")
    return 0


def cmd_pairwise_score(args) -> int:
    key = cc.read_json(Path(args.key))
    wins = []
    for pair in args.pick:
        item, _, letter = pair.partition("=")
        entry = key["items"].get(item)
        if entry is None or letter.upper() not in ("A", "B"):
            print(f"error: {pair!r} is not <item>=A|B", file=sys.stderr)
            return 2
        picked_a_side = (letter.upper() == "A") == (entry["aIs"] == "a")
        wins.append(1.0 if picked_a_side else 0.0)
    rng = random.Random(args.seed)
    draws = sorted(mean([wins[rng.randrange(len(wins))] for _ in wins]) for _ in range(BOOTSTRAP)) if wins else []
    rate = mean(wins) if wins else float("nan")
    print(f"{key['a']} preferred over {key['b']} in {rate:.2f} of {len(wins)} pairs"
          + (f" (95% CI {draws[int(0.025 * BOOTSTRAP)]:.2f} … {draws[int(0.975 * BOOTSTRAP) - 1]:.2f})" if draws else ""))
    return 0


def main(argv=None) -> int:
    cc.configure_output()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", help="project root (default: $CLAUDE_PROJECT_DIR, git, cwd)")
    parser.add_argument("--role-dir", help="the role's folder, when it is not installed next to ceet-core")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("add")
    p.add_argument("--pack-id", required=True)
    p.add_argument("--situation", required=True)
    p.add_argument("--option", action="append", required=True)
    p.add_argument("--choice", type=int, required=True)
    for key in ("domain", "rationale", "when", "defect"):
        p.add_argument(f"--{key}")
    p.set_defaults(func=cmd_add)
    p = sub.add_parser("retest-sheet")
    p.add_argument("--pack-id", required=True)
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(func=cmd_retest_sheet)
    p = sub.add_parser("retest")
    p.add_argument("--pack-id", required=True)
    p.add_argument("--answer", action="append", required=True)
    p.set_defaults(func=cmd_retest)
    p = sub.add_parser("prompts")
    p.add_argument("--pack-id", required=True)
    p.add_argument("--pack", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--arm", action="append", choices=ARMS)
    p.set_defaults(func=cmd_prompts)
    p = sub.add_parser("score")
    p.add_argument("--pack-id", required=True)
    p.add_argument("--responses", required=True)
    p.add_argument("--baseline", default="raw", choices=ARMS)
    p.add_argument("--defects", help="JSON {arm: {item: true|false}}: whether each reply found the planted defect")
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(func=cmd_score)
    p = sub.add_parser("pairwise-sheet")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(func=cmd_pairwise_sheet)
    p = sub.add_parser("pairwise-score")
    p.add_argument("--key", required=True)
    p.add_argument("--pick", action="append", required=True)
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(func=cmd_pairwise_score)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
