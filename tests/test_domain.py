import copy
import json
import unittest
from pathlib import Path
from opsrag.domain import analyze

class ChangeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(Path("examples/sample.json").read_text())

    def test_stateful_replacement_is_critical(self):
        result = analyze(self.data)
        self.assertEqual(result["risk_rating"], "critical")
        self.assertIn("REPLACE", {f["code"] for f in result["findings"]})

    def test_both_replacement_orders_detected(self):
        self.data["resource_changes"][0]["change"]["actions"] = ["create", "delete"]
        self.assertIn("REPLACE", {f["code"] for f in analyze(self.data)["findings"]})

    def test_public_ingress_detected(self):
        self.assertIn("PUBLIC_INGRESS", {f["code"] for f in analyze(self.data)["findings"]})

    def test_egress_not_mislabeled(self):
        rule = self.data["resource_changes"][1]
        rule["type"] = "aws_security_group_rule"
        rule["change"]["after"]["type"] = "egress"
        self.assertNotIn("PUBLIC_INGRESS", {f["code"] for f in analyze(self.data)["findings"]})

    def test_existing_public_ingress_not_new(self):
        rule = self.data["resource_changes"][1]
        rule["change"]["before"] = copy.deepcopy(rule["change"]["after"])
        self.assertNotIn("PUBLIC_INGRESS", {f["code"] for f in analyze(self.data)["findings"]})

    def test_unknown_values_reported(self):
        self.assertIn("UNKNOWN_VALUES", {f["code"] for f in analyze(self.data)["findings"]})

    def test_sensitive_plan_values_not_exported(self):
        self.data["resource_changes"][0]["change"]["after"]["password"] = "never-export"
        self.assertNotIn("never-export", json.dumps(analyze(self.data)))

    def test_no_op_does_not_count_as_change(self):
        for item in self.data["resource_changes"]:
            item["change"]["actions"] = ["no-op"]
        result = analyze(self.data)
        self.assertEqual(result["change_count"], 0)
        self.assertEqual(result["risk_rating"], "low")

    def test_unsupported_format_rejected(self):
        self.data["format_version"] = "2.0"
        with self.assertRaises(ValueError):
            analyze(self.data)

    def test_data_source_reads_are_not_changes(self):
        for item in self.data["resource_changes"]:
            item["change"]["actions"] = ["read"]
        self.assertEqual(analyze(self.data)["change_count"], 0)

    def test_unsupported_action_rejected(self):
        self.data["resource_changes"][0]["change"]["actions"] = ["invented"]
        with self.assertRaises(ValueError):
            analyze(self.data)
