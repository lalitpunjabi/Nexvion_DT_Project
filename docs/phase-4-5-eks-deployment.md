# Phase 4.5 — Amazon EKS Container Deployment & Application Health Validation

## Executive Summary

Phase 4.5 achieves end-to-end containerized workload deployment of the **Nexvion E-Commerce Platform** onto the live **Amazon EKS (Elastic Kubernetes Service)** cluster (`nexvion-eks`) in AWS region `ap-south-1`.

The deployment pulls the immutable container image artifact (`677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web:0d575d0`) from Amazon ECR using short-lived IAM node role credentials (`AmazonEC2ContainerRegistryReadOnly`), instantiates a 2-replica Kubernetes Deployment in namespace `nexvion` via Helm 3, enforces strict security contexts, and validates application endpoints internally.

---

## Architecture Topology

```
External Traffic
      ↓
Ingress Controller (NOT INSTALLED — Deferred to Phase 4.6)
      ↓
Ingress Resource (DECLARED — nexvion-web-ingress / host: nexvion.example.com)
      ↓
ClusterIP Service (nexvion-web-service — Internal Cluster IP: 10.100.27.163:80)
      ↓
Nexvion Pods (2/2 Ready Running Pods in namespace 'nexvion')
```

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                              AMAZON AWS EKS CLUSTER (nexvion-eks)                                       |
|                                                     Kubernetes v1.36.4                                                  |
|                                                                                                                         |
|  External Traffic                                                                                                       |
|        │                                                                                                                |
|        ▼                                                                                                                |
|  [ Ingress Controller: NOT INSTALLED — Deferred to Phase 4.6 ]                                                          |
|        │                                                                                                                |
|        ▼                                                                                                                |
|  +-------------------------------------------------------------------------------------------------------------------+  |
|  | KUBERNETES NAMESPACE: nexvion                                                                                     |  |
|  |                                                                                                                   |  |
|  |   Ingress Resource (DECLARED ONLY — nexvion-web-ingress | Host: nexvion.example.com)                              |  |
|  |        │                                                                                                          |  |
|  |        ▼                                                                                                          |  |
|  |   ClusterIP Service (nexvion-web-service — Port: 80/TCP | Internal IP: 10.100.27.163)                              |  |
|  |        │                                                                                                          |  |
|  |        ├───────────────────────────────────────┐                                                                  |  |
|  |        ▼                                       ▼                                                                  |  |
|  |  +-------------------------------------+  +-------------------------------------+                                 |  |
|  |  | Pod 1: nexvion-web-78d49686cd-jtvbw   |  | Pod 2: nexvion-web-78d49686cd-qcnwx   |                                 |  |
|  |  | Status: 1/1 Running                 |  | Status: 1/1 Running                 |                                 |  |
|  |  | Non-root UID/GID: 101               |  | Non-root UID/GID: 101               |                                 |  |
|  |  | Read-Only Root Filesystem           |  | Read-Only Root Filesystem           |                                 |  |
|  |  +-------------------------------------+  +-------------------------------------+                                 |  |
|  |                                                                                                                   |  |
|  +-------------------------------------------------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------------------------------------------------+
```

---

## 1. Deployed Artifacts & Configuration

### A. Container Image Details
- **Registry URI:** `677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web`
- **Immutable Tag:** `0d575d0` (Git Commit SHA)
- **Image Digest:** `sha256:c4955394e26f60db8f3a1243b72307308aa3ad8c0545ec4f9703e7ab21863361`
- **Image Pull Policy:** `Always` (enforced via `values-prod.yaml`)

### B. Helm Release Specifications
- **Release Name:** `nexvion-web`
- **Chart Directory:** `helm/nexvion-web`
- **Values File:** `helm/nexvion-web/values-prod.yaml`
- **Target Namespace:** `nexvion`
- **Status:** `DEPLOYED` (Revision 1)

---

## 2. Kubernetes Resource Manifest Breakdown

| Resource Type | Resource Identifier | Configuration Details | Status |
|---|---|---|---|
| **Namespace** | `nexvion` | Dedicated workload namespace | Active |
| **Deployment** | `deployment.apps/nexvion-web` | 2/2 ready replicas, Capacity-Safe RollingUpdate (`maxSurge: 0`, `maxUnavailable: 1`) | **2/2 Ready** |
| **Pods** | `pod/nexvion-web-78d49686cd-*` | 2 running pods, UID 101 non-root, read-only FS, tmpfs mounts | **1/1 Running** |
| **Service** | `service/nexvion-web-service` | `ClusterIP` (Internal IP: `10.100.27.163`, Port: 80/TCP) | Active |
| **ConfigMap** | `configmap/nexvion-web-config` | Environment variables (`APP_NAME`, `ENVIRONMENT=staging`, `LOG_LEVEL=warn`) | Active |
| **Secret** | `secret/nexvion-web-secret` | Staging placeholder values only (`API_KEY_PLACEHOLDER`, `SESSION_SECRET_PLACEHOLDER`); not production secret management | **Placeholder Only** |
| **HPA** | `horizontalpodautoscaler/nexvion-web-hpa` | Autoscaling range 2-5 replicas targeting 70% CPU utilization; CPU metrics unavailable (Metrics Server deferred) | **Deployed (Metrics Deferred)** |
| **Ingress** | `ingress.networking.k8s.io/nexvion-web-ingress` | Host: `nexvion.example.com`, Class: `nginx`, Path: `/`; controller not installed | **Declared (Controller Deferred)** |

---

## 3. Security Hardening Controls

The deployed workloads enforce enterprise DevSecOps security controls defined in `helm/nexvion-web/values.yaml`:

- **Non-Root Execution:** `runAsNonRoot: true`, `runAsUser: 101`, `runAsGroup: 101`, `fsGroup: 101` (NGINX unprivileged user).
- **Read-Only Root Filesystem:** `readOnlyRootFilesystem: true` prevents unauthorized runtime filesystem modifications.
- **Privilege Escalation Prevention:** `allowPrivilegeEscalation: false`.
- **Capability Drop:** All Linux capabilities dropped (`capabilities.drop: ["ALL"]`), with only `NET_BIND_SERVICE` added for unprivileged port binding.
- **Seccomp Profile:** `seccompProfile.type: RuntimeDefault`.
- **Resource Limits & Requests:**
  - `requests`: CPU `100m`, Memory `128Mi`
  - `limits`: CPU `500m`, Memory `256Mi`
- **Probe Timings:**
  - `startupProbe`: `/healthz`, initial delay 3s, period 5s, failure threshold 10
  - `livenessProbe`: `/healthz`, initial delay 5s, period 10s, failure threshold 3
  - `readinessProbe`: `/healthz`, initial delay 3s, period 5s, failure threshold 3

---

## 4. Application Health & Endpoint Validation Logs

Internal HTTP request validation executed against `service/nexvion-web-service` inside the cluster:

| Endpoint Tested | Expected Status | Actual Status | Details / Headers Verified |
|---|---|---|---|
| `/healthz` | `HTTP 200 OK` | **200 OK** | `OK` body returned; security headers verified (`X-Frame-Options`, `CSP`, `X-Content-Type-Options`) |
| `/` (Index Page) | `HTTP 200 OK` | **200 OK** | Full HTML document rendered with navigation, brand logo, and featured products grid |
| `/products.html` | `HTTP 200 OK` | **200 OK** | Products catalog page rendered successfully (Content-Length: 9000 bytes) |
| `/payment.html` | `HTTP 200 OK` | **200 OK** | Payment checkout page rendered successfully (Content-Length: 8468 bytes) |

---

## 5. Architectural Disclosures & Deferred Components

1. **Ingress Controller & External Traffic Routing (Deferred to Phase 4.6):**
   - Flow: `External Traffic` → `Ingress Controller (NOT INSTALLED)` → `Ingress Resource (DECLARED)` → `ClusterIP Service` → `Nexvion Pods`.
   - The Service is maintained as `ClusterIP` to avoid creating billable AWS Load Balancers ($18.00+/month base charge) during staging.
   - The Ingress resource (`nexvion-web-ingress`) is declared in the Helm chart, but the Ingress Controller (`ingress-nginx` or AWS Load Balancer Controller) is **currently not installed**. External traffic routing is intentionally deferred to Phase 4.6.
   - **External access is currently not functional** and cannot route public HTTP traffic into the cluster. Internal health and endpoint validation are performed directly via ClusterIP.

2. **HPA & Metrics-Server Dependency:**
   - HPA is configured and deployed; CPU-based autoscaling requires Metrics Server, which is intentionally deferred to a later phase.
   - Configuration parameters: minimum 2 replicas, maximum 5 replicas, CPU target 70%.
   - CPU metrics are currently unavailable (`cpu: <unknown>/70%`) because Metrics Server has not been installed on the cluster.
   - Therefore, HPA configuration exists, but active CPU-based autoscaling has **NOT yet been validated**.

3. **Secret Management Disclosure (Placeholder Values Only):**
   - The current Kubernetes Secret (`secret/nexvion-web-secret`) contains **PLACEHOLDER/demo values only** (`API_KEY_PLACEHOLDER`, `SESSION_SECRET_PLACEHOLDER`) and is **NOT** production secret management.
   - Real production secrets should later be injected securely using an appropriate mechanism such as:
     - AWS Secrets Manager
     - External Secrets Operator (ESO)
     - Secure CI/CD secret injection
   - Real credentials or secrets are intentionally omitted for security and staging cost management.

---

## 6. Verification & Troubleshooting Commands

### Helm Release Verification:
```bash
helm list -n nexvion
helm status nexvion-web -n nexvion
```

### Kubernetes Workload Verification:
```bash
kubectl get all -n nexvion
kubectl rollout status deployment/nexvion-web -n nexvion
kubectl describe deployment nexvion-web -n nexvion
kubectl logs -n nexvion -l app.kubernetes.io/name=nexvion-web --tail=50
```

### Application Endpoint Testing (Internal):
```bash
kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl --namespace=nexvion -- curl -i http://nexvion-web-service.nexvion.svc.cluster.local/healthz
```
