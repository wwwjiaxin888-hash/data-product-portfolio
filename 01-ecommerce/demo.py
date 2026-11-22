"""Recompute aggregate behavior metrics, retention, and an ordered category funnel."""

import argparse
import csv
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
LOCAL_TIME = timezone(timedelta(hours=8))
QUERIES = ("behavior_metrics.sql", "next_day_retention.sql", "category_funnel.sql")


def read_events(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            stamp = int(row["timestamp"])
            date = datetime.fromtimestamp(stamp, LOCAL_TIME).date().isoformat()
            yield row["user_id"], row["category_id"], date, row["behavior_type"], stamp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events_csv", nargs="?", type=Path, default=HERE / "sample_events.csv")
    args = parser.parse_args()

    with closing(sqlite3.connect(":memory:")) as db:
        db.execute(
            """
            CREATE TABLE events (
                user_id TEXT NOT NULL,
                category_id TEXT NOT NULL,
                event_date TEXT NOT NULL,
                behavior_type TEXT NOT NULL,
                event_ts INTEGER NOT NULL
            )
            """
        )
        db.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?)", read_events(args.events_csv))
        db.execute("CREATE INDEX event_lookup ON events(user_id, category_id, behavior_type, event_ts)")
        writer = csv.writer(sys.stdout, lineterminator="\n")
        for filename in QUERIES:
            print(filename)
            result = db.execute((HERE / filename).read_text(encoding="utf-8"))
            writer.writerow(column[0] for column in result.description)
            writer.writerows(result)
            print()


if __name__ == "__main__":
    main()
