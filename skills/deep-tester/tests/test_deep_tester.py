#!/usr/bin/env python3
"""
Unit and Adversarial Test Suite for Deep-Tester.
Validates combinatorial matrix generator, pairwise coverage, and constraint filtering.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

DEEP_TESTER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEEP_TESTER_DIR / "scripts"))

import matrix_generator


class TestMatrixGenerator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_path = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_cartesian_generation(self):
        dims = {
            "role": ["admin", "guest"],
            "status": ["active", "suspended"],
        }
        matrix = matrix_generator.generate_cartesian_matrix(dims)
        self.assertEqual(len(matrix), 4)
        self.assertIn({"role": "admin", "status": "active"}, matrix)
        self.assertIn({"role": "guest", "status": "suspended"}, matrix)

    def test_cartesian_with_constraint_filter(self):
        dims = {
            "role": ["admin", "guest"],
            "status": ["active", "suspended"],
        }
        # Filter out guest + active
        filtered = matrix_generator.generate_cartesian_matrix(
            dims,
            exclude_filter="role == 'guest' and status == 'active'",
        )
        self.assertEqual(len(filtered), 3)
        self.assertNotIn({"role": "guest", "status": "active"}, filtered)

    def test_filter_with_list_membership(self):
        dims = {
            "role": ["admin", "guest", "moderator"],
            "status": ["active", "suspended"],
        }
        # Filter out any role in ['guest', 'moderator']
        filtered = matrix_generator.generate_cartesian_matrix(
            dims,
            exclude_filter="role in ['guest', 'moderator']",
        )
        self.assertEqual(len(filtered), 2)
        for row in filtered:
            self.assertEqual(row["role"], "admin")

    def test_pairwise_reduction(self):
        dims = {
            "a": [1, 2, 3],
            "b": ["x", "y", "z"],
            "c": [True, False],
        }
        full = matrix_generator.generate_cartesian_matrix(dims)
        pairwise = matrix_generator.generate_pairwise_matrix(dims)

        # Full Cartesian is 3 * 3 * 2 = 18 combinations
        self.assertEqual(len(full), 18)
        # Pairwise must be significantly smaller while covering all 2-way interactions
        self.assertLess(len(pairwise), len(full))
        self.assertGreaterEqual(len(pairwise), 9)

        # Verify every 2-way interaction between 'a' and 'c' is covered
        ac_pairs = {((row["a"]), row["c"]) for row in pairwise}
        for a_val in dims["a"]:
            for c_val in dims["c"]:
                self.assertIn((a_val, c_val), ac_pairs)

    def test_format_pytest(self):
        matrix = [{"role": "admin", "active": True}]
        out = matrix_generator.format_pytest(matrix)
        self.assertIn('@pytest.mark.parametrize("role, active"', out)
        self.assertIn("pytest.param('admin', True", out)

    def test_format_jest(self):
        matrix = [{"role": "admin", "active": True}]
        out = matrix_generator.format_jest(matrix)
        self.assertIn("test.each([", out)
        self.assertIn('"role": "admin"', out)

    def test_format_markdown(self):
        matrix = [{"role": "admin", "active": True}]
        out = matrix_generator.format_markdown(matrix)
        self.assertIn("| # | role | active | Expected Outcome |", out)
        self.assertIn("| 1 | admin | True | `PASS` / `REJECT` |", out)

    def test_format_go(self):
        matrix = [{"role": "admin", "count": 5, "rate": 0.75, "active": True}]
        out = matrix_generator.format_go(matrix)
        self.assertIn("tests := []struct {", out)
        self.assertIn('role: "admin"', out)
        self.assertIn("count: 5", out)
        self.assertIn("rate: 0.75", out)
        self.assertIn("rate float64", out)

    def test_format_rust(self):
        matrix = [{"role": "admin", "count": 5, "rate": 0.75, "active": True}]
        out = matrix_generator.format_rust(matrix)
        self.assertIn("let test_cases = vec![", out)
        self.assertIn('role: "admin"', out)
        self.assertIn("rate: 0.75", out)
        self.assertIn("rate: f64", out)

    def test_format_empty_string_ids(self):
        matrix = [{"val": ""}]
        out = matrix_generator.format_pytest(matrix)
        self.assertIn('id="empty"', out)

    def test_format_junit(self):
        matrix = [{"role": "admin", "status": "active"}]
        out = matrix_generator.format_junit(matrix)
        self.assertIn("@ParameterizedTest", out)
        self.assertIn("@CsvSource", out)


if __name__ == "__main__":
    unittest.main()
