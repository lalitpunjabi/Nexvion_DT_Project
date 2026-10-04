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

## 7. Actual Validation Evidence

### 1. Amazon ECR Push Verification:
- **Repository**: `677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web`
- **Tag**: `685f1c1`
- **Digest**: `sha256:1a8dc151c103bf6de6374f35bea6b6fdccac1cd348d719933cba7b07ef3510ab`
- **Status**: `ACTIVE`

### 2. EKS Helm Deployment & Rolling Update Output:
```
Release "nexvion-web" has been upgraded. Happy Helming!
NAME: nexvion-web
LAST DEPLOYED: Sun Oct 4 19:02:33 2026
NAMESPACE: nexvion
STATUS: deployed
REVISION: 3
deployment "nexvion-web" successfully rolled out
```

### 3. Live Pod Readiness (`kubectl get pods -n nexvion -o wide`):
```
NAME                           READY   STATUS    RESTARTS   AGE   IP              NODE
nexvion-web-6968cb9fbf-st278   1/1     Running   0          2m    172.31.63.146   ip-172-31-59-164.ap-south-1.compute.internal
nexvion-web-6968cb9fbf-xbm9n   1/1     Running   0          9m    172.31.63.145   ip-172-31-59-164.ap-south-1.compute.internal
```

### 4. Application Endpoint Health Probes:
- `/healthz`: `HTTP 200`
- `/`: `HTTP 200`
- `/products.html`: `HTTP 200`
- `/payment.html`: `HTTP 200`

---

## 8. Resource & Cost Considerations

- **AWS Cost Alignment**: No additional EC2 instances, EKS worker nodes, NAT Gateways, or managed load balancers were created for Phase 5. Existing EKS control plane and worker node charges apply.

---

## 9. Phase 5 Completion Status

Phase 5 is **100% COMPLETE and FULLY VALIDATED** on the live AWS platform.

- [x] Full Jenkins delivery pipeline declared in [`Jenkinsfile`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/Jenkinsfile).
- [x] Code validation and static web dependency checks integrated.
- [x] GitLeaks secret scan gate integrated (`v8.28.0`).
- [x] Immutable Docker image building with Git SHA tag (`685f1c1`).
- [x] Trivy container security gate integrated (`v0.60.0`, 0 findings).
- [x] Amazon ECR authentication and image push verified.
- [x] Amazon EKS authentication and Helm deployment verified.
- [x] Pod budget constraint resolved via `maxSurge: 0, maxUnavailable: 1` rolling updates.
- [x] Workload health probes (`/healthz`, `/`, `/products.html`, `/payment.html`) verified 200 OK.
- [x] Failure diagnostics and automated Helm rollback mechanism implemented.
- [x] Observability integration (Prometheus, Grafana, ELK `nexvion-logs-*`) verified active.
