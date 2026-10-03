# Phase 4.7 — Prometheus & Grafana Observability Foundation

## Executive Summary

Phase 4.7 implements an in-cluster observability foundation on the live **Amazon EKS** cluster (`nexvion-eks`, Kubernetes `v1.36.4`) in region `ap-south-1`.

This phase deploys **Prometheus** for metrics collection and time-series storage alongside **Grafana** for visualization and dashboarding. The deployment uses a resource-conscious, Helm-based staging architecture tailored for the single `t3.small` EKS worker node, establishing complete visibility into Kubernetes nodes, pod resource usage, HPA scaling metrics, and workload availability without incurring additional AWS managed service costs ($0.00 extra cloud infrastructure charges).

---

## Observability Architecture & Metrics Pipeline

```
  +-------------------------------------------------------------------------------------------------------------+
  |                                   KUBERNETES NAMESPACE: monitoring                                           |
  |                                                                                                             |
  |  +---------------------------+       PromQL Metrics Scrape (15s)       +---------------------------------+  |
  |  | Prometheus Server         | ◄────────────────────────────────────── | Grafana (Port 80)               |  |
  |  | (prometheus-server)       |                                         | - Datasource: Prometheus        |  |
  |  | - 2d Retention / emptyDir |                                         | - Dashboard: Nexvion Platform   |  |
  |  +──────────────┬────────────+                                         +─────────────────────────────────+  |
  |                 │                                                                                           |
  |                 │ Scrapes Targets (Kubelet / cAdvisor / kube-state-metrics / node-exporter)                 |
  |                 ▼                                                                                           |
  +─────────────────┼───────────────────────────────────────────────────────────────────────────────────────────+
                    │
                    ▼
  +─────────────────┼───────────────────────────────────────────────────────────────────────────────────────────+
  | KUBERNETES WORKLOADS & CLUSTER TARGETS                                                                      |
  |                                                                                                             |
  |  +────────────────────────────────---+   +───────────────────────────────────+   +──────────────────────────+  |
  |  | EKS Node (node-exporter)          |   | kube-state-metrics                |   | cAdvisor / Kubelet       |  |
  |  | - Node CPU / RAM %                |   | - Deployment Replicas             |   | - Pod CPU Usage          |  |
  |  | - Node Readiness                  |   | - HPA Current vs Desired          |   | - Pod Memory Working Set |  |
  |  |                                   |   | - Pod Restarts Total              |   | - Container Restarts     |  |
  |  +───────────────────────────────────+   +───────────────────────────────────+   +──────────────────────────+  |
  |                                                                                                             |
  |  +───────────────────────────────────────────────────────────────────────────────────────────────────────+  |
  |  | WORKLOAD SCOPE: nexvion (nexvion-web 2/2 Replicas & nexvion-web-hpa 2–5 Replicas @ 70% CPU Target)    |  |
  |  +───────────────────────────────────────────────────────────────────────────────────────────────────────+  |
  +-------------------------------------------------------------------------------------------------------------+
```

---

## 1. Existing Phase 4.6 Baseline Preserved

Before executing Phase 4.7, the Phase 4.6 baseline was audited and preserved completely:

- **EKS Cluster:** `nexvion-eks` (v1.36.4) in `ap-south-1`.
- **Nexvion Workload:** `deployment.apps/nexvion-web` in namespace `nexvion` (2/2 Ready).
- **HPA Configuration:** `horizontalpodautoscaler/nexvion-web-hpa` active (`cpu: 1%/70%`, min 2, max 5).
- **Metrics Server:** `metrics-server` in `kube-system` namespace active.
- **Ingress Controller:** `ingress-nginx` (`type: NodePort`, HTTP 31449) active.

---

## 2. Helm Installation & Namespace Architecture

Observability components were deployed in a dedicated `monitoring` namespace using declarative Helm values files stored in the repository at [`helm/monitoring/`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/helm/monitoring):

- **Target Namespace:** `monitoring` (`kubectl create namespace monitoring`)
- **Prometheus Helm Chart:** `prometheus-community/prometheus` (v27.5.0)
  - Values File: [`helm/monitoring/prometheus-values.yaml`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/helm/monitoring/prometheus-values.yaml)
- **Grafana Helm Chart:** `grafana/grafana` (v10.5.15, Grafana v12.3.1)
  - Values File: [`helm/monitoring/grafana-values.yaml`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/helm/monitoring/grafana-values.yaml)

### Kubernetes Resources Created in Namespace `monitoring`:

