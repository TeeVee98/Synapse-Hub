---
name: docker-patterns
description: >
  Hardened container isolation skill: design production-grade Dockerfiles with
  minimal attack surface, non-root users, read-only filesystems, multi-stage builds,
  and security scanning gates. Use when writing or reviewing Dockerfile, docker-compose,
  or Kubernetes pod spec configurations.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# Docker Patterns Skill (`docker-patterns`)

## Overview

Production containers must be **minimal, non-privileged, and reproducible**. This skill enforces hardened Dockerfile patterns, multi-stage build separation, and mandatory security scanning gates before any container image ships to production.

> [!CAUTION]
> Never run production containers as root (UID 0). A container breakout from a
> root-running container grants full host access. This is a Severity.CRITICAL finding
> in SkillSpector (PE2 / PE5 rules).

## When to Activate

- Writing a new Dockerfile for a service or test runner image.
- Reviewing an existing Dockerfile for security or size issues.
- Designing docker-compose or Kubernetes pod specs.
- Setting up container image scanning in CI/CD.

## Hardened Dockerfile Template

```dockerfile
# ✅ Hardened Multi-Stage Dockerfile
# Stage 1: Build (can use full SDK image with build tools)
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime (minimal image, no build tools)
FROM python:3.12-slim AS runtime

# Never run as root — create dedicated non-root user
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy only the installed packages from builder (not build toolchain)
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup src/ ./src/

# Drop all Linux capabilities — grant only what is required
# (remove this line and add back specific caps if needed)
USER appuser

# Read-only root filesystem (mount tmpfs for writable paths)
# Set in docker run: --read-only --tmpfs /tmp

EXPOSE 8080
ENTRYPOINT ["python", "-m", "src.main"]
```

## Security Rules

### FORBIDDEN Patterns (SkillSpector PE1-PE5)

```dockerfile
# ❌ Running as root
USER root
# or missing USER directive entirely

# ❌ Mounting docker socket (container breakout)
# docker run -v /var/run/docker.sock:/var/run/docker.sock ...

# ❌ Privileged mode
# docker run --privileged ...

# ❌ Copying entire source tree (leaks secrets, .env, .git)
COPY . .  # FORBIDDEN — use explicit COPY of only required files

# ❌ Unpinned base image (supply chain risk)
FROM python:latest  # FORBIDDEN — always pin to digest or exact version tag
FROM python:3.12-slim  # OK but prefer digest pinning in production
```

### REQUIRED Patterns

```dockerfile
# ✅ Pin base image to SHA256 digest in production
FROM python:3.12-slim@sha256:abc123...

# ✅ Explicit non-root user
USER 10001:10001

# ✅ No new privileges
# Set in kubernetes securityContext:
#   allowPrivilegeEscalation: false
#   readOnlyRootFilesystem: true

# ✅ Minimal layer count — combine related RUN commands
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```

## Image Scanning Gate

Add to CI before any image push:

```yaml
# .github/workflows/docker.yml
- name: Scan image with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE_TAG }}
    format: sarif
    output: reports/trivy-results.sarif
    exit-code: "1"           # Fail CI on CRITICAL findings
    severity: CRITICAL,HIGH
```

## docker-compose Hardening

```yaml
# docker-compose.yml
services:
  api:
    image: synapse-hub-api:latest
    user: "10001:10001"
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only add specific capabilities if required
```

## Non-Goals

- Do not use `--privileged` for any test runner containers — use rootless Podman or Docker-in-Docker with strict socket mounting rules.
- Do not cache pip packages in the final runtime image layer.
- Do not store secrets in Dockerfile `ENV` instructions — use Docker secrets or external vaults.
