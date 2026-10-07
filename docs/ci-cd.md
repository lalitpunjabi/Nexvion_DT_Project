# Nexvion CI/CD Pipeline & DevSecOps Platform Specification (Final Integrated Scope)

## Architecture & Lifecycle Environments

This pipeline architecture establishes the complete integrated operational delivery model:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. LOCAL VALIDATION (Developer Workstation - Executed & Verified)                      │
│    - Manual CLI execution: docker build, docker compose, gitleaks, trivy, curl checks  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. LIVE JENKINS EXECUTION (Automated End-to-End CI/CD Pipeline - Fully Implemented)     │
│    - Declarative Jenkinsfile on Jenkins Runner Agent                                  │
│    - Automated Gates: Code Audit ➔ GitLeaks ➔ Docker Build ➔ Trivy Scan ➔ ECR Push ➔ │
│      EKS Kubeconfig ➔ Helm Upgrade ➔ Rolling Update ➔ Health Verification ➔ Rollback   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. INFRASTRUCTURE & CONFIG MANAGEMENT (Terraform & Ansible Implemented)                 │
│    - Infrastructure as Code (Terraform) + System Configuration (Ansible)              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. CLOUD KUBERNETES DEPLOYMENT & OBSERVABILITY (Amazon EKS & Helm Implemented)          │
│    - Amazon EKS Cluster (`nexvion-eks` v1.36.4) + Helm 3 Rolling Updates + HPA +       │
│      Prometheus/Grafana Observability + ELK Logging + AI Incident Analyzer             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Target Agent Environment
- **Jenkins Runner:** Linux Agent / Built-in Node with Docker socket and AWS CLI access.
- **Shell Executor:** Standard Linux `/bin/sh` (POSIX compliant).

---

## AWS ECR & EKS Authentication Strategy

- **ECR Authentication:** Uses `aws ecr get-login-password --region ap-south-1` wrapped in `withCredentials` binding `ecr-credentials` (or host IAM Instance Profile fallback).
- **EKS Kubeconfig Generation:** Executes `aws eks update-kubeconfig --region ap-south-1 --name nexvion-eks` inside Stage 7.
- **Security Group Access:** EKS Cluster Security Group authorizes TCP port 443 inbound from the VPC CIDR (`172.31.0.0/16`), enabling `kubectl` control plane connectivity.

---

## Container Registry Parameters & Controls

- **Supported Registries:** `AWS_ECR` (Primary Cloud Target), `LOCAL_ONLY` (Development fallback).
- **Deployment Targets:** `EKS` (Primary Amazon EKS cluster), `LOCAL_DOCKER` (Staging fallback), `BOTH`.
- **Primary Parameters:**
  - `REGISTRY_TYPE`: `AWS_ECR`
  - `DEPLOY_TARGET`: `EKS`
  - `PUSH_TO_REGISTRY`: `true`
  - `DEPLOY_EKS`: `true`

---

## Image Tagging Strategy & Immutability Controls

- **Primary Immutable Tag (Git SHA):** `nexvion-web:${GIT_COMMIT_SHORT}` (e.g., `nexvion-web:4448d92`)
  - **Rationale:** Guarantees deterministic, traceable, and audit-compliant deployments.
- **Secondary Tags:** `${APP_NAME}:${BUILD_NUMBER}` and `${APP_NAME}:latest`.
- **Artifact Immutability:** Amazon ECR tag mutability configured as `IMMUTABLE` with AES256 server-side encryption.

---

## DevSecOps Scanner Tool Integration

| Scanner Tool | Pinned Version Tag | Execution Command | Hard Security Gate Behavior |
| :--- | :--- | :--- | :--- |
| **GitLeaks** | `zricethezav/gitleaks:v8.28.0` | `docker run --rm -v "${WORKSPACE}:/path" zricethezav/gitleaks:v8.28.0 detect --source="/path" -c="/path/.gitleaks.toml" --no-git -v` | **Fails pipeline immediately** if any plaintext password, AWS key, API key, or private token is detected. |
| **Trivy** | `aquasec/trivy:0.60.0` | `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.60.0 image --severity HIGH,CRITICAL --exit-code 1 ${IMAGE_TAG_COMMIT}` | **Fails pipeline immediately** if any `HIGH` or `CRITICAL` vulnerability exists. |

---

## Pipeline Stage Workflow

1. **Checkout & Metadata Discovery:** Clones repository, extracts short Git SHA (`GIT_COMMIT_SHA`).
2. **Validate & Dependency Security Scan:** Validates static workload files, runs JavaScript syntax checks (`node -c`), and validates Docker Compose structure.
3. **Secret Scan (GitLeaks):** Executes GitLeaks v8.28.0. Halts pipeline if hardcoded secrets are found.
4. **Docker Build:** Builds Docker image with tags `:GIT_SHA`, `:BUILD_NUMBER`, `:latest`.
5. **Container Security Gate (Trivy):** Executes Trivy 0.60.0 container vulnerability scan. Halts pipeline on `HIGH` or `CRITICAL` CVEs.
6. **Authenticate & Push to ECR:** Logins to AWS ECR and pushes immutable Git SHA image artifact.
7. **EKS Helm Deployment & Rolling Update:**
   - Authenticates `kubectl` to EKS (`nexvion-eks`).
   - Verifies namespace `nexvion` and attaches Helm ownership metadata (`app.kubernetes.io/managed-by: Helm`).
   - Runs `helm lint` and dry-run rendering.
   - Executes live `helm upgrade --install` with capacity-safe rolling update parameters (`maxSurge: 0, maxUnavailable: 1`).
   - Verifies rollout status (`kubectl rollout status --timeout=300s`).
   - Executes multi-level HTTP 200 health checks (pod-local + service routing).
   - Dynamic Automated Rollback: If rollout fails or times out, automatically executes `helm rollback` to previous deployed revision.
8. **Post Diagnostics & Summary:** Outputs workload summary and container diagnostic logs.

---

## Summary of Credentials

| Credential ID | Credential Type | Description |
| :--- | :--- | :--- |
| `ecr-credentials` | Username with Password | AWS Access Key ID (`AWS_ACCESS_KEY_ID`) and Secret Access Key (`AWS_SECRET_ACCESS_KEY`). |
| `github-nexvion-fine-grained` | Git Username & PAT | GitHub Fine-Grained PAT for repository checkout. |