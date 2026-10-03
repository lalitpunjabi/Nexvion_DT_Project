# Phase 4.6 — EKS Observability Metrics, HPA Validation & Ingress NodePort Routing

## Executive Summary

Phase 4.6 implements Kubernetes observability metrics, validates real Horizontal Pod Autoscaler (HPA) metric calculations, and deploys cost-conscious ingress routing on the live **Amazon EKS** cluster (`nexvion-eks`, Kubernetes `v1.36.4`) in region `ap-south-1`.

This phase introduces **Metrics Server** for resource metric collection, validates active HPA CPU metrics for `deployment/nexvion-web`, and deploys **`ingress-nginx`** configured with `type: NodePort` (HTTP Port `31449`, HTTPS Port `31941`). This approach establishes operational ingress routing through the EKS worker node's private VPC address while avoiding the creation of a separate AWS Load Balancer and its associated hourly/data-processing charges.

---

## Architecture & Traffic Flow Topology

```
Client / VPC Traffic (Host: nexvion.example.com)
            │
            ▼
EKS Worker Node Private IP : 31449 (NodePort)
            │
            ▼
Ingress Controller (ingress-nginx / NodePort 31449 / ClusterIP 10.100.51.190)
            │
            ▼
Nexvion Ingress (nexvion-web-ingress — Class: nginx | Host: nexvion.example.com)
            │
            ▼
ClusterIP Service (nexvion-web-service — Port: 80/TCP | Cluster IP: 10.100.27.163)
            │
            ├───────────────────────────────────────┐
            ▼                                       ▼
  ┌─────────────────────┐       ┌─────────────────────┐
  │ Pod 1: ...-jtvbw    │       │ Pod 2: ...-qcnwx    │    ◄─── Monitored by Metrics Server & HPA
  │ Status: 1/1 Running │       │ Status: 1/1 Running │         (Autoscaling: 2–5 Replicas @ 70% CPU Target)
  │ Non-root UID: 101   │       │ Non-root UID: 101   │
  │ Read-Only Root FS   │       │ Read-Only Root FS   │
  └─────────────────────┘       └─────────────────────┘
```

> [!NOTE]
> **Access Validation Scope:**
> 1. **Ingress Routing:** VERIFIED (Internal ClusterIP & service-level host routing functional).
> 2. **NodePort Routing:** VERIFIED (Worker node private IP `172.31.59.164:31449` functional).
> 3. **Public Internet Exposure:** NOT VALIDATED (Public Internet exposure, public security group HTTP ingress rules, and public DNS resolution were not validated in Phase 4.6).

---

## 1. Initial State Audit (Before Phase 4.6)

Before modifying the cluster, an initial read-only audit confirmed:

- **EKS Cluster:** `nexvion-eks` (v1.36.4-eks-3b4a6ca) in `ap-south-1`.
- **Worker Node:** `ip-172-31-59-164.ap-south-1.compute.internal` (`t3.small`, Ready).
- **Workload:** `deployment.apps/nexvion-web` with 2/2 Ready running pods.
- **Service:** `service/nexvion-web-service` (`ClusterIP`, Port 80).
- **Metrics Status:** `kubectl top nodes` failed with `error: Metrics API not available`.
- **HPA Status:** `horizontalpodautoscaler/nexvion-web-hpa` returned `cpu: <unknown>/70%`.
- **Ingress Status:** `ingress.networking.k8s.io/nexvion-web-ingress` declared with class `nginx`, but no ingress controller was installed (`ADDRESS` was blank).

---

## 2. Metrics Server Deployment & Verification

### A. Installation Details
- **Component:** `Metrics Server` (official Kubernetes SIG release v0.7.x / `components.yaml`).
- **Namespace:** `kube-system`.
- **Deployment Strategy:** Declarative YAML manifest via official release endpoint.
- **Pod Status:** `metrics-server-687f9dc499-jgvds` (1/1 Running).

### B. Live Verification Commands & Metrics Output

