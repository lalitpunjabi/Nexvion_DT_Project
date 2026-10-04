# Phase 5 — End-to-End CI/CD Integration

## 1. Objective

Phase 5 delivers the complete, enterprise-grade **End-to-End CI/CD Integration Layer** for the Nexvion AI-Powered E-Commerce DevOps & Cloud-Native Delivery Platform. Building directly upon the static security gates (Phase 2), Infrastructure-as-Code & configuration management (Phase 3), EKS cluster deployment (Phase 4.4–4.5), metrics & ingress routing (Phase 4.6), Prometheus/Grafana observability (Phase 4.7), ELK centralized logging (Phase 4.8), and AI-assisted incident analysis (Phase 4.9), Phase 5 unifies all platform components into a single automated delivery pipeline managed by Jenkins.

---

## 2. Platform Architecture Evolution

### Previous Architecture (Phase 4.9 Baseline):
Telemetry, logging, and metrics were integrated, but workload deployments to Amazon EKS were executed manually via CLI/Helm commands.

### Phase 5 Integrated End-to-End Delivery Architecture:

```
GitHub Repository
       ↓
Jenkins Controller (EC2 / 'linux' node)
       ↓
Stage 1: Checkout & Git SHA Metadata Discovery
       ↓
Stage 2: Code Validation & Dependency Security Scan
       ↓
Stage 3: GitLeaks Secret Scan (v8.28.0)
       ↓
Stage 4: Docker Immutable Image Build (nexvion-web:${GIT_SHA})
       ↓
Stage 5: Trivy Container Vulnerability Gate (v0.60.0)
       ↓
Stage 6: Authenticate & Push to Amazon ECR (677012863109.dkr.ecr.ap-south-1.amazonaws.com)
       ↓
Stage 7: Authenticate to Amazon EKS (nexvion-eks)
       ↓
Helm Lint & Manifest Dry-Run Rendering
       ↓
Helm Upgrade / Install Release (nexvion-web)
       ↓
EKS Rolling Update Deployment (maxSurge: 0, maxUnavailable: 1)
       ↓
kubectl rollout status verification
       ↓
Workload Health Probes (/healthz, /, /products.html, /payment.html)
       ├─────────────────────────────────┐
       ▼                                 ▼
Deployment SUCCESS             Deployment FAILURE
       │                                 │
       │                        Collect Diagnostics
       │                                 │
       │                   Execute Failure-Safe Incident Analyzer
       │                                 │
       │                   Execute Automated Helm Rollback
       ▼                                 ▼
Prometheus Metrics Scraper     Kibana Centralized Search
& Grafana Overview             & Elasticsearch Indexing
```

---

## 3. Pipeline Stages & Execution Flow

The delivery flow is declared in [`Jenkinsfile`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/Jenkinsfile):

1. **Stage 1: Checkout & Metadata**: Fetches Git SCM and determines immutable 7-character Git commit SHA (`env.GIT_COMMIT_SHA`).
2. **Stage 2: Validate & Dependency Scan**: Validates HTML/CSS/JS syntax, Docker Compose files, Helm chart linting, and runs dependency security checks.
3. **Stage 3: Secret Scan (GitLeaks)**: Executes GitLeaks `v8.28.0` with `.gitleaks.toml` rules. Blocks builds if secrets are detected.
4. **Stage 4: Docker Build**: Builds container image tagged with `${GIT_COMMIT_SHA}`, `${BUILD_NUMBER}`, and `latest`.
5. **Stage 5: Image Vulnerability Scan (Trivy)**: Scans exact image `${APP_NAME}:${GIT_COMMIT_SHA}` for `HIGH,CRITICAL` vulnerabilities using Trivy `0.60.0`.
6. **Stage 6: Authenticate & Push to ECR**: Obtains short-lived Docker credentials via `aws ecr get-login-password --region ap-south-1`, tags image, pushes to Amazon ECR, and verifies OCI digest.
7. **Stage 7: EKS Helm Deployment & Rolling Update**:
   - Updates `kubeconfig` for `nexvion-eks` cluster.
   - Runs `helm lint` and `helm template` dry-run checks.
   - Executes `helm upgrade --install nexvion-web helm/nexvion-web -f helm/nexvion-web/values-prod.yaml --set image.repository=677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web --set image.tag=${GIT_SHA}`.
   - Monitors `kubectl rollout status deployment/nexvion-web -n nexvion --timeout=300s`.
   - Probes internal endpoints `/healthz`, `/`, `/products.html`, `/payment.html`.
8. **Stage 8: Local Compose Staging Deployment (Optional)**: Retains local Docker Compose staging path when `DEPLOY_TARGET == 'LOCAL_DOCKER'`.

---

## 4. Single-Node EKS Pod Budget Optimization (`maxPods=11`)

