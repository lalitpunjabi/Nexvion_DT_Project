# Nexvion DevOps Platform — Final Demonstration Runbook (Viva & Technical Demo)

This document provides a step-by-step, interactive demonstration guide for evaluators, instructors, and technical examiners. It walks through the complete Nexvion AI-Powered E-Commerce DevOps & Cloud-Native Delivery Platform in logical sequence from source repository to live AWS EKS deployment, multi-layer observability, centralized logging, AI incident analysis, and failure recovery.

---

## Technical Prerequisites & Terminal Setup

Before starting the demonstration, open two terminal windows on the workstation:
- **Terminal 1**: PowerShell / Bash connected to AWS CLI and `kubectl` context set to `nexvion-eks` (`aws eks update-kubeconfig --region ap-south-1 --name nexvion-eks`).
- **Terminal 2**: Local repository root (`c:\Users\Lalit Punjabi\Nexvion_DT_Project`).

---

## 20-Step Viva & Technical Demonstration Sequence

### Step 1 — Show GitHub Repository
- **Objective**: Demonstrate source control structure and version control hygiene.
- **Action**: Open GitHub repository `https://github.com/lalitpunjabi/Nexvion_DT_Project.git`.
- **Key Points**:
  - Main branch is protected and clean.
  - Show directory organization: `terraform/`, `ansible/`, `kubernetes/`, `helm/`, `tools/incident-analysis/`, `scripts/`, `docs/`.
  - Point out `.gitignore` ensuring `.env` and sensitive files are strictly un-tracked.

### Step 2 — Show Project Architecture
- **Objective**: Explain the end-to-end cloud-native architecture.
- **Action**: Refer to the architecture block diagram in [README.md](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/README.md) or [docs/final-project-summary.md](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/docs/final-project-summary.md).
- **Key Points**:
  - Full flow: `GitHub -> Jenkins -> Validation & Scans -> Docker Build -> Trivy -> AWS ECR -> AWS EKS -> Helm Rolling Update -> Prometheus/Grafana -> ELK -> AI Incident Analyzer`.

### Step 3 — Show Jenkinsfile
- **Objective**: Demonstrate declarative CI/CD pipeline definition.
- **Action**: Open [Jenkinsfile](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/Jenkinsfile).
- **Key Points**:
  - 8 declarative stages: Checkout, App Validation, Dependency Audit, GitLeaks Secret Scan, Docker Build, Trivy Image Scan, ECR Authentication & Push, EKS & Helm Deployment with Health Check and Dynamic Rollback handling.
  - Parameterized for both `LOCAL_ONLY` staging and `AWS_ECR` + `EKS` live deployment.

### Step 4 — Trigger / Show Jenkins Pipeline Execution
- **Objective**: Demonstrate automated CI/CD execution.
- **Action**: Open Jenkins dashboard UI (`http://localhost:8080`) or review Build #5 stage log summary.
- **Key Points**:
  - Show stage execution timeline.
  - Point out Git commit SHA (`685f1c1`) carried as the primary immutable build tag throughout the pipeline.

### Step 5 — Show Security Scan Results
- **Objective**: Prove DevSecOps security gate enforcement.
- **Action**: Show Jenkins console logs or local terminal execution output for:
  - `npm audit`: `0 vulnerabilities`
  - `gitleaks`: `0 leaks found` (post-allowlist configuration in `.gitleaks.toml`)
  - `trivy image`: `0 HIGH / 0 CRITICAL` vulnerabilities on `nginx:alpine` base image.

### Step 6 — Show ECR Image Artifact
- **Objective**: Verify immutable container artifact storage in AWS ECR.
- **Action**: Run AWS CLI command:
  ```bash
  aws ecr describe-images --region ap-south-1 --repository-name nexvion-web --output table
  ```
- **Key Points**:
  - Immutable image tag `685f1c1` stored with digest `sha256:1a8dc151b7538ecb476eb3ceceac2f0bf26f1dfc5039f6fb2aee050d24fa93bc`.
  - AES256 server-side encryption and scanOnPush enabled.

### Step 7 — Show EKS Cluster & Worker Node
- **Objective**: Verify live AWS EKS cluster and worker node state.
- **Action**: Run:
  ```bash
  aws eks describe-cluster --region ap-south-1 --name nexvion-eks --query 'cluster.{name:name,status:status,version:version}' --output table
  kubectl get nodes -o wide
  ```
- **Key Points**:
  - Cluster `nexvion-eks` status `ACTIVE`, Kubernetes version `1.36`.
  - Single worker node `ip-172-31-59-164` running Kubernetes `v1.36.4` on `t3.small` instance.

### Step 8 — Show Helm Release State
- **Objective**: Demonstrate Helm 3 release management.
- **Action**: Run:
  ```bash
  helm status nexvion-web -n nexvion
  helm get values nexvion-web -n nexvion
  ```
- **Key Points**:
  - Status `deployed`, Chart `nexvion-web-0.1.0`, Revision 5.
  - Configured with `environment: staging` and capacity-safe rolling update strategy (`maxSurge: 0, maxUnavailable: 1`).

### Step 9 — Show Running Workload Pods
- **Objective**: Prove application container availability and security context.
- **Action**: Run:
  ```bash
  kubectl get pods -n nexvion -o wide
  ```
