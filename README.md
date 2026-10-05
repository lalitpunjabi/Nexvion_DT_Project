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
│ 4. KUBERNETES, HELM, ECR, EKS & WORKLOAD DEPLOYMENT (Phase 4.1 - 4.9 Implemented)      │
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
│    - Phase 4.6 Metrics, HPA & Ingress (`ingress-nginx`): Metrics Server running,       │
│      active CPU HPA metric calculation, and cost-conscious NodePort ingress routing     │
│    - Phase 4.7 Prometheus & Grafana Observability (`helm/monitoring/`): Prometheus     │
│      metrics scraper and Grafana platform overview dashboards verified live             │
│    - Phase 4.8 ELK Centralized Logging (`helm/logging/`): Fluent Bit, single-node       │
│      Elasticsearch, and Kibana log search/visualization validated end-to-end             │
│    - Phase 4.9 AI Incident Analysis (`tools/incident-analysis/`): Live telemetry       │
│      collector (K8s APIs, ES logs, PromQL), 12-rule classifier, & report engine         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. END-TO-END CI/CD PIPELINE INTEGRATION (Phase 5 Implemented & Validated)            │
│    - Automated Jenkins Delivery Pipeline (`Jenkinsfile`): GitHub ➔ Checkout ➔          │
│      Validation ➔ npm audit ➔ GitLeaks ➔ Docker Build (Git SHA) ➔ Trivy ➔ ECR Auth ➔  │
│      ECR Push ➔ EKS Auth ➔ Helm Dry-Run ➔ Helm Upgrade ➔ Rolling Update (maxSurge: 0) ➔ │
│      Rollout Status ➔ Endpoint Verification ➔ Diagnostics & Rollback Handling          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. FINAL INTEGRATION AUDIT, END-TO-END VALIDATION & PROJECT CLOSURE (Phase 6.1 - 6.3) │
│    - Phase 6.1 Final Audit: Zero blocking architecture, security, or implementation gaps │
│    - Phase 6.2 End-to-End Validation: 20-step validation across all system layers      │
│    - Phase 6.3 Final Project Closure: Demonstration runbook, viva Q&A, submission package│
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
- **Cost-Constrained Multi-AZ Networking:** Extends existing VPC (`vpc-09df3f5fdabdcf81f`) with a non-overlapping second public subnet (`aws_subnet.eks_public_a`, `172.31.48.0/20` in `ap-south-1a`), avoiding expensive NAT Gateway hourly and data-processing charges.
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
- **Application Endpoint Validation:** Internal HTTP validation via ClusterIP verified `/healthz` (200 OK), `/` (200 OK), `products.html` (200 OK), and `payment.html` (200 OK).
- **Detailed Specification:** See [`docs/phase-4.5-eks-deployment.md`](docs/phase-4.5-eks-deployment.md).

---

## Phase 4.6 Overview: EKS Observability Metrics, HPA Validation & Ingress External Access
- **Metrics Server Installed:** `metrics-server` deployed to `kube-system` namespace. Verified `kubectl top nodes` (`32m` CPU / `50%` RAM) and `kubectl top pods -n nexvion` (`1m` CPU per pod).
- **Active HPA Metric Validation:** `horizontalpodautoscaler/nexvion-web-hpa` active with real CPU metric calculation (`cpu: 1%/70%`, `ScalingActive = True`). Controlled load testing validated real CPU metric collection and HPA replica calculation.
- **Cost-Conscious Ingress Controller:** Installed `ingress-nginx` controller (v1.15.1) configured with `type: NodePort` (HTTP Port `31449`, HTTPS Port `31941`), avoiding creation of a separate AWS Load Balancer and associated hourly/data-processing charges.
- **Ingress Route & NodePort Validation:** Validated 200 OK responses for `/healthz`, `/`, `products.html`, and `payment.html` internally via ClusterIP and against the EKS worker node's private VPC IP (`172.31.59.164:31449`).
- **Detailed Specification:** See [`docs/phase-4-6-metrics-hpa-external-access.md`](docs/phase-4-6-metrics-hpa-external-access.md).

---

## Phase 4.7 Overview: Prometheus & Grafana Observability Foundation
- **Prometheus Deployed:** `prometheus-community/prometheus` (v27.5.0) deployed to namespace `monitoring` using existing EKS worker capacity with staging parameters (2d retention, `emptyDir` storage, 128Mi RAM request).
- **Grafana Deployed:** `grafana/grafana` (v10.5.15) deployed to namespace `monitoring` with declarative Prometheus datasource and pre-loaded `Nexvion EKS Platform Observability` dashboard.
- **PromQL Metrics Scraped & Validated:** Verified live collection for node CPU/RAM usage, `nexvion-web` pod CPU/RAM, deployment replicas (`2` available), HPA replicas (`2` current), and node readiness (`1` node ready).
- **Detailed Specification:** See [`docs/phase-4-7-prometheus-grafana.md`](docs/phase-4-7-prometheus-grafana.md).

