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
│ 4. KUBERNETES, HELM, ECR, EKS & WORKLOAD DEPLOYMENT (Phase 4.1 - 4.5 Implemented)      │
│    - Phase 4.1 Raw Manifests (`kubernetes/`): Namespace, ConfigMap, Secret,            │
│      Deployment, Service, Ingress, HPA (Validated on Minikube)                          │
│    - Phase 4.2 Helm Packaging (`helm/nexvion-web/`): Templated Helm 3 Chart with      │
│      values-dev.yaml & values-prod.yaml (Verified deployed & running on Minikube)      │
│    - Phase 4.3 ECR Container Registry (`terraform/main.tf`): Immutable `nexvion-web`  │
│      ECR repository, AES256 encryption, scan-on-push, and 7-day untagged lifecycle     │
│    - Phase 4.4 EKS Infrastructure (`terraform/main.tf`): Amazon EKS cluster            │
│      `nexvion-eks` (v1.36), managed node group (t3.small), IAM roles, multi-AZ         │
│    - Phase 4.5 EKS Workload Deployment (`helm/nexvion-web/`): Helm release deployed to  │
│      EKS pulling ECR image `0d575d0` (2/2 Ready pods, ClusterIP Service, health 200)   │
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

---

## Phase 4.1 Overview: Raw Kubernetes Manifests
- **Kubernetes Manifest Stack:** [`kubernetes/`](kubernetes/) provides baseline, production-ready manifests (`namespace.yaml`, `configmap.yaml`, `secret.yaml`, `deployment.yaml`, `service.yaml`, `ingress.yaml`, `hpa.yaml`).
- **Detailed Specification:** See [`kubernetes/README.md`](kubernetes/README.md).

---

## Phase 4.2 Overview: Helm Chart Packaging
- **Helm Chart Structure:** [`helm/nexvion-web/`](helm/nexvion-web/) encapsulates the Kubernetes manifests into a modular, reusable Helm 3 chart:
  - `Chart.yaml`: Metadata (name: `nexvion-web`, version: `0.1.0`, appVersion: `1.0.0`).
  - `values.yaml`: Centralized default values and container hardening specs.
  - `values-dev.yaml`: Local development overrides targeting Minikube image `nexvion-web:v1.0.0`.
  - `values-prod.yaml`: EKS production overrides targeting ECR repository placeholders and Git SHA tags.
  - `templates/_helpers.tpl`: Standard Helm label, naming, and selector helpers.
  - `templates/`: Parameterized templates for Namespace, ConfigMap, Secret, Deployment, Service, Ingress, and HPA.
- **Detailed Specification:** See [`helm/nexvion-web/README.md`](helm/nexvion-web/README.md).

---

## Phase 4.3 Overview: Amazon ECR Container Registry
- **Amazon ECR Resource:** `aws_ecr_repository.nexvion` (`nexvion-web`) managed via Terraform in `ap-south-1`.
- **Tag Mutability:** `IMMUTABLE` mode enforced to prevent image tag tampering or overwriting.
- **Scanning & Encryption:** Native image scan-on-push enabled; AES256 server-side encryption enabled at rest.
- **Lifecycle Policy:** `aws_ecr_lifecycle_policy.nexvion` automatically purges untagged images >7 days old and retains the 30 most recent tagged releases.
- **Trivy-Before-Push Workflow:** Image scanning via Trivy `0.60.0` enforced before pushing to ECR; vulnerable builds are blocked at the security gate.
- **Jenkins Integration:** `Jenkinsfile` Stage 6 supports `AWS_ECR` registry push via short-lived AWS CLI token authentication (`aws ecr get-login-password`), preserving local staging defaults (`LOCAL_ONLY`).
- **Detailed Specification:** See [`docs/phase-4-3.md`](docs/phase-4-3.md).

---

