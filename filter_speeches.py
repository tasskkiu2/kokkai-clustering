#!/usr/bin/env python3
"""除外ルールを適用し、採用データと除外ログを別々に保存する。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from noise_rules import clean_text, noise_labels, should_exclude


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("cleaned"))
    parser.add_argument("--include-related-meetings", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for source in args.inputs:
        kept_path = args.output_dir / source.name
        excluded_path = args.output_dir / f"{source.stem}_excluded.jsonl"
        kept = excluded = 0
        with (
            source.open(encoding="utf-8") as src,
            kept_path.open("w", encoding="utf-8") as keep_stream,
            excluded_path.open("w", encoding="utf-8") as exclude_stream,
        ):
            for line in src:
                record = json.loads(line)
                labels = noise_labels(record)
                if should_exclude(record, exact_meeting_only=not args.include_related_meetings):
                    exclude_stream.write(json.dumps({
                        "exclusion_reasons": labels,
                        "record": record,
                    }, ensure_ascii=False) + "\n")
                    excluded += 1
                else:
                    record["speech_cleaned"] = clean_text(record["speech"])
                    record["review_flags"] = [
                        label for label in labels
                        if label in {"very_short_review", "contains_stage_direction"}
                    ]
                    keep_stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    kept += 1
        print(f"{source}: kept={kept} excluded={excluded}")


if __name__ == "__main__":
    main()
