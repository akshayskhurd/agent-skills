import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark
import telemetry


def get_expected_scratch_dir(conv_id: str) -> Path:
    uid_suffix = f"-{os.getuid()}" if hasattr(os, "getuid") else ""
    return Path(tempfile.gettempdir()) / f"leanctx{uid_suffix}" / conv_id


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
        self.script_path = SCRIPTS_DIR / "session_init.py"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        scratch = get_expected_scratch_dir(self.conv_id)
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)

    def test_session_init_creates_secure_scratch_and_registers_master(self):
        payload = {
            "conversationId": self.conv_id,
            "workspacePaths": [self.test_dir]
        }
        res = subprocess.run(
            [sys.executable, str(self.script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)

        # Check scratch dir
        scratch_dir = get_expected_scratch_dir(self.conv_id)
        self.assertTrue(scratch_dir.exists())
        if hasattr(os, "chmod"):
            mode = oct(scratch_dir.stat().st_mode & 0o777)
            self.assertEqual(mode, oct(0o700))

        # Check .master_session file
        master_file = Path(self.test_dir) / ".agents" / "memory" / ".master_session"
        self.assertTrue(master_file.exists())
        with open(master_file, "r") as f:
            self.assertEqual(f.read().strip(), self.conv_id)

    def test_session_init_updates_gitignore(self):
        gitignore = Path(self.test_dir) / ".gitignore"
        gitignore.write_text("node_modules/\n")

        payload = {
            "conversationId": self.conv_id,
            "workspacePaths": [self.test_dir]
        }
        subprocess.run(
            [sys.executable, str(self.script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        updated = gitignore.read_text()
        self.assertIn(".agents/memory/", updated)


class TestLeanctxLedgerAndSubagentIsolation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.update_script = SCRIPTS_DIR / "update_ledger.py"
        self.init_script = SCRIPTS_DIR / "session_init.py"
        self.anchor_script = SCRIPTS_DIR / "inject_anchor.py"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_master_agent_mutates_ledger_atomically(self):
        # 1. Initialize master session
        init_payload = {
            "conversationId": "master-session-001",
            "workspacePaths": [self.test_dir]
        }
        subprocess.run(
            [sys.executable, str(self.init_script)],
            input=json.dumps(init_payload),
            text=True,
            capture_output=True
        )

        # 2. Trigger PostToolUse from master agent
        tool_payload = {
            "conversationId": "master-session-001",
            "workspacePaths": [self.test_dir],
            "toolCall": {
                "name": "write_file",
                "args": {"Path": os.path.join(self.test_dir, "src", "cache.py")}
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.update_script)],
            input=json.dumps(tool_payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)

        ledger_file = Path(self.test_dir) / ".agents" / "memory" / "LEDGER.json"
        self.assertTrue(ledger_file.exists())
        with open(ledger_file, "r") as f:
            data = json.load(f)

        files = data["rank3_semantic_ledger"]["modified_files"]
        self.assertIn("src/cache.py", files)
        self.assertEqual(files["src/cache.py"], "modified")

    def test_update_ledger_preserves_public_symbols(self):
        # Initialize master session
        init_payload = {
            "conversationId": "master-session-001",
            "workspacePaths": [self.test_dir]
        }
        subprocess.run([sys.executable, str(self.init_script)], input=json.dumps(init_payload), text=True)

        # Add file with public symbols via ledger_tool.py
        ledger_script = SCRIPTS_DIR / "ledger_tool.py"
        subprocess.run([sys.executable, str(ledger_script), "-w", self.test_dir, "add-file", "--file", "src/auth.py", "--symbols", "validate(t: str) -> bool; refresh()"], text=True)

        # Trigger edit_file via update_ledger.py
        tool_payload = {
            "conversationId": "master-session-001",
            "workspacePaths": [self.test_dir],
            "toolCall": {
                "name": "edit_file",
                "args": {"Path": os.path.join(self.test_dir, "src", "auth.py")}
            }
        }
        res = subprocess.run([sys.executable, str(self.update_script)], input=json.dumps(tool_payload), text=True, capture_output=True)
        self.assertEqual(res.returncode, 0)

        # Verify symbols were preserved and status updated to modified
        ledger_file = Path(self.test_dir) / ".agents" / "memory" / "LEDGER.json"
        with open(ledger_file, "r") as f:
            data = json.load(f)

        auth_meta = data["rank3_semantic_ledger"]["modified_files"]["src/auth.py"]
        self.assertIsInstance(auth_meta, dict)
        self.assertEqual(auth_meta["status"], "modified")
        self.assertIn("validate(t: str) -> bool", auth_meta["symbols"])
        self.assertIn("refresh()", auth_meta["symbols"])

    def test_subagent_cannot_mutate_master_ledger(self):
        # 1. Initialize master session
        init_payload = {
            "conversationId": "master-session-001",
            "workspacePaths": [self.test_dir]
        }
        subprocess.run([sys.executable, str(self.init_script)], input=json.dumps(init_payload), text=True)

        # 2. Write initial state as master
        tool_payload = {
            "conversationId": "master-session-001",
            "workspacePaths": [self.test_dir],
            "toolCall": {
                "name": "write_file",
                "args": {"Path": os.path.join(self.test_dir, "initial.txt")}
            }
        }
        subprocess.run([sys.executable, str(self.update_script)], input=json.dumps(tool_payload), text=True)

        # 3. Subagent attempts to write to master ledger
        subagent_payload = {
            "conversationId": "subagent-worker-999",
            "workspacePaths": [self.test_dir],
            "toolCall": {
                "name": "write_file",
                "args": {"Path": os.path.join(self.test_dir, "subagent_file.txt")}
            }
        }
        res = subprocess.run(
            [sys.executable, str(self.update_script)],
            input=json.dumps(subagent_payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)

        # Verify subagent file was NOT added to master LEDGER.json
        ledger_file = Path(self.test_dir) / ".agents" / "memory" / "LEDGER.json"
        with open(ledger_file, "r") as f:
            data = json.load(f)

        files = data["rank3_semantic_ledger"]["modified_files"]
        self.assertIn("initial.txt", files)
        self.assertNotIn("subagent_file.txt", files)

    def test_inject_anchor_protojson_schema(self):
        # Create a ledger
        ledger_dir = Path(self.test_dir) / ".agents" / "memory"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        ledger_file = ledger_dir / "LEDGER.json"
        with open(ledger_file, "w") as f:
            json.dump({
                "version": 1,
                "rank1_root_intent": {"goal": "Build High-Performance Cache", "constraints": ["No Redis", "Memory < 100MB"]},
                "rank2_active_state": {"current_dag_node": "T1-INIT"}
            }, f)

        payload = {"cwd": self.test_dir}
        res = subprocess.run(
            [sys.executable, str(self.anchor_script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertIn("injectSteps", out)
        self.assertEqual(len(out["injectSteps"]), 1)
        text = out["injectSteps"][0]["systemMessage"]["systemMessage"]
        self.assertIn("[leanctx-anchor]", text)
        self.assertIn("GOAL: Build High-Performance Cache", text)
        self.assertIn("CONSTRAINTS: No Redis; Memory < 100MB", text)
        self.assertIn("ACTIVE: T1-INIT", text)

    def test_inject_anchor_subagent_isolation(self):
        # Setup master session and master ledger
        mem_dir = Path(self.test_dir) / ".agents" / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / ".master_session").write_text("master-001\n")
        (mem_dir / "LEDGER.json").write_text(json.dumps({
            "rank1_root_intent": {"goal": "Master Objective", "constraints": ["Global Constraint"]},
            "rank2_active_state": {"current_dag_node": "M1"}
        }))

        # Setup worker subagent ledger
        (mem_dir / "LEDGER_worker_99.json").write_text(json.dumps({
            "rank1_root_intent": {"goal": "Subagent Sharded Task", "constraints": ["Worker Constraint"]},
            "rank2_active_state": {"current_dag_node": "W1"}
        }))

        # Subagent invocation
        subagent_payload = {
            "cwd": self.test_dir,
            "conversationId": "worker_99"
        }
        res = subprocess.run(
            [sys.executable, str(self.anchor_script)],
            input=json.dumps(subagent_payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        text = out["injectSteps"][0]["systemMessage"]["systemMessage"]
        self.assertIn("Subagent Sharded Task", text)
        self.assertIn("Worker Constraint", text)
        self.assertIn("W1", text)
        self.assertNotIn("Master Objective", text)

        # Uninitialized subagent: verify it receives empty injectSteps and does NOT leak master's anchor
        uninit_payload = {
            "cwd": self.test_dir,
            "conversationId": "uninit_worker_100"
        }
        res = subprocess.run(
            [sys.executable, str(self.anchor_script)],
            input=json.dumps(uninit_payload),
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out.get("injectSteps", []), [])


class TestLeanctxGateTool(unittest.TestCase):
    def setUp(self):
        self.script_path = SCRIPTS_DIR / "gate_tool.py"

    def test_gate_tool_wraps_high_volume_commands(self):
        for cmd in ["pytest tests/ -v", "uv run pytest", "cargo test", "npm run build"]:
            payload = {
                "conversationId": "gate-test-01",
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": cmd}
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
            self.assertIn("lean_run.py", overwritten_cmd)
            self.assertIn(cmd, overwritten_cmd)

    def test_gate_tool_ignores_git_commit_and_cat(self):
        # Verify overly broad regex bug is fixed: commit messages with 'build' or 'test' are not wrapped
        for cmd in ['git commit -m "fix build and test"', 'cat test_data.json', 'echo "running test; cargo build"']:
            payload = {
                "conversationId": "gate-test-commit",
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": cmd}
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

    def test_gate_tool_bypasses_low_volume_commands(self):
        payload = {
            "conversationId": "gate-test-02",
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status"}
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
            "conversationId": "gate-test-03",
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
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out.get("decision"), "allow")
        self.assertNotIn("overwrite", out)

    def test_gate_tool_clamps_large_unbounded_read_file(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            for i in range(250):
                f.write(f"Line {i}\n")
            temp_path = f.name

        try:
            payload = {
                "toolCall": {
                    "name": "read_file",
                    "args": {"Path": temp_path}
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
            self.assertEqual(out["overwrite"]["StartLine"], 1)
            self.assertEqual(out["overwrite"]["EndLine"], 150)
        finally:
            os.remove(temp_path)

    def test_gate_tool_fail_open_on_malformed_input(self):
        res = subprocess.run(
            [sys.executable, str(self.script_path)],
            input="invalid-json",
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out.get("decision"), "allow")


class TestLeanctxUniversalCLIWrappers(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_lean_run_success_output(self):
        script = SCRIPTS_DIR / "lean_run.py"
        # Command with 50 lines of output
        cmd = "python3 -c 'for i in range(50): print(f\"line_{i}\")'"
        res = subprocess.run(
            [sys.executable, str(script), cmd],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Tail 25 lines displayed", res.stdout)
        self.assertIn("line_49", res.stdout)
        self.assertNotIn("line_0\n", res.stdout)

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
        self.assertIn("--- INITIAL OUTPUT (Head 15) ---", res.stdout)
        self.assertIn("--- FINAL OUTPUT (Tail 15) ---", res.stdout)

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

    def test_lean_read_clamps_minified_single_line_token_bomb(self):
        test_file = Path(self.test_dir) / "bundle.min.js"
        # 1-line file with 10,000 characters
        test_file.write_text("var x = 1;" * 1000 + "\n")

        script = SCRIPTS_DIR / "lean_read.py"
        res = subprocess.run(
            [sys.executable, str(script), str(test_file)],
            text=True,
            capture_output=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("[...line truncated]", res.stdout)
        # Verify output line does not exceed line budget + truncation notice
        lines = res.stdout.splitlines()
        content_lines = [l for l in lines if not l.startswith("[leanctx:")]
        for l in content_lines:
            self.assertLessEqual(len(l), 530)

    def test_ledger_tool_cli_commands(self):
        script = SCRIPTS_DIR / "ledger_tool.py"
        ws = self.test_dir

        # 1. init
        res = subprocess.run([sys.executable, str(script), "-w", ws, "init", "--goal", "Build Cache", "--constraints", "No Redis; Mem < 100MB"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 2. set-task
        res = subprocess.run([sys.executable, str(script), "-w", ws, "set-task", "--id", "T1", "--desc", "Init Store"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 3. anchor (verifies GOAL, CONSTRAINTS, ACTIVE, <= 240 chars)
        res = subprocess.run([sys.executable, str(script), "-w", ws, "anchor"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("[leanctx-anchor]", res.stdout)
        self.assertIn("GOAL: Build Cache", res.stdout)
        self.assertIn("CONSTRAINTS: No Redis; Mem < 100MB", res.stdout)
        self.assertIn("ACTIVE: T1 (Init Store)", res.stdout)
        self.assertLessEqual(len(res.stdout.strip()), 240)

        # 4. add-file with symbols
        res = subprocess.run([sys.executable, str(script), "-w", ws, "add-file", "--file", "src/cache.py", "--symbols", "get(k: str) -> str; set(k: str, v: str)"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 5. add-decision
        res = subprocess.run([sys.executable, str(script), "-w", ws, "add-decision", "--text", "Adopt LRU eviction"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 6. add-rejection (negative knowledge / dead end)
        res = subprocess.run([sys.executable, str(script), "-w", ws, "add-rejection", "--approach", "Redis subprocess", "--reason", "Violated memory constraint"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 7. amend-intent (user authorized amendment)
        res = subprocess.run([sys.executable, str(script), "-w", ws, "amend-intent", "--goal", "Build Distributed Cache", "--constraints", "Mem < 200MB", "--reason", "User scaled workload"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # 8. rehydrate (verifies all sections restored)
        res = subprocess.run([sys.executable, str(script), "-w", ws, "rehydrate"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("[leanctx-rehydrate]", res.stdout)
        self.assertIn("ROOT INTENT: Build Distributed Cache", res.stdout)
        self.assertIn("NON-NEGOTIABLE CONSTRAINTS: Mem < 200MB", res.stdout)
        self.assertIn("ACTIVE TASK: [T1] Init Store", res.stdout)
        self.assertIn("Adopt LRU eviction", res.stdout)
        self.assertIn("Redis subprocess -> REJECTED: Violated memory constraint", res.stdout)
        self.assertIn("src/cache.py: get(k: str) -> str, set(k: str, v: str)", res.stdout)

        # 9. status
        res = subprocess.run([sys.executable, str(script), "-w", ws, "status"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Status: Active", res.stdout)
        self.assertIn("Files Tracked: 1", res.stdout)
        self.assertIn("Decisions: 1", res.stdout)
        self.assertIn("Dead Ends: 1", res.stdout)

        # 10. session isolation
        res = subprocess.run([sys.executable, str(script), "-w", ws, "-s", "worker_99", "init", "--goal", "Isolated Worker Task"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        worker_file = Path(ws) / ".agents" / "memory" / "LEDGER_worker_99.json"
        self.assertTrue(worker_file.exists())


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
