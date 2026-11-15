"""Operator CLI for the growth agent.

    python -m draftmaster_growth run          # one full cycle
    python -m draftmaster_growth status       # what the agent knows
    python -m draftmaster_growth plan         # show today's plan, publish nothing
    python -m draftmaster_growth outreach     # generate + review outreach messages
    python -m draftmaster_growth report       # the latest cycle report

Everything defaults to dry-run. ``--live`` is required to send anything to a
network channel, and even then the channel must be enabled and credentialed.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .agent import GrowthAgent
from .config import GrowthConfig


def _agent(args) -> GrowthAgent:
    settings = GrowthConfig.from_env()
    if args.live:
        settings.allow_publish = True
    if args.state:
        settings.state_path = args.state
    if args.out:
        settings.output_dir = args.out
    if args.exploration is not None:
        settings.exploration_rate = args.exploration
    return GrowthAgent(settings)


def cmd_run(args) -> int:
    agent = _agent(args)
    report = agent.run_cycle(posts=args.posts, videos=args.videos, outreach=not args.no_outreach)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


def cmd_plan(args) -> int:
    agent = _agent(args)
    plan = {}
    for locale in ("en", "ru"):
        topics, variant = agent.decide(limit=args.posts or agent.settings.posts_per_day, locale=locale)
        plan[locale] = {
            "variant": variant,
            "topics": [t.key for t in topics],
            "rendered": [agent.content.render(t, variant=variant).title for t in topics],
        }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args) -> int:
    agent = _agent(args)
    print(json.dumps(agent.status(), ensure_ascii=False, indent=2))
    return 0


def cmd_outreach(args) -> int:
    agent = _agent(args)
    result = agent.do_outreach(limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_report(args) -> int:
    agent = _agent(args)
    runs = agent.store.get("runs", [])
    if not runs:
        print("no cycles have run yet")
        return 0
    print(json.dumps(runs[-1], ensure_ascii=False, indent=2, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="draftmaster-growth", description="DraftMaster AI autonomous growth agent")
    ap.add_argument("--live", action="store_true", help="allow real publishing to credentialed channels")
    ap.add_argument("--state", help="override the state file path")
    ap.add_argument("--out", help="override the output directory")
    ap.add_argument("--exploration", type=float, default=None, help="bandit exploration rate (0..1)")
    sub = ap.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run one full growth cycle")
    p_run.add_argument("--posts", type=int, default=None)
    p_run.add_argument("--videos", type=int, default=None)
    p_run.add_argument("--no-outreach", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_plan = sub.add_parser("plan", help="show the plan without publishing")
    p_plan.add_argument("--posts", type=int, default=None)
    p_plan.set_defaults(func=cmd_plan)

    p_status = sub.add_parser("status", help="show agent state")
    p_status.set_defaults(func=cmd_status)

    p_out = sub.add_parser("outreach", help="generate outreach messages")
    p_out.add_argument("--limit", type=int, default=None)
    p_out.set_defaults(func=cmd_outreach)

    p_rep = sub.add_parser("report", help="print the latest cycle report")
    p_rep.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
