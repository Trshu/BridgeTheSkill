import database
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def get_missing_skills(role_id: int, skill_ids: list[int]) -> set[int]:
    """Identify required career skills the user does not have."""

    required_skills = database.get_required_skills(role_id)
    existing_skills = set(skill_ids)

    return required_skills - existing_skills

def get_skill_names(skill_ids: set[int]) -> list[str]:
    """Convert skill IDs into their corresponding names."""

    skills = database.get_skills()

    return [
        skill["name"]
        for skill in skills
        if skill["id"] in skill_ids
    ]

def get_course_text(course: dict) -> str:
    """Combine course information into searchable text."""

    return " ".join([
        course["title"],
        course["description"] or "",
        " ".join(course["skills"])
    ])


def score_courses(missing_skills: list[str], courses: list[dict]):
    """Calculate similarity between missing skills and courses."""

    if not missing_skills or not courses:
        return []

    query = " ".join(missing_skills)

    course_texts = [
        get_course_text(course)
        for course in courses
    ]

    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform(
        [query] + course_texts
    )

    scores = cosine_similarity(
        vectors[0:1],
        vectors[1:]
    )[0]

    return scores.tolist()

def analyze_skills(role_id: int, skill_ids: list[int]) -> list[dict]:
    """Return up to three courses addressing the user's skill gaps."""

    missing_ids = get_missing_skills(role_id, skill_ids)

    if not missing_ids:
        return []

    missing_names = get_skill_names(missing_ids)
    courses = database.get_courses()
    scores = score_courses(missing_names, courses)

    recommendations = []

    for course, score in zip(courses, scores):
        matched = set(missing_names) & set(course["skills"])

        if score > 0 and matched:
            recommendations.append({
                "title": course["title"],
                "score": score,
                "explanation": "Develops missing skills: "
                + ", ".join(sorted(matched))
            })

    recommendations.sort(
        key=lambda course: course["score"],
        reverse=True
    )

    return recommendations[:3]
if __name__ == "__main__":
    recommendations = analyze_skills(2, [3, 7])

    for course in recommendations:
        print(course["title"])
        print(f"Score: {course['score']:.4f}")
        print(course["explanation"])
        print()