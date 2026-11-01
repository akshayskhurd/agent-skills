#!/usr/bin/env python3
"""
Unit and Adversarial Test Suite for the Telescope Skill.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
import sys

TELESCOPE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TELESCOPE_DIR / "scripts"))

import orchestrate_dag


class TestTelescope(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_file = Path(self.test_dir) / "PERSPECTIVE.json"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_perspective(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Test Project",
            objective="Deliver resilient rate-limiting dispatcher.",
        )
        self.assertTrue(self.state_file.exists())
        state = orchestrate_dag.load_state(self.state_file)
        self.assertEqual(state["project"], "Test Project")
        self.assertEqual(len(state["tasks"]), 0)

    def test_init_collision_without_overwrite(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Test Project",
            objective="Initial objective.",
        )
        with self.assertRaises(SystemExit):
            orchestrate_dag.init_perspective(
                self.state_file,
                project="Test Project",
                objective="Second attempt.",
                overwrite=False,
            )

    def test_add_task_and_dependencies(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Test Project",
            objective="Deliver system.",
        )
        orchestrate_dag.add_task(
            self.state_file,
            task_id="task-1",
            title="Setup Signer",
            spec="HMAC SHA-256 signature generator.",
        )
        orchestrate_dag.add_task(
            self.state_file,
            task_id="task-2",
            title="Dispatcher",
            spec="HTTP Client.",
            depends_on=["task-1"],
        )

        state = orchestrate_dag.load_state(self.state_file)
        self.assertEqual(len(state["tasks"]), 2)
        self.assertEqual(state["tasks"][1]["depends_on"], ["task-1"])

    def test_add_task_duplicate_id_rejected(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Test Project",
            objective="Deliver system.",
        )
        orchestrate_dag.add_task(
            self.state_file,
            task_id="task-1",
            title="Setup Signer",
            spec="Spec",
        )
        with self.assertRaises(SystemExit):
            orchestrate_dag.add_task(
                self.state_file,
                task_id="task-1",
                title="Duplicate",
                spec="Spec",
            )

    def test_update_task_status(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Test Project",
            objective="Deliver system.",
        )
        orchestrate_dag.add_task(
            self.state_file,
            task_id="task-1",
            title="Setup Signer",
            spec="Spec",
        )
        orchestrate_dag.update_task(
            self.state_file,
            task_id="task-1",
            status="MICRO_GRILLED",
            notes="Passed zero defects in Developer and Security personas.",
        )

        state = orchestrate_dag.load_state(self.state_file)
        self.assertEqual(state["tasks"][0]["status"], "MICRO_GRILLED")
        self.assertIn("Passed zero defects", state["tasks"][0]["notes"])

    def test_update_task_invalid_status_rejected(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Test Project",
            objective="Deliver system.",
        )
        orchestrate_dag.add_task(
            self.state_file,
            task_id="task-1",
            title="Setup Signer",
            spec="Spec",
        )
        with self.assertRaises(SystemExit):
            orchestrate_dag.update_task(
                self.state_file,
                task_id="task-1",
                status="INVALID_STATUS",
            )

    def test_record_clarification(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Test Project",
            objective="Deliver system.",
        )
        orchestrate_dag.record_clarification(
            self.state_file,
            question="Should HTTP 429 respect Retry-After header?",
            answer="Yes, fallback to exponential backoff if missing.",
        )

        state = orchestrate_dag.load_state(self.state_file)
        self.assertEqual(len(state["clarifications_needed"]), 1)
        self.assertTrue(state["clarifications_needed"][0]["resolved"])

    def test_render_perspective_markdown(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Production Engine",
            objective="Build high throughput ingestor.",
        )
        orchestrate_dag.add_task(
            self.state_file,
            task_id="task-1",
            title="Parser",
            spec="Schema validator",
        )
        orchestrate_dag.update_task(
            self.state_file,
            task_id="task-1",
            status="COMPLETED",
        )

        md = orchestrate_dag.render_perspective_markdown(self.state_file)
        self.assertIn("# Macro Perspective Document: Production Engine", md)
        self.assertIn("**Completion**: 1/1 tasks completed", md)
        self.assertIn("`task-1`", md)
        self.assertIn("flowchart TD", md)

    def test_cycle_detection(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Cycle Test",
            objective="Detect cycle.",
        )
        orchestrate_dag.add_task(self.state_file, "t-1", "Task 1", "Spec", depends_on=["t-2"])
        # Adding t-2 depending on t-1 creates a cycle: t-1 -> t-2 -> t-1
        with self.assertRaises(SystemExit):
            orchestrate_dag.add_task(self.state_file, "t-2", "Task 2", "Spec", depends_on=["t-1"])

    def test_resolve_next_tasks_topological(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Topological Test",
            objective="Test next task.",
        )
        orchestrate_dag.add_task(self.state_file, "t-1", "Task 1", "Spec")
        orchestrate_dag.add_task(self.state_file, "t-2", "Task 2", "Spec", depends_on=["t-1"])

        state = orchestrate_dag.load_state(self.state_file)
        ready = orchestrate_dag.resolve_next_tasks(state["tasks"])
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0]["id"], "t-1")

        # After t-1 is micro-grilled, t-2 should become ready
        orchestrate_dag.update_task(self.state_file, "t-1", "MICRO_GRILLED")
        state = orchestrate_dag.load_state(self.state_file)
        ready = orchestrate_dag.resolve_next_tasks(state["tasks"])
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0]["id"], "t-2")

    def test_generate_mermaid_dag(self):
        tasks = [
            {"id": "t-1", "title": "Signer", "status": "COMPLETED", "depends_on": []},
            {"id": "t-2", "title": "Dispatcher", "status": "PENDING", "depends_on": ["t-1"]},
        ]
        mermaid = orchestrate_dag.generate_mermaid_dag(tasks)
        self.assertIn("flowchart TD", mermaid)
        self.assertIn("node_t_1 --> node_t_2", mermaid)
        self.assertIn("classDef completed", mermaid)

    def test_diamond_dependency_topological_resolution(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Diamond DAG",
            objective="Test diamond graph resolution.",
        )
        orchestrate_dag.add_task(self.state_file, "t-root", "Root Task", "Spec")
        orchestrate_dag.add_task(self.state_file, "t-left", "Left Branch", "Spec", depends_on=["t-root"])
        orchestrate_dag.add_task(self.state_file, "t-right", "Right Branch", "Spec", depends_on=["t-root"])
        orchestrate_dag.add_task(self.state_file, "t-join", "Join Branch", "Spec", depends_on=["t-left", "t-right"])

        state = orchestrate_dag.load_state(self.state_file)
        ready = orchestrate_dag.resolve_next_tasks(state["tasks"])
        self.assertEqual([t["id"] for t in ready], ["t-root"])

        orchestrate_dag.update_task(self.state_file, "t-root", "MICRO_GRILLED")
        state = orchestrate_dag.load_state(self.state_file)
        ready = orchestrate_dag.resolve_next_tasks(state["tasks"])
        # Both left and right are now unblocked simultaneously
        self.assertEqual([t["id"] for t in ready], ["t-left", "t-right"])

        # Complete only left branch; join must remain blocked
        orchestrate_dag.update_task(self.state_file, "t-left", "COMPLETED")
        state = orchestrate_dag.load_state(self.state_file)
        ready = orchestrate_dag.resolve_next_tasks(state["tasks"])
        self.assertEqual([t["id"] for t in ready], ["t-right"])

        # Complete right branch; join must become unblocked
        orchestrate_dag.update_task(self.state_file, "t-right", "COMPLETED")
        state = orchestrate_dag.load_state(self.state_file)
        ready = orchestrate_dag.resolve_next_tasks(state["tasks"])
        self.assertEqual([t["id"] for t in ready], ["t-join"])

    def test_self_loop_cycle_detection(self):
        orchestrate_dag.init_perspective(
            self.state_file,
            project="Self Loop",
            objective="Detect self loop.",
        )
        with self.assertRaises(SystemExit):
            orchestrate_dag.add_task(self.state_file, "t-loop", "Self Looping Task", "Spec", depends_on=["t-loop"])


if __name__ == "__main__":
    unittest.main()