```bash
# Verify Metrics Server Pod
kubectl get pods -n kube-system -l k8s-app=metrics-server
```
**Output:** `metrics-server-687f9dc499-jgvds  1/1  Running  0  10m`

```bash
# Verify Node Resource Usage Metrics
kubectl top nodes
```
**Output:**
```text
NAME                                           CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)   
ip-172-31-59-164.ap-south-1.compute.internal   32m          1%       718Mi           50%         
```

```bash
# Verify Pod Resource Usage Metrics in 'nexvion' Namespace
kubectl top pods -n nexvion
```
**Output:**
```text
NAME                           CPU(cores)   MEMORY(bytes)   
nexvion-web-78d49686cd-jtvbw   1m           3Mi             
nexvion-web-78d49686cd-qcnwx   1m           3Mi             
```

---

## 3. Horizontal Pod Autoscaler (HPA) Real Metric Validation

### A. HPA Status Resolution
With Metrics Server active, `horizontalpodautoscaler/nexvion-web-hpa` immediately resolved real CPU metrics:

- **Reference:** `Deployment/nexvion-web`
- **Configured Scaling Range:** Minimum `2` replicas, Maximum `5` replicas
- **CPU Target:** `70%` utilization threshold
- **Current Metric:** `cpu: 1%/70%` (1m CPU per pod against 100m requested CPU)
- **Status Condition:** `ScalingActive = True` (`ValidMetricFound: the HPA was able to successfully calculate a replica count from cpu resource utilization`).

### B. Controlled CPU Load Testing Results
Controlled load testing validated real CPU metric collection and HPA replica calculation:

1. **Load Test Execution:** A temporary curl load generator pod was launched in namespace `nexvion`.
2. **CPU Metrics Under Load:** `kubectl top pods -n nexvion` confirmed pod CPU usage increased to `7m` per pod (`21%` of requested CPU).
3. **HPA Replica Calculation:** `kubectl get hpa -n nexvion` updated TARGETS to `cpu: 21%/70%` and correctly calculated 2 desired replicas (since utilization remained well below the 70% threshold).
4. **Load Cleanup:** The temporary load generator was completely deleted (`kubectl delete pod load-generator -n nexvion`). Pod metrics returned to 1m, and workload remained at 2/2 ready replicas.

---

## 4. Ingress Controller Deployment & Platform Dependency Architecture

### A. Cost-Conscious Ingress Controller
To satisfy staging cost constraints and avoid creating a separate AWS Load Balancer and its associated hourly/data-processing charges, **`ingress-nginx`** was installed via Helm configured with **`controller.service.type=NodePort`**.

- **Helm Release Name:** `ingress-nginx`
- **Chart:** `ingress-nginx/ingress-nginx` (v4.15.1, App Version v1.15.1)
- **Namespace:** `ingress-nginx`
- **Service Type:** `NodePort`
- **Allocated NodePorts:** HTTP `31449`, HTTPS `31941`
- **Admission Webhooks:** Disabled for staging efficiency (`controller.admissionWebhooks.enabled=false`).

### B. Platform Dependency Management Note
- **EKS Infrastructure:** Provisioned and managed via Terraform (`terraform/`).
- **Nexvion Application Workload:** Managed via Helm chart (`helm/nexvion-web`).
- **Ingress Controller (`ingress-nginx`):** Installed separately using Helm during Phase 4.6 as a shared cluster platform dependency, rather than embedding it inside the application workload chart.

### C. Ingress Resource Binding
Once active, `ingress-nginx` automatically discovered and bound `ingress.networking.k8s.io/nexvion-web-ingress`:

- **Ingress Address Assigned:** `10.100.51.190`
- **Ingress Class:** `nginx`
- **Host Route:** `nexvion.example.com` → `service/nexvion-web-service:80` (Endpoints: `172.31.58.158:80`, `172.31.57.239:80`)

---

## 5. Live Ingress NodePort Routing Validation

Endpoint routing tests were executed against `ingress-nginx-controller` with Host header `nexvion.example.com`:

