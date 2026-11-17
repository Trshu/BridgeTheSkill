"""Connect the Streamlit form to the catalog and optional AI engine."""
from importlib import import_module

import database


def analyze(role_id, skill_ids):
    names = {skill["id"]: skill["name"] for skill in database.get_skills()}
    gaps = database.get_required_skills(role_id) - set(skill_ids)
    missing = sorted((names[skill_id] for skill_id in gaps), key=str.casefold)
    if not missing:
        return missing, [], "No skill gaps"

    try:
        engine = import_module("recommendations")
    except ModuleNotFoundError as exc:
        if exc.name != "recommendations":
            raise
        courses = database.get_matching_courses(gaps, limit=3)
        return missing, [
            {"title": course["title"],
             "explanation": "Covers: " + ", ".join(course["covered_skill_names"])}
            for course in courses
        ], "Catalog matching only (AI not installed)"

    courses = engine.analyze_skills(role_id, list(skill_ids))
    if not isinstance(courses, list) or any(
        not isinstance(course, dict)
        or any(not isinstance(course.get(field), str) or not course[field].strip()
               for field in ("title", "explanation"))
        for course in courses
    ):
        raise ValueError("Recommendation engine returned an invalid response")
    return missing, courses[:3], "AI recommendations"