### Engineering Challenge:
The live EKS cluster operates on a single `t3.small` worker node with a strict kubelet pod limit of `maxPods=11`. The cluster runs 11 baseline pods (`nexvion-web` 2x, `elk` 1x, `fluent-bit` 1x, `prometheus-server` 1x, `grafana` 1x, `metrics-server` 1x, `ingress-nginx` 1x, `aws-node` 1x, `coredns` 1x, `kube-proxy` 1x).

Default Kubernetes rolling update strategy (`maxSurge: 1, maxUnavailable: 0`) attempts to create a 3rd `nexvion-web` pod before terminating an old pod. This required a 12th pod slot, triggering `Warning FailedScheduling: 0/1 nodes are available: 1 Too many pods`.

### Phase 5 Solution:
We updated `helm/nexvion-web/templates/deployment.yaml` and `values-prod.yaml` to parameterize the rolling update strategy:
```yaml
rollingUpdate:
  maxSurge: 0
  maxUnavailable: 1
```
With `maxSurge: 0` and `maxUnavailable: 1`, Kubernetes terminates 1 old pod first (dropping pod count to 10), then schedules 1 new pod (pod count 11), ensuring zero pod budget violations while completing rolling updates in under 20 seconds.

---

## 5. Failure Handling & Automated Rollback

If a deployment or health check fails:
1. **Diagnostic Collection**: Automatically dumps pod states, Deployment conditions (`kubectl describe`), namespace events, and tail container logs.
2. **Failure-Safe AI Diagnostics**: Executes `python tools/incident-analysis/incident_analyzer.py --incident-id NEXVION-EKS-FAIL-${BUILD_NUMBER}` to collect observability evidence without failing the error handler.
3. **Automated Helm Rollback**: Inspects `helm history nexvion-web -n nexvion`. If revision > 1, executes:
   ```bash
   helm rollback nexvion-web -n nexvion
   kubectl rollout status deployment/nexvion-web -n nexvion --timeout=180s
   ```

---

## 6. Security & Credential Isolation

- **Zero Secrets in Source Control**: `.env` and `*.env` are strictly listed in `.gitignore`. GitLeaks scanner verifies 0 secret leaks.
- **IAM Instance Role & Short-Lived Tokens**: AWS ECR authentication uses `aws ecr get-login-password`, avoiding static hardcoded access keys.
- **EKS RBAC & Kubeconfig**: `aws eks update-kubeconfig` creates dynamic temporary session tokens.
- **No Console Credential Leakage**: `set -x` is omitted for sensitive commands.

---

## 7. Phase 5 v2 Hardening, Corrections & Controlled Failure/Rollback Validation

### 1. Capacity-Safe Rolling Update Strategy (`maxSurge: 0, maxUnavailable: 1`)
- **Single-Node Capacity Constraint**: The live AWS EKS cluster (`nexvion-eks`) operates on a single `t3.small` worker node with a strict kubelet pod limit of `maxPods=11`.
- **Strategy Tuning**: The standard Kubernetes rolling update strategy (`maxSurge: 1, maxUnavailable: 0`) attempts to create a 3rd `nexvion-web` pod before terminating an old pod. On this single-node cluster (where 11 pods are already running across system, monitoring, and logging namespaces), `maxSurge: 1` triggers `Warning FailedScheduling: 0/1 nodes are available: 1 Too many pods`.
- **Tuned Behavior**: Configuring `maxSurge: 0, maxUnavailable: 1` explicitly terminates 1 old pod first (dropping pod count to 10), then schedules 1 new pod (bringing pod count back to 11). This ensures zero pod budget violations and completes rolling updates in under 20 seconds. Rather than making unsupported zero-downtime claims, this strategy is accurately documented as a **capacity-safe rolling update optimized for the single-node staging cluster**.

### 2. Dynamic Previous Helm Revision Detection
- **Dynamic Revision Extraction**: Prior to `helm upgrade --install`, the pipeline queries the live cluster via `helm history` and dynamically parses the latest revision with status `deployed` or `superseded` (e.g. `PREVIOUS_HELM_REVISION = 3`).
- **Dynamic Rollback Execution**: If `helm upgrade` or `kubectl rollout status` fails, the pipeline executes `helm rollback nexvion-web ${PREVIOUS_HELM_REVISION} -n nexvion` rather than hardcoding revision numbers or blindly rolling back.
- **Initial Release Guard**: If no previous deployed revision exists (e.g., initial install), the pipeline safely skips rollback and reports that rollback is unavailable.

