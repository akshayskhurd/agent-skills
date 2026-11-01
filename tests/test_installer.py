#!/usr/bin/env python3
"""Unit tests for the Universal Skills Installer (install.py)."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import install


class TestInstaller(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_installer_")
        self.test_path = Path(self.test_dir)
        self.fake_home = self.test_path / "home"
        self.fake_home.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_discover_source_skills(self):
        skills = install.discover_source_skills()
        self.assertIn("deep-tester", skills)
        self.assertIn("telescope", skills)
        self.assertIn("single-pass-executor", skills)
        self.assertIn("skill-creator", skills)
        self.assertIn("grill", skills)
        self.assertIn("learn", skills)
        self.assertGreaterEqual(len(skills), 6)

    def test_detect_installed_harnesses(self):
        # Create markers for claude and codex
        (self.fake_home / ".claude").mkdir()
        (self.fake_home / ".codex").mkdir()

        detected = install.detect_installed_harnesses(home_dir=self.fake_home)
        self.assertIn("claude", detected)
        self.assertIn("codex", detected)
        self.assertNotIn("pi", detected)
        self.assertNotIn("opencode", detected)

    def test_detect_fallback_to_agents(self):
        # Empty home directory
        detected = install.detect_installed_harnesses(home_dir=self.fake_home)
        self.assertEqual(detected, ["agents"])

    def test_resolve_target_directories_global(self):
        resolved = install.resolve_target_directories(
            targets=["claude", "opencode", "codex", "pi", "gemini", "agents"],
            is_global=True,
            home_dir=self.fake_home,
        )
        self.assertEqual(len(resolved), 6)
        mapping = dict(resolved)
        self.assertEqual(mapping["claude"], self.fake_home / ".claude" / "skills")
        self.assertEqual(mapping["opencode"], self.fake_home / ".opencode" / "skills")
        self.assertEqual(mapping["codex"], self.fake_home / ".codex" / "skills")
        self.assertEqual(mapping["pi"], self.fake_home / ".pi" / "skills")
        self.assertEqual(mapping["gemini"], self.fake_home / ".gemini" / "config" / "skills")
        self.assertEqual(mapping["agents"], self.fake_home / ".agents" / "skills")

    def test_resolve_target_directories_custom_dest(self):
        custom = self.test_path / "custom_dir"
        resolved = install.resolve_target_directories(
            targets=["claude"],
            custom_dest=str(custom),
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0][1], custom.resolve())

    def test_resolve_invalid_harness(self):
        with self.assertRaises(ValueError):
            install.resolve_target_directories(targets=["nonexistent_harness"])

    def test_install_and_uninstall_copy_mode(self):
        target_dir = self.test_path / "installed_claude"
        targets = [("claude", target_dir)]

        # Install deep-tester and telescope
        ret = install.install_skills(
            skills_to_install=["deep-tester", "telescope"],
            target_dirs=targets,
            symlink=False,
            dry_run=False,
        )
        self.assertEqual(ret, 0)
        self.assertTrue((target_dir / "deep-tester" / "SKILL.md").is_file())
        self.assertTrue((target_dir / "telescope" / "SKILL.md").is_file())
        self.assertFalse((target_dir / "deep-tester").is_symlink())

        # Uninstall deep-tester
        ret_un = install.uninstall_skills(
            skills_to_remove=["deep-tester"],
            target_dirs=targets,
            dry_run=False,
        )
        self.assertEqual(ret_un, 0)
        self.assertFalse((target_dir / "deep-tester").exists())
        self.assertTrue((target_dir / "telescope").exists())

    def test_install_symlink_mode(self):
        target_dir = self.test_path / "installed_symlink"
        targets = [("agents", target_dir)]

        ret = install.install_skills(
            skills_to_install=["deep-tester"],
            target_dirs=targets,
            symlink=True,
            dry_run=False,
        )
        self.assertEqual(ret, 0)
        dest_skill = target_dir / "deep-tester"
        self.assertTrue(dest_skill.is_symlink())
        self.assertTrue((dest_skill / "SKILL.md").is_file())

    def test_dry_run_does_not_mutate(self):
        target_dir = self.test_path / "dry_run_target"
        targets = [("codex", target_dir)]

        ret = install.install_skills(
            skills_to_install=["deep-tester"],
            target_dirs=targets,
            symlink=False,
            dry_run=True,
        )
        self.assertEqual(ret, 0)
        self.assertFalse(target_dir.exists())

    def test_install_invalid_skill_fails(self):
        target_dir = self.test_path / "target"
        targets = [("codex", target_dir)]

        ret = install.install_skills(
            skills_to_install=["nonexistent-skill"],
            target_dirs=targets,
            symlink=False,
            dry_run=False,
        )
        self.assertEqual(ret, 1)

    def test_install_sh_script_execution(self):
        import subprocess
        script_path = Path(__file__).resolve().parent.parent / "install.sh"
        self.assertTrue(script_path.is_file())

        # Test --list option
        res = subprocess.run(
            ["bash", str(script_path), "--list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("deep-tester", res.stdout)
        self.assertIn("telescope", res.stdout)

        # Test local copy installation
        local_target = self.test_path / "local_test_proj"
        local_target.mkdir(parents=True, exist_ok=True)

        res_install = subprocess.run(
            [
                "bash",
                str(script_path),
                "--target", "agents",
                "--local",
                "--skills", "deep-tester",
            ],
            cwd=str(local_target),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(res_install.returncode, 0)
        installed_skill = local_target / ".agents" / "skills" / "deep-tester" / "SKILL.md"
        self.assertTrue(installed_skill.is_file())


if __name__ == "__main__":
    unittest.main()
