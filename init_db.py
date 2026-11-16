import sqlite3
from contextlib import closing
from database import DB_PATH, initialize

initialize()
with closing(sqlite3.connect(DB_PATH)) as db:
    for name in ("career_roles", "skills", "role_skills", "courses", "course_skills"):
        count = db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name:14s} {count:3d} records")
    violations = list(db.execute("PRAGMA foreign_key_check"))
    if violations:
        raise SystemExit(f"Foreign key violations: {violations}")
print(f"\nSQLite database ready: {DB_PATH}")