### 3. Multi-Level Application Health Verification
- **Level 1 (Pod-Local Health)**: Executes `kubectl exec` into the workload pod to probe `http://localhost/healthz`, `/`, `products.html`, and `payment.html` (verifying local web server process health).
- **Level 2 (Kubernetes Service Routing Health)**: Spawns a temporary diagnostic pod (`curlimages/curl:8.10.1`) in namespace `nexvion` to perform HTTP GET requests against `http://nexvion-web-service/` for `/healthz`, `/`, `products.html`, and `payment.html`. This validates end-to-end Pod $\rightarrow$ K8s Service $\rightarrow$ Pod internal networking before automatically deleting the temporary pod.
- **Level 3 (Internal NodePort Ingress Health)**: Probes internal VPC worker IP via NodePort (`http://172.31.59.164:31449/healthz`), verifying `ingress-nginx` routing.

---

## 8. Live Controlled Failure & Rollback Test Evidence

A controlled deployment failure test was executed on the live EKS cluster (`nexvion-eks`) to validate the automated failure detection, diagnostic collection, dynamic rollback, and health recovery flow:

1. **Pre-Test State**: Helm release `nexvion-web` revision 3 was active and healthy (`2/2 Ready` pods).
2. **Controlled Failure Trigger**: Executed `helm upgrade nexvion-web helm/nexvion-web` with `--set image.tag=invalid-nonexistent-image-tag-v999`.
3. **Rollout Status Failure**: `kubectl rollout status deployment/nexvion-web -n nexvion --timeout=20s` timed out as expected with `ImagePullBackOff` / `ErrImagePull`.
4. **Diagnostic Collection Output**:
   - `kubectl get pods -n nexvion`: Showed `nexvion-web-685b5d5d67-g482f 0/1 ImagePullBackOff`.
   - `kubectl describe deployment`: Showed `Failed to pull image "677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web:invalid-nonexistent-image-tag-v999"`.
5. **Dynamic Rollback Execution**: Identified `PREVIOUS_HELM_REVISION = 3` and executed `helm rollback nexvion-web 3 -n nexvion`.
6. **Rollback Rollout Status**: `kubectl rollout status deployment/nexvion-web -n nexvion` output:
   `deployment "nexvion-web" successfully rolled out`.
7. **Post-Rollback Health Probes**:
   - Level 1 Pod Probe: `{"status":"UP","timestamp":"...","environment":"staging"}`
   - Level 2 Service Probe: `http://nexvion-web-service/healthz` (HTTP 200), `/` (HTTP 200), `products.html` (HTTP 200), `payment.html` (HTTP 200).
8. **Final Helm History**:
   ```
   REVISION  UPDATED                   STATUS      CHART            APP VERSION  DESCRIPTION
   1         Sun Oct  4 00:23:00 2026  superseded  nexvion-web-0.1.0 1.0.0        Install complete
   2         Sun Oct  4 18:55:59 2026  superseded  nexvion-web-0.1.0 1.0.0        Upgrade complete
   3         Sun Oct  4 19:02:33 2026  superseded  nexvion-web-0.1.0 1.0.0        Upgrade complete
   4         Sun Oct  4 19:18:34 2026  superseded  nexvion-web-0.1.0 1.0.0        Upgrade complete
   5         Sun Oct  4 19:18:57 2026  deployed    nexvion-web-0.1.0 1.0.0        Rollback to 3
   ```
9. **Clean State Restoration**: The temporary failure configuration was completely removed and the cluster restored to 100% healthy operational state (`2/2 Ready` pods, revision 5).

---

## 9. Resource & Cost Considerations

- **AWS Cost Alignment**: No additional EC2 instances, EKS worker nodes, NAT Gateways, or managed load balancers were created for Phase 5. Existing EKS control plane and worker node charges apply.

---

## 10. Phase 5 Completion Status

Phase 5 v2 is **Hardened & Validated** on the live AWS platform.

- [x] Full Jenkins delivery pipeline declared in [`Jenkinsfile`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/Jenkinsfile).
- [x] Code validation and static web dependency checks integrated (`npm audit`).
- [x] GitLeaks secret scan gate integrated (`v8.28.0`).
- [x] Immutable Docker image building with Git SHA tag (`685f1c1`).
- [x] Trivy container security gate integrated (`v0.60.0`, 0 findings).
- [x] Amazon ECR authentication and image push verified.
- [x] Amazon EKS authentication and Helm deployment verified.
- [x] Pod budget constraint resolved via `maxSurge: 0, maxUnavailable: 1` capacity-safe rolling updates.
- [x] Dynamic previous Helm revision detection implemented (`helm rollback ${PREVIOUS_HELM_REVISION}`).
- [x] Multi-level workload health verification (Level 1 Pod-Local + Level 2 K8s Service `curlimages/curl` diagnostic pod) verified 200 OK across `/healthz`, `/`, `products.html`, `payment.html`.
- [x] Controlled deployment failure test executed on live EKS cluster; failure detected, diagnostics captured, dynamic rollback executed, and workload health restored.
- [x] Observability integration (Prometheus, Grafana, ELK `nexvion-logs-*`) verified active.
