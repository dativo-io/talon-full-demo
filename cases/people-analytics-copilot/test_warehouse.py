"""DuckDB source-of-truth and privacy-boundary tests (no model/provider calls)."""
import os
import tempfile
import unittest
from pathlib import Path

import warehouse


class WarehouseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.previous = os.environ.get("HR_DEMO_DB_PATH")
        os.environ["HR_DEMO_DB_PATH"] = str(Path(cls.temp.name) / "people.duckdb")
        cls.seed_result = warehouse.seed()

    @classmethod
    def tearDownClass(cls):
        if cls.previous is None:
            os.environ.pop("HR_DEMO_DB_PATH", None)
        else:
            os.environ["HR_DEMO_DB_PATH"] = cls.previous
        cls.temp.cleanup()

    def test_seed_is_persistent_and_idempotent(self):
        self.assertTrue(Path(self.seed_result["path"]).is_file())
        self.assertEqual(warehouse.row_count(), 1200)
        second = warehouse.seed()
        self.assertFalse(second["seeded"])
        self.assertEqual(second["employees"], 1200)

    def test_duckdb_aggregates_match_raw_sql(self):
        hc = warehouse.headcount_summary()
        self.assertGreater(sum(x["active_headcount"] for x in hc["departments"]), 700)
        for dept in warehouse.departments():
            rows = warehouse.headcount_summary(dept)["departments"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["department"], dept)
        self.assertEqual(
            sum(r["active_headcount"] for r in hc["departments"]),
            warehouse.sql_rows("""SELECT COUNT(*) AS n FROM employees
                                  WHERE hire_date <= '2026-09-30' AND
                                    (termination_date IS NULL OR termination_date > '2026-09-30')""")[0]["n"])

    def test_attrition_series_has_real_12_month_history(self):
        result = warehouse.attrition_summary(months=12)
        self.assertEqual(result["period"], "2026-09")
        self.assertTrue(result["cohorts"])
        for r in result["cohorts"]:
            self.assertEqual(len(r["months"]), 12)
            self.assertEqual(r["months"][-1]["month"], "2026-09")
            self.assertTrue(all(x["attrition_rate_pct"] >= 0 for x in r["months"]))

    def test_aggregation_does_not_disclose_employee_records(self):
        import json
        payload = [warehouse.attrition_summary(), warehouse.headcount_summary(),
                   warehouse.tenure_summary(), warehouse.dashboard_summary()]
        packed = json.dumps(payload)
        self.assertNotIn("monthly_salary_mxn", packed)
        self.assertNotIn("full_name", packed)
        self.assertNotIn("employee_id", packed)
        private = warehouse.privileged_employee_detail()
        self.assertEqual(private["synthetic"], True)
        self.assertIn("monthly_salary_mxn", private["employees"][0])

    def test_untrusted_department_never_interpolated_into_sql(self):
        for fn in [warehouse.attrition_summary, warehouse.headcount_summary,
                   warehouse.tenure_summary, warehouse.dashboard_summary]:
            with self.assertRaisesRegex(ValueError, "Unknown department"):
                fn("Sales' OR 1=1 --")
        with self.assertRaises(ValueError):
            warehouse.attrition_summary(months=0)
        with self.assertRaises(ValueError):
            warehouse.attrition_summary(months=True)

    def test_tenure_bands_and_scoped_dashboard(self):
        tenure = warehouse.tenure_summary("Sales")
        self.assertGreater(tenure["average_tenure_years"], 0)
        self.assertTrue(tenure["bands"])
        for x in tenure["bands"]:
            self.assertGreaterEqual(x["headcount"], 10)
        stats = warehouse.dashboard_summary("Sales")
        self.assertEqual(stats["warehouse"], "DuckDB")
        self.assertEqual(stats["department"], "Sales")
        self.assertEqual(len(stats["attrition_12m"]), 12)


if __name__ == "__main__":
    unittest.main()