---

## Phase 4.8 Overview: ELK Centralized Logging
- **Declarative Manifests & Values:** Maintained under `helm/logging/` using declarative Kubernetes manifests (`elk-stack.yaml`, `fluent-bit.yaml`).
- **Fluent Bit Deployed:** `fluent/fluent-bit` (v2.2.0) DaemonSet deployed in namespace `logging` with CRI log parsing and Kubernetes metadata enrichment.
- **Elasticsearch & Kibana Deployed:** Single-node Elasticsearch (7.17.18) and Kibana (7.17.18) deployed in namespace `logging` with low JVM heap limits (`-Xms128m -Xmx128m`) tailored for `t3.small` resource safety.
- **End-to-End Log Validation:** Generated workload logs verified ingested by Fluent Bit into Elasticsearch index `nexvion-logs-YYYY.MM.DD` and searchable via Kibana.
- **Detailed Specification:** See [`docs/phase-4-8-elk-centralized-logging.md`](docs/phase-4-8-elk-centralized-logging.md).

---

## Phase 4.9 Overview: AI-Assisted Incident Analysis
- **Incident Analysis Engine:** Client-side python/shell framework in `tools/incident-analysis/` that aggregates telemetry across K8s APIs, Elasticsearch REST APIs, and Prometheus PromQL metrics.
- **Classifier & Severity Engine:** Automatically categorizes incidents (`CrashLoopBackOff`, `Dependency Failure`, `High CPU`, etc.) and assigns severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`).
- **Dual-Mode Intelligence:** Supports Google Gemini AI (`AI-Assisted Analysis` when `AI_API_KEY` is provided) with a 100% offline, deterministic `Rule-Based Analysis` fallback.
- **Detailed Specification:** See [`docs/phase-4-9-ai-assisted-incident-analysis.md`](docs/phase-4-9-ai-assisted-incident-analysis.md).

---

## Phase 5 Overview: End-to-End CI/CD Integration & Hardened Rollback
- **Automated Delivery Pipeline:** [`Jenkinsfile`](Jenkinsfile) integrates all components into an 8-stage automated delivery flow connecting GitHub source control to Amazon EKS cluster deployments.
- **Capacity-Safe Rolling Update:** Tuned deployment strategy to `maxSurge: 0` and `maxUnavailable: 1` to strictly adhere to single `t3.small` EKS worker node capacity (`maxPods=11`).
- **Dynamic Automated Rollback:** Automatically extracts previous deployed Helm revision prior to upgrade, monitors rollout timeout (300s), collects diagnostics on failure, and executes `helm rollback`.
- **Detailed Specification:** See [`docs/phase-5-end-to-end-cicd.md`](docs/phase-5-end-to-end-cicd.md).

---

## Phase 6 Overview: Final Validation, Audit & Project Closure (Phases 6.1 – 6.3)
- **Phase 6.1 Final Integration Audit:** Audit verified zero blocking gaps in architecture, security, or implementation.
- **Phase 6.2 Final End-to-End Validation:** Verified 20 live validation steps across CI/CD, security scanning, container build, ECR, EKS, Helm, health probes, HPA, Prometheus, Grafana, ELK, AI analysis, and failure recovery ([docs/phase-6-2.md](docs/phase-6-2.md)).
- **Phase 6.3 Final Project Closure:** Prepared complete submission package including 20-step demonstration runbook ([docs/final-demo-runbook.md](docs/final-demo-runbook.md)), viva Q&A guide ([docs/viva-questions-and-answers.md](docs/viva-questions-and-answers.md)), and final project summary ([docs/final-project-summary.md](docs/final-project-summary.md)).

---

## Current Staging Limitations

The platform operates in a cost-constrained **staging environment** with the following explicit technical scope boundaries:
1. **Single Worker Node**: Deployed on a single EC2 `t3.small` instance (2 vCPUs, 2 GB RAM, `maxPods=11`).
2. **Capacity-Safe Rolling Update**: Uses `maxSurge: 0, maxUnavailable: 1` to prevent pod quota exhaustion.
3. **Internal NodePort Ingress**: Uses NGINX Ingress NodePort `31449` without an AWS Load Balancer (ALB/NLB) or Route 53 public DNS to eliminate hourly AWS fees.
4. **Single-Node Logging & Storage**: Elasticsearch and Prometheus use single-node staging parameters and `emptyDir` volumes.

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

# 10. Run AI Incident Analyzer on Staging Telemetry
python tools/incident-analysis/incident_analyzer.py --incident-id NEXVION-DEMO-001 --namespace nexvion --output-dir reports
```