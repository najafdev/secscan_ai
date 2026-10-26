import unittest
from workbench.evidence_safety import summarize_records


class EvidenceSafetyTests(unittest.TestCase):
    def test_real_values_are_not_exported(self):
        result = summarize_records(
            [{"id": 1, "email": "person@example.test", "password": "secret"}]
        )
        rendered = repr(result)
        self.assertNotIn("person@example.test", rendered)
        self.assertNotIn("secret", rendered)
        self.assertFalse(result["ordinary_values_exported"])
        self.assertEqual(result["columns"], ["email", "id", "password"])

    def test_synthetic_canary_is_retained_as_proof(self):
        result = summarize_records(
            [{"id": 1, "marker": "SECSCAN_AI-SYNTHETIC-abc123", "name": "do-not-export"}]
        )
        self.assertEqual(
            result["synthetic_canaries"][0]["value"], "SECSCAN_AI-SYNTHETIC-abc123"
        )
        self.assertNotIn("do-not-export", repr(result))

    def test_hash_changes_when_source_changes(self):
        a = summarize_records([{"id": 1}])
        b = summarize_records([{"id": 2}])
        self.assertNotEqual(a["content_sha256"], b["content_sha256"])

    def test_invalid_shape_rejected(self):
        with self.assertRaises(ValueError):
            summarize_records({"id": 1})


if __name__ == "__main__":
    unittest.main()