| Tested Endpoint | Transport / Routing Target | Expected Status | Actual Status | Response Verification |
|---|---|---|---|---|
| `/healthz` | ClusterIP Service (`10.100.51.190:80`) | `HTTP 200 OK` | **200 OK** | `OK` body returned; CSP & security headers verified |
| `/` (Index) | ClusterIP Service (`10.100.51.190:80`) | `HTTP 200 OK` | **200 OK** | Home page HTML rendered successfully |
| `/products.html` | ClusterIP Service (`10.100.51.190:80`) | `HTTP 200 OK` | **200 OK** | Products catalog page rendered successfully |
| `/payment.html` | ClusterIP Service (`10.100.51.190:80`) | `HTTP 200 OK` | **200 OK** | Payment checkout page rendered successfully |
| `/healthz` (NodePort) | Worker Private IP (`172.31.59.164:31449`) | `HTTP 200 OK` | **200 OK** | Validated NodePort ingress routing on worker private IP |

> [!IMPORTANT]
> Public Internet exposure and public DNS resolution were **not validated** in Phase 4.6. The NodePort test verified traffic routing through the worker node's private VPC IP (`172.31.59.164:31449`).

---

## 6. Workload Security Profile & Audit

All container security context constraints on `deployment/nexvion-web` remain 100% active and enforced:

- `runAsNonRoot: true`
- `runAsUser: 101` / `runAsGroup: 101` / `fsGroup: 101`
- `readOnlyRootFilesystem: true` with `emptyDir` temp mounts (`/tmp`, `/var/cache/nginx`, `/var/run`)
- `allowPrivilegeEscalation: false`
- `capabilities.drop: ["ALL"]`, `capabilities.add: ["NET_BIND_SERVICE"]`
- `seccompProfile.type: RuntimeDefault`
- Resource Requests (`100m` CPU / `128Mi` RAM) and Limits (`500m` CPU / `256Mi` RAM)
- Health Probes (`startupProbe`, `livenessProbe`, `readinessProbe`) targeting `/healthz`

---

## 7. Cost Considerations & Architectural Trade-Offs

| Component | Architecture Choice | Cost Trade-Off / Rationale |
|---|---|---|
| **Metrics Server** | In-Cluster Deployment | Minimal node overhead (~18MiB RAM). Avoids external monitoring service charges. |
| **Ingress Controller** | `ingress-nginx` (`type: NodePort`) | Exposes HTTP via NodePort `31449`, avoiding creation of a separate AWS Load Balancer and associated hourly/data-processing charges. |
| **AWS Load Balancers (ALB/NLB)** | Intentionally Omitted | Avoids recurring AWS load balancer base charges during staging. |
| **AWS NAT Gateway** | Intentionally Omitted | Avoids recurring NAT Gateway hourly and data processing charges; worker nodes run in public subnets with Internet Gateway routing. |

---

## 8. Exact Execution & Validation Commands

```bash
# 1. Install Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 2. Add Ingress NGINX Helm Repo & Install Controller with NodePort
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.admissionWebhooks.enabled=false

# 3. Verify Metrics & HPA
kubectl top nodes
kubectl top pods -n nexvion
kubectl get hpa -n nexvion
kubectl describe hpa nexvion-web-hpa -n nexvion

# 4. Validate Ingress Endpoint Routing (Internal)
kubectl run ingress-test --rm -i --restart=Never --image=curlimages/curl --namespace=nexvion -- \
  curl -i -H "Host: nexvion.example.com" http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/healthz

# 5. Validate NodePort Access (Worker Node Private IP)
kubectl run ingress-nodeport-test --rm -i --restart=Never --image=curlimages/curl --namespace=nexvion -- \
  curl -i -H "Host: nexvion.example.com" http://172.31.59.164:31449/healthz
```

---

## 9. Next Planned Phase (Phase 4.7 — Prometheus + Grafana Observability Foundation)

With Metrics Server and Ingress active, the cluster is ready for **Phase 4.7**:
- Deploy lightweight **Prometheus** for cluster metric scraping and historical storage.
- Deploy **Grafana** with dashboards for Kubernetes workload monitoring and HTTP request throughput visualization.
