"""Print behavior and retention metrics from a small synthetic event log."""

import csv
import sqlite3
import sys
from contextlib import closing
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main():
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute(
            """
            CREATE TABLE events (
                user_id TEXT NOT NULL,
                category_id TEXT NOT NULL,
                event_date TEXT NOT NULL,
                behavior_type TEXT NOT NULL
            )
            """
        )
        with (HERE / "sample_events.csv").open(encoding="utf-8", newline="") as file:
            rows = csv.DictReader(file)
            db.executemany(
                """
                INSERT INTO events VALUES (:user_id, :category_id, :event_date, :behavior_type)
                """,
                rows,
            )

        writer = csv.writer(sys.stdout, lineterminator="\n")
        for query in ("behavior_metrics.sql", "next_day_retention.sql"):
            print(query)
            result = db.execute((HERE / query).read_text(encoding="utf-8"))
            writer.writerow(column[0] for column in result.description)
            writer.writerows(result)
            print()


if __name__ == "__main__":
    main()
