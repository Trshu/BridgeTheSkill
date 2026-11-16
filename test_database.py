import sqlite3
import tempfile
import unittest
from pathlib import Path
from database import managed_connection, get_courses, get_matching_courses, get_required_skills, get_roles, get_skills, initialize


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test.db"
        initialize(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_catalog_counts(self):
        self.assertEqual(len(get_roles(self.db_path)), 5)
        self.assertEqual(len(get_courses(self.db_path)), 20)
        self.assertEqual(len(get_skills(self.db_path)), 24)

    def test_every_role_and_course_has_skills(self):
        self.assertTrue(all(r["skills"] for r in get_roles(self.db_path)))
        self.assertTrue(all(c["skills"] for c in get_courses(self.db_path)))

    def test_initialize_idempotent(self):
        initialize(self.db_path)
        self.assertEqual(len(get_roles(self.db_path)), 5)
        self.assertEqual(len(get_courses(self.db_path)), 20)

    def test_role_skill_mapping(self):
        analyst = next(r for r in get_roles(self.db_path) if r["title"] == "Data Analyst")
        self.assertIn("SQL", analyst["skills"])
        self.assertEqual(len(get_required_skills(analyst["id"], self.db_path)), 5)

    def test_matching_course_coverage(self):
        sql_id = next(s["id"] for s in get_skills(self.db_path) if s["name"] == "SQL")
        result = get_matching_courses({sql_id}, limit=3, db_path=self.db_path)
        self.assertTrue(result)
        self.assertEqual(result[0]["title"], "SQL Foundations")
        self.assertEqual(result[0]["covered_skill_names"], ["SQL"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            get_required_skills(999, self.db_path)
        with self.assertRaises(ValueError):
            get_matching_courses({999}, db_path=self.db_path)
        with self.assertRaises(ValueError):
            get_matching_courses({1}, limit=11, db_path=self.db_path)
        self.assertEqual(get_matching_courses(set(), db_path=self.db_path), [])

    def test_foreign_keys_enforced(self):
        with managed_connection(self.db_path) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO role_skills(role_id,skill_id) VALUES (?, ?)", (999, 999))
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_seed_data_is_not_overwritten(self):
        with managed_connection(self.db_path) as conn:
            conn.execute("UPDATE career_roles SET description = ? WHERE role_id = 1", ("Custom",))
        initialize(self.db_path)
        with managed_connection(self.db_path) as conn:
            value = conn.execute("SELECT description FROM career_roles WHERE role_id = 1").fetchone()[0]
        self.assertEqual(value, "Custom")


if __name__ == "__main__":
    unittest.main()
