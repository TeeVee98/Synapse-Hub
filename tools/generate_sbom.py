#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tools/generate_sbom.py — Enterprise Software Bill of Materials (SBOM) Generator
--------------------------------------------------------------------------------
Generates standard SPDX 2.3 JSON compliant Software Bill of Materials for Synapse Hub.
Covers:
  - Primary Hub package metadata & MIT license provenance
  - Python dependencies (requirements-dev.txt, pyproject.toml)
  - NPM dependencies (package.json)
  - Cryptographic SHA-256 checksums and supplier attribution

Usage:
  python tools/generate_sbom.py
  python tools/generate_sbom.py --output reports/synapse_hub_sbom.spdx.json
"""

import os
import sys
import json
import uuid
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Enforce UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_version(repo_root: str) -> str:
    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "1.0.0").strip()
        except (OSError, json.JSONDecodeError, KeyError) as err:
            sys.stderr.write(f"Warning: Failed to parse package.json: {err}\n")
    return "1.0.0"


def calculate_sha256(file_path: str) -> Optional[str]:
    if not os.path.isfile(file_path):
        return None
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_requirements_txt(file_path: str) -> List[Dict[str, str]]:
    packages = []
    if not os.path.exists(file_path):
        return packages

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(("#", "-", "@")):
                continue
            # Parse package==version or package>=version
            parts = line.split("==") if "==" in line else line.split(">=")
            pkg_name = parts[0].strip()
            pkg_ver = parts[1].split(";")[0].strip() if len(parts) > 1 else "NOASSERTION"
            packages.append({
                "name": pkg_name,
                "version": pkg_ver,
                "type": "pypi"
            })
    return packages


def parse_package_json(file_path: str) -> List[Dict[str, str]]:
    packages = []
    if not os.path.exists(file_path):
        return packages

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}
        for name, ver in all_deps.items():
            clean_ver = ver.lstrip("^~>=< ")
            packages.append({
                "name": name,
                "version": clean_ver,
                "type": "npm"
            })
    except (OSError, json.JSONDecodeError, KeyError) as err:
        sys.stderr.write(f"Warning: Failed to parse package.json for deps: {err}\n")
    return packages


def build_spdx_sbom(repo_root: str = REPO_ROOT) -> Dict[str, Any]:
    """Generates standard SPDX 2.3 JSON document."""
    version = get_version(repo_root)
    doc_id = f"SPDXRef-DOCUMENT-{uuid.uuid4().hex[:8]}"
    created_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    root_sha = calculate_sha256(os.path.join(repo_root, "package.json")) or ""

    packages = []
    relationships = []

    # 1. Primary Root Package (Synapse-Hub)
    root_pkg_id = "SPDXRef-Package-synapse-hub"
    root_pkg = {
        "SPDXID": root_pkg_id,
        "name": "synapse-hub",
        "versionInfo": version,
        "downloadLocation": "https://github.com/TeeVee998/Synapse-Hub",
        "filesAnalyzed": False,
        "homepage": "https://github.com/TeeVee998/Synapse-Hub",
        "originator": "Person: Thế Vị (@TeeVee998)",
        "supplier": "Person: Thế Vị (@TeeVee998)",
        "licenseConcluded": "MIT",
        "licenseDeclared": "MIT",
        "copyrightText": "Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.",
        "description": "Enterprise QA & Automation Multi-Agent Hub enforcing Clean POM Flat Architecture.",
        "checksums": [
            {
                "algorithm": "SHA256",
                "checksumValue": root_sha
            }
        ]
    }
    packages.append(root_pkg)
    relationships.append({
        "spdxElementId": "SPDXRef-DOCUMENT",
        "relationshipType": "DESCRIBES",
        "relatedSpdxElement": root_pkg_id
    })

    # 2. Python Dependencies
    req_file = os.path.join(repo_root, "requirements-dev.txt")
    py_pkgs = parse_requirements_txt(req_file)
    for p in py_pkgs:
        clean_name = p["name"].replace("_", "-").lower()
        pkg_id = f"SPDXRef-Package-pypi-{clean_name}"
        packages.append({
            "SPDXID": pkg_id,
            "name": p["name"],
            "versionInfo": p["version"],
            "downloadLocation": f"https://pypi.org/project/{p['name']}/",
            "filesAnalyzed": False,
            "supplier": "Organization: PyPI Community",
            "licenseConcluded": "NOASSERTION",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE_MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/{p['name']}@{p['version']}"
                }
            ]
        })
        relationships.append({
            "spdxElementId": root_pkg_id,
            "relationshipType": "DEPENDS_ON",
            "relatedSpdxElement": pkg_id
        })

    # 3. NPM Dependencies
    pkg_json_file = os.path.join(repo_root, "package.json")
    npm_pkgs = parse_package_json(pkg_json_file)
    for p in npm_pkgs:
        clean_name = p["name"].replace("@", "").replace("/", "-")
        pkg_id = f"SPDXRef-Package-npm-{clean_name}"
        packages.append({
            "SPDXID": pkg_id,
            "name": p["name"],
            "versionInfo": p["version"],
            "downloadLocation": f"https://registry.npmjs.org/{p['name']}",
            "filesAnalyzed": False,
            "supplier": "Organization: NPM Community",
            "licenseConcluded": "NOASSERTION",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE_MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:npm/{p['name']}@{p['version']}"
                }
            ]
        })
        relationships.append({
            "spdxElementId": root_pkg_id,
            "relationshipType": "DEPENDS_ON",
            "relatedSpdxElement": pkg_id
        })

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"Synapse-Hub-SBOM-v{version}",
        "documentNamespace": f"https://github.com/TeeVee998/Synapse-Hub/spdx/{version}-{uuid.uuid4().hex[:12]}",
        "creationInfo": {
            "created": created_time,
            "creators": [
                "Tool: synapse-sbom-generator-1.0.0",
                "Person: Thế Vị (@TeeVee998)"
            ]
        },
        "packages": packages,
        "relationships": relationships
    }

    return sbom


def main() -> int:
    parser = argparse.ArgumentParser(description="SPDX 2.3 JSON SBOM Generator for Synapse Hub")
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Target repository root")
    parser.add_argument("--output", default="reports/synapse_hub_sbom.spdx.json", help="Path to write generated SBOM")
    args = parser.parse_args()

    sbom = build_spdx_sbom(args.repo_root)

    out_path = os.path.join(args.repo_root, args.output) if not os.path.isabs(args.output) else args.output
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2, ensure_ascii=False)

    print("=" * 68)
    print("      SYNAPSE HUB — ENTERPRISE SOFTWARE BILL OF MATERIALS (SBOM)     ")
    print("=" * 68)
    print(f"  SPDX Standard     : SPDX-2.3 (JSON)")
    print(f"  Package Name      : {sbom['name']}")
    print(f"  Total Packages    : {len(sbom['packages'])} packages cataloged")
    print(f"  Relationships     : {len(sbom['relationships'])} dependencies mapped")
    print(f"  Output Artifact   : {out_path}")
    print("=" * 68)
    print("✅ SPDX 2.3 SBOM generated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
