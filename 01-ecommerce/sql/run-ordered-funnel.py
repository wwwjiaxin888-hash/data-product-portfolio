"""Reproduce the ordered funnel and its sensitivity checks from a local CSV."""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def read_events(path, grain):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = ("user_id", "item_id", "category_id", "behavior_type", "timestamp")
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError("Missing expected event-log columns.")
        for row in reader:
            user, item, category, behavior, timestamp = (row[k].strip() for k in required)
            if not (user and item and category and behavior):
                raise ValueError(f"Empty event key or type at CSV line {reader.line_num}.")
            entity = item if grain == "item" else category
            yield user, entity, category, behavior, int(timestamp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_csv", type=Path, help="Local cleaned event CSV")
    parser.add_argument("--hours", type=int, choices=(24, 48), default=24)
    parser.add_argument("--grain", choices=("item", "category"), default="item")
    args = parser.parse_args()

    with sqlite3.connect(":memory:") as database:
        database.execute(
            "CREATE TABLE events (user_id TEXT, entity_id TEXT, category_id TEXT, "
            "behavior TEXT, ts INTEGER)"
        )
        database.executemany(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)", read_events(args.event_csv, args.grain)
        )
        database.execute(
            "CREATE INDEX events_path ON events(user_id, entity_id, category_id, behavior, ts)"
        )
        result = database.execute(
            (HERE / "ordered-funnel-24h.sql").read_text(encoding="utf-8"),
            {"window_seconds": args.hours * 3600},
        )
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(column[0] for column in result.description)
        writer.writerows(result)


if __name__ == "__main__":
    main()
