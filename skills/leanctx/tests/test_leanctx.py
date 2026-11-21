#!/usr/bin/env python3
"""
Exhaustive Offline Unit & Integration Test Suite for leanctx.
Tests all scripts, hooks, CLI wrappers, fail-open semantics, daemon bypasses,
subagent isolation, and schema contracts with 0 external network/LLM dependencies.
"""
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Import scripts directly for white-box unit testing
SKILLS_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILLS_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import telemetry
import ledger_tool
import benchmark


class TestLeanctxBenchmark(unittest.TestCase):
    def test_benchmark_sla_assertions(self):
        results = benchmark.run_benchmark(total_turns=10)
        deltas = results["deltas"]
        self.assertGreater(deltas["token_savings_percentage"], 80.0)
        self.assertGreater(deltas["watermark_reduction_percentage"], 80.0)
        self.assertEqual(results["leanctx"]["constraint_retention_pct"], 100.0)
        self.assertLess(results["leanctx"]["final_watermark_tokens"], 8000)


class TestLeanctxSessionInit(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.conv_id = "test-conv-1234"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(f"/tmp/leanctx/{self.conv_id}", ignore_errors=True)

    def test_session_init_creates_secure_scratch_and_registers_master(self):
        payload = {
            "conversationId": self.conv_id,
            "workspacePaths": [self.test_dir]
        }
        script_path = SCRIPTS_DIR / "session_init.py"
        res = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out, {"injectSteps": []})

        # Check scratch directory creation and 0700 permissions
        scratch_dir = Path(f"/tmp/leanctx/{self.conv_id}")
        self.assertTrue(scratch_dir.is_dir())
        mode = scratch_dir.stat().st_mode & 0o777
        self.assertEqual(mode, 0o700)

        # Check master session file
        session_file = Path(self.test_dir) / ".agents" / "memory" / ".master_session"
        self.assertTrue(session_file.is_file())
        self.assertEqual(session_file.read_text().strip(), self.conv_id)

    def test_session_init_updates_gitignore(self):
        gitignore = Path(self.test_dir) / ".gitignore"
        gitignore.write_text("node_modules/\n")

        payload = {
            "conversationId": self.conv_id,
            "workspacePaths": [self.test_dir]
        }
        script_path = SCRIPTS_DIR / "session_init.py"
        subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        updated = gitignore.read_text()
        self.assertIn(".agents/memory/", updated)


