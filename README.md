# Nexvion — AI-Powered E-Commerce DevOps & Cloud-Native Delivery Platform

## Lifecycle Environment Scopes

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. LOCAL VALIDATION (Developer Workstation - Executed & Verified)                      │
│    - CLI commands: docker build, docker compose, gitleaks, trivy, curl health checks   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. LIVE JENKINS EXECUTION (Automated CI/CD Pipeline - Phase 2 Configured)              │
│    - Declarative Jenkinsfile executed on Linux Runner Agent (`label 'linux'`)          │
│    - Automated Gates: Code Validation ➔ GitLeaks ➔ Docker Build ➔ Trivy ➔ Staging     │
│    - Note: Pipeline logic validated locally; triggers upon Jenkins SCM checkout.      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. FUTURE AWS/KUBERNETES DEPLOYMENT (Production Cloud Target - Phase 3 & 4)            │
│    - Terraform Infrastructure (Phase 3) + IAM Roles / IRSA for ECR authentication      │
│    - Amazon EKS + Helm Chart Rolling Updates with Immutable Git SHA Tags (Phase 4)     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 Overview: Containerization & Web Server Hardening
- **Runtime Base:** `nginx:alpine` running as non-root user `nginx` (UID 101).
- **Security Hardening:** Read-only root filesystem (`read_only: true`), `tmpfs` mounts on `/tmp`, `/var/cache/nginx`, and `/var/run`, `cap_drop: ALL`, `cap_add: NET_BIND_SERVICE`, `no-new-privileges:true`.
- **HTTP Security Headers:** `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy` (configured for Google Fonts, Unsplash images, placehold.co).
- **Health Check Endpoint:** Dedicated `/healthz` endpoint responding with `HTTP 200 OK`.

---

## Phase 2 Overview: Jenkins CI/CD & DevSecOps Pipeline (Hardened)
- **Declarative Pipeline:** [`Jenkinsfile`](Jenkinsfile) defines an 8-stage automated delivery pipeline targeting Linux runner agents (`label 'linux'`).
- **Code & Syntax Validation:** Validates required static workload files, JavaScript syntax (`node -c`), and Compose file structure (`docker compose config`).
- **Secret Scanning (GitLeaks):** Integrates [GitLeaks v8.28.0](.gitleaks.toml) to scan the codebase for hardcoded secrets, API keys, AWS keys, or private SSH keys. Broad doc exclusions are removed; all files are scanned.
- **Deterministic & Immutable Tagging:** Builds Docker images with primary immutable tag `nexvion-web:${GIT_COMMIT_SHORT}` (Git SHA), alongside secondary tags `${BUILD_NUMBER}` and `latest`.
- **Container Security Scanning (Trivy):** Integrates [Trivy 0.60.0](aquasec/trivy) container scanner with security gate enforcement (`--severity HIGH,CRITICAL --exit-code 1`).
- **Safe Registry Defaults:** Default execution parameters (`REGISTRY_TYPE = 'LOCAL_ONLY'`, `PUSH_TO_REGISTRY = false`) ensure fresh Jenkins builds run safely without failing on placeholder ECR URIs.
- **Health Verification:** Post-deployment verification checks `http://localhost:8081/healthz` (200 OK) and root web pages before declaring pipeline success.
- **Detailed Specification:** See [`docs/ci-cd.md`](docs/ci-cd.md) for full CI/CD architecture, plugin lists, credential mappings, and deployment scope documentation.

---

### Local Validation Commands

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

# 6. Deploy Local Staging Stack
docker compose up -d --force-recreate

# 7. Verify Endpoint Health
curl -i http://localhost:8081/healthz
curl -i http://localhost:8081/

# 8. Stop Container Stack (Optional Cleanup)
docker compose down
```

---

### Required Jenkins Credentials

| Credential ID | Type | Description | Target Stage |
| :--- | :--- | :--- | :--- |
| `ecr-credentials` | Username with Password | Temporary Phase 2 fallback AWS credentials (Replaced by IAM Roles / IRSA in Phase 3/4) | Stage 6: Registry Push |
| `docker-registry-credentials` | Username with Password | Docker Hub Username & Access Token (Optional) | Stage 6: Registry Push |
| `github-webhook-secret` | Secret text | Shared secret token for GitHub webhook payloads | SCM Trigger |