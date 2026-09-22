import sqlite3
from pathlib import Path


def get_database_path() -> Path:
    """Resolve the SQLite database path relative to this file."""
    script_dir = Path(__file__).resolve().parent
    return script_dir / "db.sqlite3"


def inspect_database() -> None:
    db_path = get_database_path()

    if not db_path.exists():
        print(f"Database file not found at: {db_path}")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            tables = cursor.fetchall()
    except sqlite3.Error as exc:
        print(f"Unable to inspect database '{db_path}': {exc}")
        return

    print(f"Database: {db_path}")
    print(f"Total tables: {len(tables)}")
    print("\nTable names:")

    for table_name, in tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    inspect_database()