## Phase 4.4 Overview: Amazon EKS Cluster & Managed Node Group Infrastructure (Cost-Constrained Staging)
- **EKS Cluster Resource:** `aws_eks_cluster.nexvion` (`nexvion-eks`, Kubernetes `1.36` Standard Support) in `ap-south-1`.
- **Managed Node Group:** `aws_eks_node_group.nexvion` (`nexvion-node-group`, 1x `t3.small` instance initial deployment, scaling min:1, max:2).
- **Cost-Constrained Multi-AZ Networking:** Extends existing VPC (`vpc-09df3f5fdabdcf81f`) with a non-overlapping second public subnet (`aws_subnet.eks_public_a`, `172.31.48.0/20` in `ap-south-1a`), avoiding expensive NAT Gateway charges ($0.00 extra NAT GW cost).
- **Account-Aware Cost Disclosures:** EKS Control Plane ($0.10/hr, ~$73/mo) is **not covered by Free Tier**; EC2 worker nodes (`t3.small`) are potentially billable. Cluster is provisioned on-demand.
- **IAM Security:** Dedicated roles (`nexvion-eks-cluster-role`, `nexvion-eks-node-group-role`) with `AmazonEKSClusterPolicy`, `AmazonEKSWorkerNodePolicy`, `AmazonEKS_CNI_Policy`, and `AmazonEC2ContainerRegistryReadOnly`.
- **Zero Destruction Guarantee:** Verified via `terraform plan` (13 to add, 0 to change, 0 to destroy). Existing EC2, EIP, VPC, subnet, IGW, SG, and ECR preserved untouched.
- **Detailed Specification:** See [`docs/phase-4-4.md`](docs/phase-4-4.md).

---

## Phase 4.5 Overview: Amazon EKS Workload Deployment & Application Health Validation
- **Helm Release Deployed:** `nexvion-web` deployed to namespace `nexvion` on live AWS EKS cluster (`nexvion-eks` v1.36.4).
- **ECR Image Artifact:** `677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web:0d575d0` (Git SHA tag `0d575d0`).
- **Workload Status:** `deployment.apps/nexvion-web` with 2/2 Ready running pods, UID/GID 101 non-root, read-only root filesystem.
- **Service & Networking:** ClusterIP Service (`service/nexvion-web-service` on port 80/TCP) serving internally.
- **Ingress Controller Status:** Ingress resource declared, but Ingress Controller is **currently not installed**; external traffic routing is deferred to Phase 4.6 (external access is currently not functional).
- **HPA Status:** HPA is configured and deployed (2–5 replicas, 70% CPU target); CPU-based autoscaling requires Metrics Server, which is intentionally deferred to a later phase.
- **Secret Management Status:** Kubernetes Secret contains **placeholder values only** (`API_KEY_PLACEHOLDER`, `SESSION_SECRET_PLACEHOLDER`) and is not production secret management (AWS Secrets Manager / ESO deferred).
- **Application Endpoint Validation:** Internal HTTP validation via ClusterIP verified `/healthz` (200 OK), `/` (200 OK), `products.html` (200 OK), and `payment.html` (200 OK).
- **Detailed Specification:** See [`docs/phase-4.5-eks-deployment.md`](docs/phase-4.5-eks-deployment.md).

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

# 8. Validate Kubernetes Manifest Syntax
kubectl apply --dry-run=client -f kubernetes/

# 9. Lint & Render Helm Chart
helm lint helm/nexvion-web
helm template nexvion-web helm/nexvion-web -f helm/nexvion-web/values-dev.yaml

# 10. Install Helm Release on Minikube
helm install nexvion-web helm/nexvion-web -f helm/nexvion-web/values-dev.yaml --namespace nexvion --create-namespace

# 11. Deploy Local Staging Stack (Docker Compose)
docker compose up -d --force-recreate

# 12. Verify Endpoint Health
curl -i http://localhost:8081/healthz
curl -i http://localhost:8081/

# 11. Stop Container Stack (Optional Cleanup)
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