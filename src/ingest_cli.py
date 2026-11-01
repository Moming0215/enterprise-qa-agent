"""Build a local hybrid index from PDF and Markdown files."""

import argparse
import json
import sys

from .hybrid_knowledge import build_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Index PDF/Markdown knowledge documents")
    parser.add_argument("--source", required=True, help="Directory containing PDF/Markdown files")
    parser.add_argument("--index", required=True, help="Output directory for local Qdrant and parent store")
    args = parser.parse_args()
    try:
        result = build_index(args.source, args.index)
    except (ValueError, OSError) as exc:
        print(f"ingestion_failed: {exc}", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not result["failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
