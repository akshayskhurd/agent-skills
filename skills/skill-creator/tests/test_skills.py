#!/usr/bin/env python3
"""
Comprehensive Unit & Adversarial Tests for Skill-Creator and Single-Pass-Executor.
"""

import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

# Import module under test
import sys

SKILL_CREATOR_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_CREATOR_DIR / "scripts"))

SPE_DIR = SKILL_CREATOR_DIR.parent / "single-pass-executor"
sys.path.insert(0, str(SPE_DIR / "scripts"))

import scaffold_skill
import verify_contracts


class TestSkillCreator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scaffold_happy_path(self):
        skill_dir = scaffold_skill.scaffold_skill(
            name="demo-task",
            description="Use this skill when running demo tasks.",
            target_dir=self.target_dir,
        )
        self.assertTrue((skill_dir / "SKILL.md").exists())
        self.assertTrue((skill_dir / "scripts").is_dir())
        self.assertTrue((skill_dir / "references").is_dir())
        self.assertTrue((skill_dir / "examples").is_dir())

    def test_scaffold_collision_without_overwrite(self):
        scaffold_skill.scaffold_skill(
            name="demo-task",
            description="Use this skill when running demo tasks.",
            target_dir=self.target_dir,
        )
        with self.assertRaises(SystemExit):
            scaffold_skill.scaffold_skill(
                name="demo-task",
                description="Duplicate attempt.",
                target_dir=self.target_dir,
                overwrite=False,
            )

    def test_scaffold_collision_with_overwrite(self):
        scaffold_skill.scaffold_skill(
            name="demo-task",
            description="Initial description.",
            target_dir=self.target_dir,
        )
        skill_dir = scaffold_skill.scaffold_skill(
            name="demo-task",
            description="Updated description.",
            target_dir=self.target_dir,
            overwrite=True,
        )
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Updated description", content)

    def test_parse_frontmatter_block_scalars(self):
        sample = """---
name: sample-scalar
description: >-
  This is a multiline description
  that spans multiple indented lines.
---
# Content
"""
        raw, data = scaffold_skill.parse_frontmatter(sample)
        self.assertIsNotNone(data)
        self.assertEqual(data["name"], "sample-scalar")
        self.assertEqual(
            data["description"],
            "This is a multiline description that spans multiple indented lines.",
        )

    def test_validate_skill_clean(self):
        skill_dir = scaffold_skill.scaffold_skill(
            name="clean-skill",
            description="Use this skill for clean operations.",
            target_dir=self.target_dir,
        )
        self.assertTrue(scaffold_skill.validate_skill(skill_dir))

    def test_validate_skill_name_mismatch(self):
        skill_dir = self.target_dir / "mismatched-dir"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: different-name
description: Valid description under 80 words.
---
# Title
"""
        )
        self.assertFalse(scaffold_skill.validate_skill(skill_dir))

    def test_validate_script_executable_check(self):
        skill_dir = scaffold_skill.scaffold_skill(
            name="script-skill",
            description="Use this skill for script operations.",
            target_dir=self.target_dir,
        )
        script_file = skill_dir / "scripts" / "run.sh"
        script_file.write_text("#!/bin/bash\necho hello\n")
        # Ensure it is NOT executable
        script_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

        # Should pass validation but emit warnings
        self.assertTrue(scaffold_skill.validate_skill(skill_dir))

        # Make executable
        script_file.chmod(stat.S_IRWXU)
        self.assertTrue(scaffold_skill.validate_skill(skill_dir))


class TestVerifyContracts(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_verify_python_syntax(self):
        good_py = self.target_dir / "valid.py"
        good_py.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
        ok, errors = verify_contracts.verify_python_syntax(good_py)
        self.assertTrue(ok)
        self.assertEqual(len(errors), 0)

        bad_py = self.target_dir / "invalid.py"
        bad_py.write_text("def broken(\n")
        ok, errors = verify_contracts.verify_python_syntax(bad_py)
        self.assertFalse(ok)
        self.assertTrue(len(errors) > 0)

    def test_verify_json_schema(self):
        good_json = self.target_dir / "valid.json"
        good_json.write_text('{"status": "ok", "count": 10}')
        ok, errors = verify_contracts.verify_json_schema(good_json)
        self.assertTrue(ok)

        bad_json = self.target_dir / "invalid.json"
        bad_json.write_text('{"status": unquoted}')
        ok, errors = verify_contracts.verify_json_schema(bad_json)
        self.assertFalse(ok)

    def test_verify_shell_syntax(self):
        good_sh = self.target_dir / "valid.sh"
        good_sh.write_text("#!/bin/bash\nif [ -f foo ]; then echo yes; fi\n")
        ok, errors = verify_contracts.verify_shell_syntax(good_sh)
        self.assertTrue(ok)

        bad_sh = self.target_dir / "invalid.sh"
        bad_sh.write_text("#!/bin/bash\nif then fi\n")
        ok, errors = verify_contracts.verify_shell_syntax(bad_sh)
        self.assertFalse(ok)

    def test_file_size_limit(self):
        huge_file = self.target_dir / "huge.py"
        # Temporarily mock stat size check
        original_max = verify_contracts.MAX_FILE_SIZE_BYTES
        try:
            verify_contracts.MAX_FILE_SIZE_BYTES = 50
            huge_file.write_text("x = 1\n" * 20)
            ok, errors = verify_contracts.verify_python_syntax(huge_file)
            self.assertFalse(ok)
            self.assertIn("File size exceeds", errors[0])
        finally:
            verify_contracts.MAX_FILE_SIZE_BYTES = original_max


if __name__ == "__main__":
    unittest.main()
