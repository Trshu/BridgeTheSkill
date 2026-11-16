from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "bridgetheskill.db"
SEED_PATH = BASE / "data" / "seed.json"
SCHEMA_PATH = BASE / "schema.sql"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Connect to SQLite with foreign key enforcement."""
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


@contextmanager
def managed_connection(db_path: str | Path | None = None):
    """Manage database connections and transactions."""
    conn = connect(db_path)

    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize(db_path: str | Path | None = None) -> None:
    """Create database tables and load sample data."""

    with managed_connection(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        role_count = conn.execute(
            "SELECT COUNT(*) FROM career_roles"
        ).fetchone()[0]

        course_count = conn.execute(
            "SELECT COUNT(*) FROM courses"
        ).fetchone()[0]

        if role_count == 0 and course_count == 0:
            _seed_catalog(conn)


def _seed_catalog(conn: sqlite3.Connection) -> None:
    """Load career roles, skills, and courses from seed.json."""

    catalog = json.loads(
        SEED_PATH.read_text(encoding="utf-8")
    )

    role_records = catalog["roles"]
    course_records = catalog["courses"]

    # Collect unique skills from roles and courses.
    names = sorted(
        {
            str(skill).strip()
            for record in role_records + course_records
            for skill in record["skills"]
        },
        key=str.casefold,
    )

    if not names or any(not name for name in names):
        raise ValueError("Sample catalog contains an empty skill")

    # Insert skills.
    conn.executemany(
        "INSERT INTO skills(name) VALUES (?)",
        ((name,) for name in names),
    )

    skill_ids = {
        row["name"].casefold(): row["skill_id"]
        for row in conn.execute(
            "SELECT skill_id, name FROM skills"
        )
    }

    # Insert career roles and their required skills.
    for role in role_records:
        cur = conn.execute(
            """
            INSERT INTO career_roles(title, description)
            VALUES (?, ?)
            """,
            (role["title"], role["description"]),
        )

        conn.executemany(
            """
            INSERT INTO role_skills(role_id, skill_id)
            VALUES (?, ?)
            """,
            [
                (cur.lastrowid, skill_ids[skill.casefold()])
                for skill in set(role["skills"])
            ],
        )

    # Insert courses and the skills they teach.
    for course in course_records:
        cur = conn.execute(
            """
            INSERT INTO courses(title, description, url)
            VALUES (?, ?, ?)
            """,
            (
                course["title"],
                course["description"],
                course.get("url"),
            ),
        )

        conn.executemany(
            """
            INSERT INTO course_skills(course_id, skill_id)
            VALUES (?, ?)
            """,
            [
                (cur.lastrowid, skill_ids[skill.casefold()])
                for skill in set(course["skills"])
            ],
        )


def get_roles(db_path: str | Path | None = None) -> list[dict]:
    """Retrieve career roles and required skills."""

    with managed_connection(db_path) as conn:
        roles = [
            dict(row)
            for row in conn.execute(
                """
                SELECT role_id AS id, title, description
                FROM career_roles
                ORDER BY title
                """
            )
        ]

        for role in roles:
            role["skills"] = [
                row["name"]
                for row in conn.execute(
                    """
                    SELECT s.name
                    FROM skills s
                    JOIN role_skills rs
                        ON rs.skill_id = s.skill_id
                    WHERE rs.role_id = ?
                    ORDER BY s.name
                    """,
                    (role["id"],),
                )
            ]

        return roles


def get_courses(db_path: str | Path | None = None) -> list[dict]:
    """Retrieve courses and their associated skills."""

    with managed_connection(db_path) as conn:
        courses = [
            dict(row)
            for row in conn.execute(
                """
                SELECT course_id AS id, title, description, url
                FROM courses
                ORDER BY title
                """
            )
        ]

        for course in courses:
            course["skills"] = [
                row["name"]
                for row in conn.execute(
                    """
                    SELECT s.name
                    FROM skills s
                    JOIN course_skills cs
                        ON cs.skill_id = s.skill_id
                    WHERE cs.course_id = ?
                    ORDER BY s.name
                    """,
                    (course["id"],),
                )
            ]

        return courses


def get_skills(db_path: str | Path | None = None) -> list[dict]:
    """Retrieve all available skills."""

    with managed_connection(db_path) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT skill_id AS id, name
                FROM skills
                ORDER BY name
                """
            )
        ]


def get_required_skills(
    role_id: int,
    db_path: str | Path | None = None,
) -> set[int]:
    """Retrieve required skill IDs for a career."""

    if type(role_id) is not int:
        raise ValueError("role_id must be an integer")

    with managed_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT 1 FROM career_roles WHERE role_id = ?",
            (role_id,),
        ).fetchone()

        if existing is None:
            raise ValueError(
                f"Unknown career role ID: {role_id}"
            )

        return {
            row[0]
            for row in conn.execute(
                """
                SELECT skill_id
                FROM role_skills
                WHERE role_id = ?
                """,
                (role_id,),
            )
        }


def get_matching_courses(
    missing_skill_ids: set[int],
    limit: int = 5,
    db_path: str | Path | None = None,
) -> list[dict]:
    """Find courses covering missing skills.

    Returns deterministic course candidates.
    Sentence-BERT can rank these candidates separately.
    """

    if type(limit) is not int or not (1 <= limit <= 10):
        raise ValueError(
            "limit must be an integer from 1 to 10"
        )

    if any(type(sid) is not int for sid in missing_skill_ids):
        raise ValueError(
            "missing_skill_ids must contain integers"
        )

    if not missing_skill_ids:
        return []

    ids = sorted(missing_skill_ids)
    placeholders = ",".join("?" for _ in ids)

    with managed_connection(db_path) as conn:
        count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM skills
            WHERE skill_id IN ({placeholders})
            """,
            ids,
        ).fetchone()[0]

        if count != len(ids):
            raise ValueError(
                "At least one skill ID is unknown"
            )

        query = f"""
            SELECT
                c.course_id AS id,
                c.title,
                c.description,
                c.url,
                COUNT(DISTINCT cs.skill_id) AS gap_coverage
            FROM courses c
            JOIN course_skills cs
                ON cs.course_id = c.course_id
            WHERE cs.skill_id IN ({placeholders})
            GROUP BY c.course_id
            ORDER BY gap_coverage DESC, c.title COLLATE NOCASE ASC
            LIMIT ?
        """

        rows = [
            dict(row)
            for row in conn.execute(
                query,
                (*ids, limit),
            )
        ]

        for course in rows:
            covered = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT s.skill_id AS id, s.name
                    FROM skills s
                    JOIN course_skills cs
                        ON cs.skill_id = s.skill_id
                    WHERE cs.course_id = ?
                      AND s.skill_id IN ({placeholders})
                    ORDER BY s.name
                    """,
                    (course["id"], *ids),
                )
            ]

            course["covered_skill_ids"] = [
                skill["id"] for skill in covered
            ]

            course["covered_skill_names"] = [
                skill["name"] for skill in covered
            ]

        return rows