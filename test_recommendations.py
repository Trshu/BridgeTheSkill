import unittest
import database
import recommendations


class TestRecommendations(unittest.TestCase):

    def test_missing_skills(self):
        result = recommendations.get_missing_skills(2, [3, 7])
        self.assertEqual(result, {10, 13, 20})

    def test_no_missing_skills(self):
        skills = list(database.get_required_skills(2))
        result = recommendations.analyze_skills(2, skills)
        self.assertEqual(result, [])

    def test_recommendation_count(self):
        result = recommendations.analyze_skills(2, [])
        self.assertEqual(len(result), 3)

    def test_recommendation_order(self):
        result = recommendations.analyze_skills(2, [3, 7])
        scores = [course["score"] for course in result]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_recommendation_format(self):
        result = recommendations.analyze_skills(2, [3, 7])
        self.assertTrue(result)

        for course in result:
            self.assertIn("title", course)
            self.assertIn("score", course)
            self.assertIn("explanation", course)
            self.assertGreater(course["score"], 0)


if __name__ == "__main__":
    unittest.main()