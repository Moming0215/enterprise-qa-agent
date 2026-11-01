"""Command-line entry point. Run with python -m src.cli --input FILE."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .agent import run_agent


def main() -> int:
    parser = argparse.ArgumentParser(description="Evidence-grounded enterprise QA agent")
    parser.add_argument("--input", required=True, help="UTF-8 JSON file with question and optional history")
    parser.add_argument("--mode", choices=["mock", "online"], default="mock")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--fail-tool", choices=["search_documents", "read_snippet"])
    parser.add_argument("--corpus", help="Alternate synthetic document JSON file")
    parser.add_argument("--index-dir", help="Use a prebuilt hybrid PDF/Markdown index")
    parser.add_argument("--output", help="Write output JSON to this path")
    args = parser.parse_args()
    try:
        request = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error(f"cannot read input JSON: {type(exc).__name__}")
    result = run_agent(request, args.mode, args.max_steps, args.fail_tool, args.corpus, args.index_dir)
    result["executed_at_utc"] = datetime.now(timezone.utc).isoformat()
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(output)
    return 0 if result["status"] != "incomplete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
