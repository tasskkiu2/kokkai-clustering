#!/usr/bin/env python3
"""国会会議録検索システムAPIから発言を期間指定で取得する。"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://kokkai.ndl.go.jp/api/speech"


def fetch_page(params: dict[str, str | int], retries: int = 5) -> dict:
    url = f"{API_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "kokkai-data-fetcher/1.0"})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def fetch_year(year: int, output: Path, meeting: str, house: str) -> int:
    params: dict[str, str | int] = {
        "nameOfMeeting": meeting,
        "nameOfHouse": house,
        "from": f"{year}-01-01",
        "until": f"{year}-12-31",
        "maximumRecords": 100,
        "recordPacking": "json",
        "startRecord": 1,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as stream:
        while True:
            data = fetch_page(params)
            records = data.get("speechRecord", [])
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += len(records)
            next_position = data.get("nextRecordPosition")
            print(f"{year}: {count}/{data.get('numberOfRecords', count)}", flush=True)
            if not next_position:
                break
            params["startRecord"] = next_position
            time.sleep(0.2)
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, required=True)
    parser.add_argument("--meeting", default="予算委員会")
    parser.add_argument("--house", default="衆議院")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    for year in args.years:
        output = args.output_dir / f"speeches_{year}.jsonl"
        count = fetch_year(year, output, args.meeting, args.house)
        print(f"saved {count} records to {output}")


if __name__ == "__main__":
    main()
