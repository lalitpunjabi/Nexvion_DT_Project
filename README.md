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
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. INFRASTRUCTURE & CONFIG MANAGEMENT (Phase 3 Implemented)                            │
│    - Terraform Infrastructure (`terraform/`): Adopts & manages existing VPC, Subnet,   │
│      IGW, Route Table, Security Group, EC2, Elastic IP, and EIP Association             │
│    - Ansible Configuration (`ansible/`): System hardening, Docker Engine, Jenkins      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. FUTURE KUBERNETES & CLOUD PLATFORM (Phase 4 Target)                                 │
│    - Amazon EKS + Helm Chart Rolling Updates with Immutable Git SHA Tags               │
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

## Phase 3 Overview: Infrastructure as Code & Configuration Management
- **Terraform Infrastructure:** [`terraform/`](terraform/) adopts and declaratively manages existing AWS infrastructure: VPC (`vpc-09df3f5fdabdcf81f`), Subnet (`subnet-048f480df580a47f8`), Internet Gateway (`igw-045a89bde29483b3a`), Route Table (`rtb-0b5c00adb98133d97`), Security Group (`sg-0e2c619a238e449df`), EC2 instance `i-057f6d6d0bbb33b37` (Tag Name: `Nexvion`, `t3.small`), Elastic IP (`52.66.25.69`, `eipalloc-0662e014367e516bf`), and EIP Association (`eipassoc-0dfe320300f89e0da`).
- **Ansible Server Configuration:** [`ansible/`](ansible/) playbooks and roles (`common`, `docker`, `jenkins`, `security`) automate system package management, Docker Engine setup, Jenkins LTS service, and server hardening (`sysctl`, UFW firewall).
- **Detailed Architecture Specification:** See [`docs/phase-3.md`](docs/phase-3.md) for full IaC architecture, Ansible role specifications, and execution instructions.

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

# 6. Validate Terraform Infrastructure Code
cd terraform && terraform fmt -check -recursive && terraform init && terraform validate && cd ..

# 7. Validate Ansible Configuration Playbooks
cd ansible && ansible-playbook -i inventory/hosts.ini playbooks/site.yml --syntax-check && cd ..

# 8. Deploy Local Staging Stack
docker compose up -d --force-recreate

# 9. Verify Endpoint Health
curl -i http://localhost:8081/healthz
curl -i http://localhost:8081/

# 10. Stop Container Stack (Optional Cleanup)
docker compose down
```

---

### Jenkins Credentials

The current Phase 2 default pipeline uses:

- `REGISTRY_TYPE=LOCAL_ONLY`
- `PUSH_TO_REGISTRY=false`

Therefore, external registry credentials are NOT required for the default staging pipeline.

| Credential ID | Type | Status | Usage |
| :--- | :--- | :--- | :--- |
| `docker-registry-credentials` | Username with Password | Optional | Docker Hub push when explicitly enabled |
| `github-webhook-secret` | Secret text | Optional | GitHub webhook authentication |
| `ecr-credentials` | Username with Password | Future/Optional | Only required if AWS ECR registry push is explicitly enabled |