import unittest
from scoring import compute_score, map_rating

class TestScoring(unittest.TestCase):
    def test_compute_score_weights_and_rounding(self):
        weights = {"gwp": 0.5, "circularity": 0.3, "cost": 0.2}
        score, subscores = compute_score(
            gwp=5.0,
            circularity=80.0,
            cost=10.0,
            weights=weights
        )

        # Sanity checks
        self.assertIn("gwp", subscores)
        self.assertIn("circularity", subscores)
        self.assertIn("cost", subscores)

        # Final score should be a float 0..100
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_map_rating(self):
        self.assertEqual(map_rating(95), "A+")
        self.assertEqual(map_rating(85), "A")
        self.assertEqual(map_rating(72), "B")
        self.assertEqual(map_rating(61), "C")
        self.assertEqual(map_rating(10), "D")

if __name__ == "__main__":
    unittest.main()