- **Key Points**:
  - 2/2 pods `nexvion-web-6968cb9fbf-xbm9n` and `nexvion-web-6968cb9fbf-z2f9f` in `Running` state.
  - Pods run as non-root user `nginx` (UID 101) with read-only root filesystem.

### Step 10 — Show Kubernetes Service
- **Objective**: Verify cluster-internal Service abstraction.
- **Action**: Run:
  ```bash
  kubectl get svc nexvion-web-service -n nexvion
  ```
- **Key Points**:
  - ClusterIP Service at `10.100.27.163:80`, routing traffic to active pod endpoints.

### Step 11 — Show Horizontal Pod Autoscaler (HPA)
- **Objective**: Demonstrate autoscaling metrics integration.
- **Action**: Run:
  ```bash
  kubectl get hpa nexvion-web-hpa -n nexvion
  kubectl top pods -n nexvion
  ```
- **Key Points**:
  - Active CPU metric calculation (`1%/70%`), target CPU 70%, 2 min / 5 max replicas.
  - Replicas stay stable at minimum 2 during normal low-traffic staging conditions.

### Step 12 — Show Level 1 Pod Health Endpoint
- **Objective**: Verify container health check API.
- **Action**: Execute local container probe:
  ```bash
  kubectl exec -n nexvion deploy/nexvion-web -c nexvion-web -- curl -s http://localhost:80/healthz
  ```
- **Key Points**:
  - Returns `{"status":"UP","environment":"staging"}` with `HTTP 200 OK`.

### Step 13 — Show Level 3 Ingress NodePort Access
- **Objective**: Demonstrate external cluster routing via NGINX Ingress Controller.
- **Action**: Run internal NodePort HTTP request against worker IP:
  ```bash
  curl -i http://172.31.59.164:31449/healthz
  curl -i http://172.31.59.164:31449/
  ```
- **Key Points**:
  - HTTP NodePort `31449` routes to `nexvion-web-ingress` with `HTTP 200 OK`.
  - Cost-conscious design avoids AWS ALB hourly fees for staging environment.

### Step 14 — Show Prometheus Metrics
- **Objective**: Validate Prometheus metric scraping.
- **Action**: Run PromQL check via kubectl:
  ```bash
  kubectl exec -n monitoring deploy/prometheus-server -c prometheus-server -- \
    curl -s "http://localhost:9090/api/v1/query?query=kube_deployment_status_replicas_available"
  ```
- **Key Points**:
  - Confirms Prometheus is actively scraping Kubernetes API and node metrics.

### Step 15 — Show Grafana Platform Dashboard
- **Objective**: Demonstrate visual platform observability.
- **Action**: Explain Grafana setup (`http://grafana.monitoring.svc.cluster.local:80`).
- **Key Points**:
  - Dashboard `Nexvion EKS Platform Observability` visualizes node readiness, pod replicas, CPU/memory consumption, and restart rates in real time.

### Step 16 — Show Centralized Logs in Elasticsearch
- **Objective**: Prove log collection by Fluent Bit and indexing in Elasticsearch.
- **Action**: Run log index search:
  ```bash
  kubectl exec -n logging deploy/elk -c elasticsearch -- \
    curl -s "http://localhost:9200/_cat/indices?v"
  ```
- **Key Points**:
  - Displays active indices `nexvion-logs-2026.10.05` storing JSON-formatted application and HTTP access logs.

### Step 17 — Show Kibana Interface & Index Pattern
- **Objective**: Demonstrate log visualization and search.
- **Action**: Explain Kibana interface (`http://kibana.logging.svc.cluster.local:5601`).
- **Key Points**:
  - Status `green`, index pattern `nexvion-logs-*` allows full-text log search and filtering by pod name, container, or namespace.

### Step 18 — Run AI Incident Analysis Engine
- **Objective**: Execute automated AI incident analysis on live telemetry.
- **Action**: Run in Terminal 2:
  ```bash
  python tools/incident-analysis/incident_analyzer.py --incident-id NEXVION-DEMO-001 --namespace nexvion --output-dir reports
  ```
- **Key Points**:
  - Collects K8s state, Elasticsearch logs, and Prometheus metrics automatically.
  - Invokes Google Gemini AI (`gemini-flash-lite-latest`) for intelligent root cause identification and remediation planning.

### Step 19 — Show Generated Incident Reports
- **Objective**: Demonstrate structured output artifacts.
- **Action**: View generated report [reports/NEXVION-DEMO-001.md](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/reports/NEXVION-DEMO-001.md).
- **Key Points**:
  - Highlights classification (`Dependency Failure`), severity (`MEDIUM`), root cause analysis, and remediation steps.

### Step 20 — Explain Controlled Failure & Rollback Evidence
- **Objective**: Prove platform resilience and automated rollback handling.
- **Action**: Run Helm history:
  ```bash
  helm history nexvion-web -n nexvion
  ```
- **Key Points**:
  - Helm history shows Revision 5 `Rollback to 3 (deployed)`.
  - Explains how Jenkins detects rollout failure (e.g. invalid tag/`ImagePullBackOff`), collects diagnostics, and automatically executes `helm rollback` to restore system health without operator intervention.