| Resource Type | Identifier | Configuration Details | Status |
|---|---|---|---|
| **Namespace** | `monitoring` | Dedicated observability isolation namespace | Active |
| **Deployment** | `deployment.apps/prometheus-server` | 2/2 ready containers (`prometheus-server`, `configmap-reload`), 2d retention | **2/2 Ready** |
| **Deployment** | `deployment.apps/prometheus-kube-state-metrics` | 1/1 ready replica exporting Kubernetes object states | **1/1 Ready** |
| **DaemonSet** | `daemonset.apps/prometheus-prometheus-node-exporter` | 1/1 ready pod per node collecting OS hardware metrics | **1/1 Ready** |
| **Deployment** | `deployment.apps/grafana` | 1/1 ready replica with pre-configured datasource & dashboards | **1/1 Ready** |
| **Services** | `prometheus-server`, `prometheus-kube-state-metrics`, `grafana` | `ClusterIP` services providing internal cluster routing | Active |

---

## 3. Scrape Configuration & Collected Metrics

Prometheus automatically discovers and scrapes cluster metrics every `15s`:

1. **EKS Node Metrics (`node-exporter`):**
   - `node_cpu_seconds_total` (Node CPU utilization mode breakdown)
   - `node_memory_MemTotal_bytes`, `node_memory_MemAvailable_bytes` (Node memory utilization)
2. **Kubernetes Object Metrics (`kube-state-metrics`):**
   - `kube_node_status_condition{condition="Ready",status="true"}` (Node readiness status)
   - `kube_deployment_status_replicas_available`, `kube_deployment_spec_replicas` (Desired vs available replicas)
   - `kube_horizontalpodautoscaler_status_current_replicas`, `kube_horizontalpodautoscaler_status_desired_replicas` (HPA replica states)
   - `kube_pod_container_status_restarts_total` (Container restart counters)
3. **Container Resource Metrics (`cAdvisor / Kubelet`):**
   - `container_cpu_usage_seconds_total` (Pod CPU rate per container)
   - `container_memory_working_set_bytes` (Pod working set memory bytes)

---

## 4. Grafana Datasource & Dashboard Provisioning

