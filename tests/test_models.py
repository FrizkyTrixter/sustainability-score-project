import unittest
from models import ScorePayload

class TestScorePayloadValidation(unittest.TestCase):
    def test_valid_payload_has_no_errors(self):
        payload = ScorePayload.from_dict({
            "product_name": "Reusable Bottle",
            "materials": ["aluminum", "plastic"],
            "weight_grams": 300,
            "transport": "air",
            "packaging": "recyclable",
            "gwp": 5.0,
            "cost": 10.0,
            "circularity": 80.0,
        })
        self.assertEqual(payload.validate(), [])

    def test_missing_required_fields(self):
        payload = ScorePayload.from_dict({
            "product_name": "",
            "gwp": -5,
            "cost": -1,
            "circularity": 200,
            "weight_grams": -10,
            "transport": "",
            "packaging": "",
        })
        errors = payload.validate()
        self.assertTrue(any("product_name is required." in e for e in errors))
        self.assertTrue(any("must be >= 0" in e for e in errors))
        self.assertTrue(any("circularity must be <= 100." in e for e in errors))
        self.assertTrue(any("transport is required." in e for e in errors))
        self.assertTrue(any("packaging is required." in e for e in errors))

if __name__ == "__main__":
    unittest.main()
