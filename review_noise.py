#!/usr/bin/env python3
"""固定シードの無作為標本と、ノイズルールの集計を生成する。"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from noise_rules import clean_text, noise_labels, should_exclude


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("data"))
    parser.add_argument("--sample-size", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20261015)
    parser.add_argument("--output", type=Path, default=Path("analysis/random_sample_150.csv"))
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for path in sorted(args.input_dir.glob("speeches_*.jsonl"))
        for line in path.open(encoding="utf-8")
    ]
    sample = random.Random(args.seed).sample(rows, args.sample_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "speechID", "date", "nameOfMeeting", "speaker", "speakerPosition",
        "text_length", "rule_labels", "default_exclude", "manual_decision",
        "cleaned_speech", "original_speech",
    ]
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in sample:
            writer.writerow({
                "speechID": row["speechID"],
                "date": row["date"],
                "nameOfMeeting": row["nameOfMeeting"],
                "speaker": row["speaker"],
                "speakerPosition": row.get("speakerPosition") or "",
                "text_length": len(row["speech"]),
                "rule_labels": ";".join(noise_labels(row)),
                "default_exclude": should_exclude(row),
                "manual_decision": "",
                "cleaned_speech": clean_text(row["speech"]),
                "original_speech": row["speech"],
            })

    labels = Counter(label for row in rows for label in noise_labels(row))
    excluded = sum(should_exclude(row) for row in rows)
    print(f"all_records={len(rows)} sample={len(sample)} seed={args.seed}")
    for label, count in labels.most_common():
        print(f"{label}={count} ({count / len(rows):.1%})")
    print(f"default_excluded={excluded} ({excluded / len(rows):.1%})")
    print(f"default_kept={len(rows) - excluded} ({(len(rows) - excluded) / len(rows):.1%})")
    print(f"sample_file={args.output}")


if __name__ == "__main__":
    main()