Grafana is provisioned declaratively via [`helm/monitoring/grafana-values.yaml`](file:///c:/Users/Lalit%20Punjabi/Nexvion_DT_Project/helm/monitoring/grafana-values.yaml):

### A. Datasource Provisioning
- **Name:** `Prometheus` (Default)
- **URL:** `http://prometheus-server.monitoring.svc.cluster.local:80`
- **Access:** `proxy`
- **Scrape Interval:** `15s`

### B. Declarative Dashboard (`Nexvion EKS Platform Observability`)
- **Dashboard UID:** `nexvion-platform-overview`
- **Folder:** `Nexvion Platform`
- **Visual Panels Provided:**
  1. **Kubernetes Node Readiness** (Stat panel: Active ready nodes)
  2. **Nexvion Deployment Replicas** (Stat panel: Desired vs Available replicas for `nexvion-web`)
  3. **HPA Replicas** (Stat panel: Current vs Desired replicas for `nexvion-web-hpa`)
  4. **Nexvion Pod Restarts Total** (Stat panel: Container restart counter)
  5. **EKS Worker Node CPU Utilization %** (Timeseries graph: Node CPU usage percentage)
  6. **EKS Worker Node Memory Utilization %** (Timeseries graph: Node RAM usage percentage)
  7. **Nexvion Pods CPU Usage** (Timeseries graph: Cores consumed per pod)
  8. **Nexvion Pods Memory Usage** (Timeseries graph: Working set RAM per pod)

---

## 5. Staging Resource Optimization & Cost Analysis

| Component | Resource Requests | Resource Limits | Cost Justification |
|---|---|---|---|
| **Prometheus Server** | CPU: `100m`, Memory: `128Mi` | CPU: `300m`, Memory: `384Mi` | Configured with `2d` retention and `emptyDir` storage ($0.00 EBS cost). |
| **Kube-State-Metrics** | CPU: `10m`, Memory: `32Mi` | CPU: `50m`, Memory: `64Mi` | Lightweight exporter consuming ~15MiB RAM. |
| **Node-Exporter** | CPU: `10m`, Memory: `16Mi` | CPU: `50m`, Memory: `32Mi` | DaemonSet container consuming ~10MiB RAM. |
| **Grafana** | CPU: `50m`, Memory: `64Mi` | CPU: `200m`, Memory: `128Mi` | Configured with `emptyDir` storage ($0.00 EBS cost). |
| **Alertmanager & Pushgateway** | **Disabled ($0.00)** | **Disabled ($0.00)** | Disabled to conserve RAM/CPU on `t3.small` worker node. |
| **AWS Managed Monitoring** | **Omitted ($0.00)** | **Omitted ($0.00)** | Avoids AWS Managed Prometheus ($0.90/GB) and Amazon Managed Grafana ($9.00/user-mo). |

---

## 6. Live Cluster Validation Results

### A. Pod & Service Status in Namespace `monitoring`:
```bash
kubectl get pods -n monitoring
```
**Output:**
```text
NAME                                             READY   STATUS    RESTARTS   AGE
grafana-7fcbd86d6f-pvprw                         1/1     Running   0          86s
prometheus-kube-state-metrics-869745d8bd-m94dw   1/1     Running   0          4m13s
prometheus-prometheus-node-exporter-cztsj        1/1     Running   0          2m36s
prometheus-server-98f675855-rk245                2/2     Running   0          4m13s
```

### B. Live PromQL Metric Queries:
```bash
# Query Deployment Replicas Available
kubectl exec -n monitoring deploy/prometheus-server -c prometheus-server -- wget -qO- "http://localhost:9090/api/v1/query?query=kube_deployment_status_replicas_available"
```
**Result:** `status: success`, `deployment: nexvion-web` → **2 available replicas**.

```bash
# Query HPA Current Replicas
kubectl exec -n monitoring deploy/prometheus-server -c prometheus-server -- wget -qO- "http://localhost:9090/api/v1/query?query=kube_horizontalpodautoscaler_status_current_replicas"
```
**Result:** `status: success`, `horizontalpodautoscaler: nexvion-web-hpa` → **2 current replicas**.

```bash
# Query Node Readiness Status
kubectl exec -n monitoring deploy/prometheus-server -c prometheus-server -- wget -qO- "http://localhost:9090/api/v1/query?query=sum(kube_node_status_condition%7Bcondition%3D%22Ready%22%2Cstatus%3D%22true%22%7D)"
```
**Result:** `status: success` → **1 Ready node**.

### C. Grafana API Health & Datasource Validation:
```bash
# Query Grafana Health API
kubectl exec -n monitoring deploy/prometheus-server -c prometheus-server -- wget -qO- "http://grafana.monitoring.svc.cluster.local/api/health"
```
**Result:** `{"database":"ok","version":"12.3.1"}`.

```bash
# Query Grafana Datasources API
kubectl exec -n monitoring deploy/prometheus-server -c prometheus-server -- wget -qO- --header="Authorization: Basic YWRtaW46bmV4dmlvbi1zdGFnaW5nLXBhc3M=" "http://grafana.monitoring.svc.cluster.local/api/datasources"
```
**Result:** `name: "Prometheus"`, `type: "prometheus"`, `isDefault: true`, `url: "http://prometheus-server.monitoring.svc.cluster.local:80"`.

```bash
# Query Grafana Provisioned Dashboards API
kubectl exec -n monitoring deploy/prometheus-server -c prometheus-server -- wget -qO- --header="Authorization: Basic YWRtaW46bmV4dmlvbi1zdGFnaW5nLXBhc3M=" "http://grafana.monitoring.svc.cluster.local/api/search"
```
**Result:** `title: "Nexvion EKS Platform Observability"`, `uid: "nexvion-platform-overview"`, `folderTitle: "Nexvion Platform"`.

---

## 7. Known Limitations & Architectural Disclosures

1. **Ephemeral Staging Storage:** Both Prometheus and Grafana use `emptyDir` volumes to avoid billable AWS EBS storage charges during staging testing. Time-series metrics reset if the server pod is deleted.
2. **HTTP Application Metrics Disclosure:** `ingress-nginx` exports metrics on port 10254. Custom NGINX HTTP request counter metrics (`nginx_ingress_controller_requests`) require optional ServiceMonitor CRD scrapers (deferred). Application pod health is monitored via standard Kubernetes pod metrics, health probes, and deployment state indicators.

---

## 8. Phase 4.7 Completion Status

```text
Phase 4.7 = COMPLETE
```

All required components (Prometheus, Grafana, datasources, dashboards, metrics scraping, and health checks) are fully functional and verified live on the Amazon EKS cluster.

---

## 9. Next Planned Phase (Phase 4.8 — ELK Centralized Logging Stack)

With metrics and observability active, the next planned scope is **Phase 4.8**:
- Deploy **Fluent-bit** / **Logstash** log shippers.
- Deploy **Elasticsearch** & **Kibana** for centralized pod log aggregation and search.
