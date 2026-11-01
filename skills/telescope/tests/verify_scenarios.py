#!/usr/bin/env python3
"""
End-to-End Multi-Scenario Verification Script for Telescope.
Executes 3 realistic multi-task scenarios through the full dual-lens lifecycle:
1. Webhook Dispatcher (Distributed Networking / SRE)
2. Database Schema Migration Engine (Infrastructure / Persistence)
3. Multi-Tenant JWT & RBAC Evaluator (Security / Auth)
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

TELESCOPE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TELESCOPE_DIR / "scripts"))

import orchestrate_dag


class TestTelescopeScenarios(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_path = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scenario_1_webhook_dispatcher(self):
        """Scenario 1: Distributed Rate-Limited Webhook Dispatcher."""
        state_file = self.base_path / "webhook_perspective.json"

        # 1. Macro Zoom-Out: Initialize perspective
        orchestrate_dag.init_perspective(
            state_file,
            project="Resilient Webhook Dispatcher",
            objective="Deliver cryptographically signed, rate-limited webhook dispatcher with retry.",
        )

        # 2. DAG Decomposition into 3 Low-Level Tasks
        orchestrate_dag.add_task(
            state_file,
            task_id="task-1-signer",
            title="HMAC SHA-256 Payload Signer",
            spec="Given payload bytes and secret, return hex-encoded signature.",
        )
        orchestrate_dag.add_task(
            state_file,
            task_id="task-2-limiter",
            title="Token-Bucket Rate Limiter",
            spec="Enforce per-domain token bucket limits.",
            depends_on=["task-1-signer"],
        )
        orchestrate_dag.add_task(
            state_file,
            task_id="task-3-dispatcher",
            title="HTTP Dispatcher with Backoff",
            spec="POST requests with exponential jittered backoff.",
            depends_on=["task-2-limiter"],
        )

        # 3. Micro Zoom-In & Grill: Complete Task 1 & 2
        orchestrate_dag.update_task(
            state_file,
            task_id="task-1-signer",
            status="MICRO_GRILLED",
            notes="Passed zero defects in Developer and Security personas with constant-time compare.",
        )
        orchestrate_dag.update_task(
            state_file,
            task_id="task-2-limiter",
            status="MICRO_GRILLED",
            notes="Passed zero defects in QA persona with boundary checks for zero capacity.",
        )

        # 4. Macro Zoom-Out Sanity Check & Clarification Gate
        orchestrate_dag.record_clarification(
            state_file,
            question="When receiving HTTP 429, should dispatcher respect Retry-After header?",
            answer="Yes, prioritize Retry-After header value in seconds; default to exponential backoff if absent.",
        )

        # 5. Micro Zoom-In: Complete Task 3 with clarified contract
        orchestrate_dag.update_task(
            state_file,
            task_id="task-3-dispatcher",
            status="COMPLETED",
            notes="Implemented Retry-After parsing and randomized exponential backoff.",
        )

        # 6. Render & Assert Macro Perspective
        md = orchestrate_dag.render_perspective_markdown(state_file)
        self.assertIn("# Macro Perspective Document: Resilient Webhook Dispatcher", md)
        self.assertIn("Retry-After", md)
        self.assertIn("`task-1-signer`", md)
        self.assertIn("`task-3-dispatcher`", md)

    def test_scenario_2_db_migration_pipeline(self):
        """Scenario 2: Database Schema Migration & Rollback Pipeline."""
        state_file = self.base_path / "db_migration_perspective.json"

        # 1. Macro Zoom-Out: Initialize perspective
        orchestrate_dag.init_perspective(
            state_file,
            project="Schema Migration Engine",
            objective="Safe, atomic SQL schema migrations with hash-based checksum validation.",
        )

        # 2. Decompose into 3 low-level tasks
        orchestrate_dag.add_task(
            state_file,
            task_id="mig-1-checksum",
            title="Migration Checksum Verifier",
            spec="Calculate SHA-256 hash of migration files and compare with db record.",
        )
        orchestrate_dag.add_task(
            state_file,
            task_id="mig-2-lock",
            title="Advisory Lock Manager",
            spec="Acquire cluster-wide advisory lock before applying migrations.",
            depends_on=["mig-1-checksum"],
        )
        orchestrate_dag.add_task(
            state_file,
            task_id="mig-3-runner",
            title="Transactional Script Runner",
            spec="Execute SQL statements inside explicit transaction blocks.",
            depends_on=["mig-2-lock"],
        )

        # 3. Simulate execution and review
        orchestrate_dag.update_task(state_file, "mig-1-checksum", "COMPLETED", "SHA-256 checksums verified.")
        orchestrate_dag.update_task(state_file, "mig-2-lock", "COMPLETED", "PostgreSQL advisory locks verified.")
        orchestrate_dag.update_task(state_file, "mig-3-runner", "COMPLETED", "Rollback on failure tested.")

        # 4. Render and verify completion
        md = orchestrate_dag.render_perspective_markdown(state_file)
        self.assertIn("**Completion**: 3/3 tasks completed", md)
        self.assertIn("`mig-1-checksum`", md)
        self.assertIn("`mig-3-runner`", md)

    def test_scenario_3_jwt_rbac_evaluator(self):
        """Scenario 3: Multi-Tenant JWT & RBAC Evaluator."""
        state_file = self.base_path / "jwt_rbac_perspective.json"

        # 1. Initialize perspective
        orchestrate_dag.init_perspective(
            state_file,
            project="Multi-Tenant Auth Engine",
            objective="Cryptographic verification of tenant JWTs and fine-grained RBAC.",
        )

        # 2. Decompose into tasks
        orchestrate_dag.add_task(
            state_file,
            task_id="auth-1-decode",
            title="JWT Unpack & Validation",
            spec="Extract claims, verify expiry (exp) and not-before (nbf) timestamps.",
        )
        orchestrate_dag.add_task(
            state_file,
            task_id="auth-2-sig",
            title="RS256 Signature Verification",
            spec="Verify cryptographic signature against tenant JWKS public keys.",
            depends_on=["auth-1-decode"],
        )
        orchestrate_dag.add_task(
            state_file,
            task_id="auth-3-rbac",
            title="Role-Based Access Policy Engine",
            spec="Match tenant roles against requested resource and action.",
            depends_on=["auth-2-sig"],
        )

        # 3. Clarification gate
        orchestrate_dag.record_clarification(
            state_file,
            question="What is the allowed clock skew tolerance for timestamp verification?",
            answer="Allow 60 seconds clock skew tolerance.",
        )

        orchestrate_dag.update_task(state_file, "auth-1-decode", "COMPLETED", "Validated with 60s clock skew.")
        orchestrate_dag.update_task(state_file, "auth-2-sig", "COMPLETED", "RS256 validated.")
        orchestrate_dag.update_task(state_file, "auth-3-rbac", "COMPLETED", "RBAC policy tree certified.")

        md = orchestrate_dag.render_perspective_markdown(state_file)
        self.assertIn("Multi-Tenant Auth Engine", md)
        self.assertIn("Allow 60 seconds clock skew tolerance.", md)
        self.assertIn("**Completion**: 3/3 tasks completed", md)


if __name__ == "__main__":
    unittest.main()