class TestLeanctxGateTool(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.script_path = SCRIPTS_DIR / "gate_tool.py"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gate_tool_wraps_high_volume_commands(self):
        payload = {
            "conversationId": "gate-test-1",
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "pytest tests/ -v"}
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out.get("decision"), "allow")
        self.assertIn("overwrite", out)
        overwritten_cmd = out["overwrite"]["CommandLine"]
        self.assertIn("pytest tests/ -v", overwritten_cmd)
        self.assertIn("INITIAL OUTPUT (Head 25)", overwritten_cmd)
        self.assertIn("FINAL OUTPUT (Tail 25)", overwritten_cmd)

    def test_gate_tool_bypasses_low_volume_commands(self):
        payload = {
            "conversationId": "gate-test-2",
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status -s"}
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out.get("decision"), "allow")
        self.assertNotIn("overwrite", out)

    def test_gate_tool_bypasses_daemon_processes(self):
        payload = {
            "conversationId": "gate-test-3",
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "npm run test:watch",
                    "IsDaemon": True
                }
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        out = json.loads(res.stdout)
        self.assertEqual(out.get("decision"), "allow")
        self.assertNotIn("overwrite", out)

    def test_gate_tool_clamps_large_unbounded_read_file(self):
        large_file = Path(self.test_dir) / "large.py"
        large_file.write_text("\n".join([f"line_{i} = {i}" for i in range(250)]))

        payload = {
            "conversationId": "gate-test-4",
            "toolCall": {
                "name": "read_file",
                "args": {"Path": str(large_file)}
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        out = json.loads(res.stdout)
        self.assertEqual(out.get("decision"), "allow")
        self.assertIn("overwrite", out)
        self.assertEqual(out["overwrite"]["StartLine"], 1)
        self.assertEqual(out["overwrite"]["EndLine"], 150)

    def test_gate_tool_fail_open_on_malformed_input(self):
        res = subprocess.run(
            [sys.executable, str(self.script_path)],
            input="MALFORMED_JSON",
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out.get("decision"), "allow")


class TestLeanctxLedgerAndSubagentIsolation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.master_id = "master-agent-999"
        self.subagent_id = "subagent-worker-111"
        self.update_script = SCRIPTS_DIR / "update_ledger.py"
        self.inject_script = SCRIPTS_DIR / "inject_anchor.py"

        # Register master
        memory_dir = Path(self.test_dir) / ".agents" / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / ".master_session").write_text(self.master_id)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_subagent_cannot_mutate_master_ledger(self):
        payload = {
            "conversationId": self.subagent_id,
            "workspacePaths": [self.test_dir],
            "toolCall": {
                "name": "write_file",
                "args": {"Path": f"{self.test_dir}/subagent_scratch.py"}
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.update_script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        ledger_file = Path(self.test_dir) / ".agents" / "memory" / "LEDGER.json"
        self.assertFalse(ledger_file.exists())

    def test_master_agent_mutates_ledger_atomically(self):
        target_file = Path(self.test_dir) / "core_auth.py"
        target_file.touch()

        payload = {
            "conversationId": self.master_id,
            "workspacePaths": [self.test_dir],
            "toolCall": {
                "name": "write_file",
                "args": {"Path": str(target_file)}
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.update_script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        ledger_file = Path(self.test_dir) / ".agents" / "memory" / "LEDGER.json"
        self.assertTrue(ledger_file.exists())
        data = json.loads(ledger_file.read_text())
        self.assertIn("core_auth.py", data["rank3_semantic_ledger"]["modified_files"])

    def test_inject_anchor_protojson_schema(self):
        # Initialize ledger
        ledger_file = Path(self.test_dir) / ".agents" / "memory" / "LEDGER.json"
        ledger_file.write_text(json.dumps({
            "rank1_root_intent": {"goal": "Optimize context memory"},
            "rank2_active_state": {"current_dag_node": "TASK-01"}
        }))

        payload = {"cwd": self.test_dir}
        res = subprocess.run(
            [sys.executable, str(self.inject_script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertIn("injectSteps", out)
        self.assertEqual(len(out["injectSteps"]), 1)
        step = out["injectSteps"][0]
        self.assertIn("systemMessage", step)
        msg = step["systemMessage"]["systemMessage"]
        self.assertIn("[leanctx-anchor]", msg)
        self.assertIn("Optimize context memory", msg)
        self.assertIn("TASK-01", msg)
        # Verify micro-anchor is bounded (<200 chars)
        self.assertLess(len(msg), 200)


class TestLeanctxUniversalCLIWrappers(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.conv_id = "cli-test-wrap"
        os.environ["CONVERSATION_ID"] = self.conv_id

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(f"/tmp/leanctx/{self.conv_id}", ignore_errors=True)

    def test_lean_run_success_output(self):
        script = SCRIPTS_DIR / "lean_run.py"
        res = subprocess.run(
            [sys.executable, str(script), "echo 'line 1'; echo 'line 2'"],
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("line 1", res.stdout)
        self.assertIn("line 2", res.stdout)

    def test_lean_run_failure_diagnostic_sandwich(self):
        script = SCRIPTS_DIR / "lean_run.py"
        # Run a multi-line failing command
        cmd = "python3 -c 'import sys; [print(f\"log_{i}\") for i in range(80)]; sys.exit(42)'"
        res = subprocess.run(
            [sys.executable, str(script), cmd],
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 42)
        self.assertIn("ERROR DETECTED (Exit code: 42", res.stdout)
        self.assertIn("--- INITIAL OUTPUT (Head 25) ---", res.stdout)
        self.assertIn("--- FINAL OUTPUT (Tail 25) ---", res.stdout)

    def test_lean_read_clamps_lines(self):
        test_file = Path(self.test_dir) / "sample.txt"
        test_file.write_text("\n".join([f"entry_{i}" for i in range(100)]))

        script = SCRIPTS_DIR / "lean_read.py"
        res = subprocess.run(
            [sys.executable, str(script), str(test_file), "--max", "20"],
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("clamped to 20 lines", res.stdout)
        self.assertIn("entry_0", res.stdout)
        self.assertIn("entry_19", res.stdout)
        self.assertNotIn("entry_25", res.stdout)

    def test_ledger_tool_cli_commands(self):
        script = SCRIPTS_DIR / "ledger_tool.py"
        ws = self.test_dir

        # 1. init
        res = subprocess.run([sys.executable, str(script), "-w", ws, "init", "--goal", "Build Cache", "--constraints", "No Redis; Mem < 100MB"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 2. set-task
        res = subprocess.run([sys.executable, str(script), "-w", ws, "set-task", "--id", "T1", "--desc", "Init Store"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 3. anchor
        res = subprocess.run([sys.executable, str(script), "-w", ws, "anchor"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("[leanctx-anchor]", res.stdout)
        self.assertIn("Build Cache", res.stdout)
        self.assertIn("T1", res.stdout)


class TestLeanctxTelemetry(unittest.TestCase):
    def test_estimate_tokens(self):
        self.assertEqual(telemetry.estimate_tokens(""), 0)
        text = "a" * 385
        self.assertEqual(telemetry.estimate_tokens(text), 100)

    def test_evaluate_snr(self):
        sig = "a" * 800
        tot = "a" * 1000
        snr = telemetry.evaluate_snr(sig, tot)
        self.assertAlmostEqual(snr, 80.0, delta=0.5)

    def test_estimate_cost(self):
        cost = telemetry.estimate_cost(input_tokens=1_000_000, output_tokens=100_000, rate_in_per_m=3.0, rate_out_per_m=15.0)
        self.assertEqual(cost, 4.5)


if __name__ == "__main__":
    unittest.main()
