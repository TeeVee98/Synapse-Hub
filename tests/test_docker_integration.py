#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_docker_integration.py — Unit Tests for Enterprise Docker & CI/CD Integration
--------------------------------------------------------------------------------------
Validates the structural and semantic integrity of:
  1. Dockerfile (Base image, runtimes, env vars, global CLI install, entrypoint).
  2. .dockerignore (Exclusion of git, caches, node_modules, reports, env files).
  3. docker-compose.yml (Valid YAML, volume mounts, service definitions).
  4. .github/workflows/docker.yml (Valid YAML, GHCR publish on tags/releases, DoD gate).
  5. docs/CI_CD_INTEGRATION[.en].md (Docker CLI 1-liners, GitLab CI, Jenkins pipeline).
  6. UTF-8 No BOM compliance on all Docker and CI/CD artifacts.
"""

import os
import unittest
try:
    import yaml
except ImportError:
    yaml = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDockerIntegration(unittest.TestCase):
    """Verifies Docker container configuration and enterprise CI/CD integration."""

    def test_dockerfile_exists_and_valid(self):
        dockerfile_path = os.path.join(REPO_ROOT, "Dockerfile")
        self.assertTrue(os.path.isfile(dockerfile_path), "Dockerfile must exist at repository root")

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check Base Image
        self.assertRegex(
            content,
            r"FROM\s+(python:3\.12-slim-bookworm|node:20-bookworm-slim)",
            "Dockerfile must use an enterprise Debian bookworm base image"
        )

        # Check required runtimes & tools
        self.assertIn("default-jre-headless", content, "Dockerfile must install OpenJDK headless")
        self.assertIn("nodejs", content, "Dockerfile must install Node.js")
        self.assertIn("chromium", content, "Dockerfile must install Chromium")
        self.assertIn("git", content, "Dockerfile must install git")

        # Check required environment variables
        self.assertIn("PYTHONUNBUFFERED=1", content)
        self.assertIn("LANG=C.UTF-8", content)
        self.assertIn("LC_ALL=C.UTF-8", content)
        self.assertIn("DEBIAN_FRONTEND=noninteractive", content)
        self.assertIn("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium", content)

        # Check workspace & global install
        self.assertIn("WORKDIR /workspace", content)
        self.assertIn("npm install -g .", content)
        self.assertIn('ENTRYPOINT ["synapse-hub"]', content)
        self.assertIn('CMD ["--help"]', content)

        # Check Hermetic container baseline & non-root security (Giai đoạn 3 / P1)
        self.assertIn("@sha256:", content, "Dockerfile base image must be pinned with deterministic sha256 digest")
        self.assertIn("useradd -u 10001 -g synapse", content, "Dockerfile must create dedicated non-root user synapse (UID 10001)")
        self.assertIn("chown -R synapse:synapse", content, "Dockerfile must set non-root ownership on workspace & install dir")
        self.assertIn("USER synapse", content, "Dockerfile must switch to non-root USER synapse")
        self.assertIn("requirements.lock", content, "Dockerfile must install from hermetic requirements.lock")

        # Check author attribution & MIT License header
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("SPDX-License-Identifier: MIT", content)

    def test_dockerignore_exists_and_complete(self):
        dockerignore_path = os.path.join(REPO_ROOT, ".dockerignore")
        self.assertTrue(os.path.isfile(dockerignore_path), ".dockerignore must exist at repository root")

        with open(dockerignore_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        required_patterns = [
            ".git",
            "__pycache__",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "dist",
            "build",
            "reports",
            "Screenshots",
            "*.log",
            ".env*",
            "target",
        ]

        for pat in required_patterns:
            matched = any(line == pat or line.startswith(pat.rstrip("*")) for line in lines)
            self.assertTrue(matched, f".dockerignore must contain pattern: {pat}")

    def test_docker_compose_valid_yaml(self):
        compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
        self.assertTrue(os.path.isfile(compose_path), "docker-compose.yml must exist at repository root")

        if yaml is None:
            raise unittest.SkipTest("PyYAML is not installed in the environment")

        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIsInstance(data, dict)
        self.assertIn("services", data)
        services = data["services"]

        # Ensure all services exist
        for expected_srv in ["verify", "lint", "analyze", "mutate", "shell"]:
            self.assertIn(expected_srv, services, f"docker-compose.yml must declare '{expected_srv}' service")

        # Ensure target volume mount is configured
        verify_srv = services["verify"]
        volumes = verify_srv.get("volumes", [])
        self.assertTrue(
            any("./target:/workspace/target" in str(v) for v in volumes),
            "verify service must mount ./target to /workspace/target"
        )
        self.assertEqual(verify_srv.get("working_dir"), "/workspace/target")

        # Ensure shell service is configured for interactive developer access
        shell_srv = services["shell"]
        self.assertEqual(shell_srv.get("entrypoint"), ["/bin/bash"])
        self.assertEqual(shell_srv.get("command"), [])
        self.assertTrue(shell_srv.get("stdin_open"))
        self.assertTrue(shell_srv.get("tty"))

    def test_github_workflow_docker_valid_yaml(self):
        workflow_path = os.path.join(REPO_ROOT, ".github", "workflows", "docker.yml")
        self.assertTrue(os.path.isfile(workflow_path), ".github/workflows/docker.yml must exist")

        if yaml is None:
            raise unittest.SkipTest("PyYAML is not installed in the environment")

        with open(workflow_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIsInstance(data, dict)
        self.assertIn("jobs", data)
        jobs = data["jobs"]
        self.assertIn("verify", jobs, "Workflow must contain pre-publish verify job")
        self.assertIn("build-and-push", jobs, "Workflow must contain build-and-push job")

        # Check GHCR registry and image target
        with open(workflow_path, "r", encoding="utf-8") as f:
            raw = f.read()
        self.assertIn("ghcr.io", raw)
        self.assertIn("docker/build-push-action", raw)
        self.assertIn("Resolve Lowercase Repository Name", raw)

    def test_documentation_docker_examples(self):
        for doc_name in ["docs/CI_CD_INTEGRATION.md", "docs/CI_CD_INTEGRATION.en.md"]:
            doc_path = os.path.join(REPO_ROOT, doc_name)
            self.assertTrue(os.path.isfile(doc_path), f"{doc_name} must exist")

            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("ghcr.io/teevee98/synapse-hub:latest", content)
            self.assertIn("docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub verify", content)
            self.assertIn("docker compose run --rm verify", content)
            self.assertIn("GitLab CI", content)
            self.assertIn("Jenkins", content)

    def test_cli_launcher_passthrough_commands(self):
        launcher_path = os.path.join(REPO_ROOT, "bin", "agent-qa.js")
        self.assertTrue(os.path.isfile(launcher_path), "bin/agent-qa.js launcher must exist")

        with open(launcher_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("PASSTHROUGH_CMDS", content)
        for cmd in ["sh", "bash", "cat"]:
            self.assertIn(f"'{cmd}'", content)

    def test_utf8_no_bom_on_all_new_files(self):
        new_files = [
            "Dockerfile",
            ".dockerignore",
            "docker-compose.yml",
            ".github/workflows/docker.yml",
            "docs/CI_CD_INTEGRATION.md",
            "docs/CI_CD_INTEGRATION.en.md",
            "tests/test_docker_integration.py",
            "requirements-dev.txt",
            "requirements.lock",
        ]
        for rel_path in new_files:
            abs_path = os.path.join(REPO_ROOT, rel_path)
            self.assertTrue(os.path.isfile(abs_path), f"File {rel_path} must exist")
            with open(abs_path, "rb") as f:
                header = f.read(3)
                self.assertNotEqual(header, b"\xef\xbb\xbf", f"File {rel_path} must not contain UTF-8 BOM bytes")


if __name__ == "__main__":
    unittest.main()
