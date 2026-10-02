# Nexvion CI/CD Pipeline & DevSecOps Platform Specification (Phase 2 Hardened)

## Architecture & Lifecycle Environments

This pipeline architecture establishes three distinct operational scopes:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. LOCAL VALIDATION (Developer Workstation - Executed & Verified)                      │
│    - Manual CLI execution: docker build, docker compose, gitleaks, trivy, curl checks  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. LIVE JENKINS EXECUTION (Automated CI/CD Pipeline - Phase 2 Configured)              │
│    - Declarative Jenkinsfile on Linux Runner Agent (`label 'linux'`)                   │
│    - Automated Gates: Code Validation ➔ GitLeaks ➔ Docker Build ➔ Trivy ➔ Staging     │
│    - Note: Pipeline syntax verified; live execution triggers upon Jenkins job run.    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. INFRASTRUCTURE & CONFIG MANAGEMENT (Phase 3 Implemented)                            │
│    - Infrastructure as Code (Phase 3 Terraform) + Ansible Configuration                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. FUTURE KUBERNETES & CLOUD PLATFORM (Phase 4 Target - Future Scope)                  │
│    - Amazon EKS + Helm Chart Rolling Updates with Immutable Git SHA Tags (Phase 4)     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Target Agent Environment
- **Intended Jenkins Runner:** Linux Agent (Ubuntu / Alpine / Amazon Linux) with Docker socket access.
- **Node Label:** `label 'linux'`
- **Shell Executor:** Standard Linux `/bin/sh` (POSIX compliant). No Windows-specific CMD/PowerShell steps required in Jenkinsfile.

---

## AWS ECR Authentication Strategy (Phase 2 vs Future Phase 4 Scope)

> [!NOTE]
> **Phase 2 / Phase 3 Local & Staging Pipeline Strategy:**
> For local testing and current staging pipelines (`REGISTRY_TYPE = 'LOCAL_ONLY'`), image building and staging deployments occur locally on the EC2 host via Docker Compose without requiring external registry credentials.
>
> **Future Production Strategy (IAM Roles & IRSA - Phase 4 Scope):**
> In Phase 4 (Kubernetes EKS deployment), static credentials can be replaced by IAM Instance Profiles or IRSA (IAM Roles for Service Accounts) using short-lived tokens generated via `aws ecr get-login-password --region ap-south-1`.

---

## Container Registry Defaults & Safety Controls

- **Default Parameters:**
  - `REGISTRY_TYPE`: `'LOCAL_ONLY'` (Prevents fresh default Jenkins jobs from attempting to push to placeholder ECR URIs).
  - `PUSH_TO_REGISTRY`: `false` (Must be explicitly enabled when real ECR URI and credentials are present).
- **Supported Targets:** `LOCAL_ONLY` (Default), `AWS_ECR` (Production target), `DOCKER_HUB`.

---

## Image Tagging Strategy & Kubernetes Best Practices

- **Primary Immutable Tag (Git SHA):** `${APP_NAME}:${GIT_COMMIT_SHORT}` (e.g., `nexvion-web:a1b2c3d`)
  - **Rationale:** Guarantees deterministic, traceable, and audit-compliant deployments.
- **Secondary Tags:** `${APP_NAME}:${BUILD_NUMBER}` and `${APP_NAME}:latest`.
- **Kubernetes Deployment Rule (Phase 4 Requirement):** Production Kubernetes manifests and Helm charts MUST use immutable Git SHA image tags (`nexvion-web:a1b2c3d`) rather than `:latest` to prevent untracked drift, ensure atomic rollbacks, and guarantee pod immutability.

---

## Pinned DevSecOps Scanner Tool Versions

| Scanner Tool | Pinned Version Tag | Execution Command | Hard Security Gate Behavior |
| :--- | :--- | :--- | :--- |
| **GitLeaks** | `zricethezav/gitleaks:v8.28.0` | `docker run --rm -v "${WORKSPACE}:/path" zricethezav/gitleaks:v8.28.0 detect --source="/path" -c="/path/.gitleaks.toml" --no-git -v` | **Fails pipeline immediately** if any plaintext password, AWS key, API key, or private token is detected. |
| **Trivy** | `aquasec/trivy:0.60.0` | `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.60.0 image --severity HIGH,CRITICAL --exit-code 1 ${IMAGE_TAG_COMMIT}` | **Fails pipeline immediately** if any `HIGH` or `CRITICAL` vulnerability exists. |

---

## GitLeaks Secret Scanner Configuration (`.gitleaks.toml`)

- **Strict Scanning Policy:** Broad directory exclusions (e.g., `docs/.*` or `README.md`) have been removed. All documentation, source code, and configuration files are scanned.
- **Scan Verification:** Verified clean locally across 782+ KB of codebase files (`0 leaks found`).

---

## Pipeline Stages Summary

1. **Checkout:** Clones repository, extracts Git SHA (`GIT_COMMIT_SHORT`).
2. **Validate:** Validates required files, runs Node.js syntax checks (`node -c`), tests `docker compose config`.
3. **Secret Scan:** Executes GitLeaks v8.28.0. Stops pipeline on detection.
4. **Docker Build:** Builds image tagged with Git SHA, Build Number, and Latest.
5. **Image Scan:** Executes Trivy 0.60.0. Stops pipeline if HIGH/CRITICAL CVEs are found.
6. **Registry Push:** Authenticates and pushes primary immutable Git SHA tag to AWS ECR (when enabled).
7. **Staging Deployment:** Deploys local staging container stack using Docker Compose (`docker compose up -d --force-recreate`). (Will be replaced by Kubernetes in Phase 4).
8. **Health Check:** Verifies HTTP GET `/healthz` (200 OK) and root `/` (200 OK). Stops pipeline on health failure.

---

## Required Jenkins Credentials

| Credential ID | Credential Type | Usage & Description |
| :--- | :--- | :--- |
| `ecr-credentials` | Username with Password | Temporary Phase 2 fallback AWS credentials (Access Key / Secret Key). Replaced by IAM Roles in Phase 3/4. |
| `docker-registry-credentials` | Username with Password | Docker Hub Username & Access Token (Optional). |
| `github-webhook-secret` | Secret text | Webhook payload signature secret. |

---

## Local Validation Commands

```bash
# 1. Validate JavaScript syntax
node -c script.js; node -c payment.js

# 2. Validate Docker Compose configuration
docker compose config

# 3. Execute GitLeaks Secret Scan (Pinned Version v8.28.0)
docker run --rm -v "${PWD}:/path" zricethezav/gitleaks:v8.28.0 detect --source="/path" -c="/path/.gitleaks.toml" --no-git -v

# 4. Build Docker Image (Using Git SHA as Primary Tag)
GIT_SHA=$(git rev-parse --short=7 HEAD)
docker build -t nexvion-web:${GIT_SHA} -t nexvion-web:latest .

# 5. Execute Trivy Vulnerability Scan (Pinned Version 0.60.0)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.60.0 image --severity HIGH,CRITICAL --exit-code 1 nexvion-web:${GIT_SHA}

# 6. Deploy Staging Stack
docker compose up -d --force-recreate

# 7. Verify Endpoint Health
curl -i http://localhost:8081/healthz
curl -i http://localhost:8081/
```