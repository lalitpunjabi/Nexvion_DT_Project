# Phase 4.8 — ELK Centralized Logging Implementation

## 1. Objective

The objective of Phase 4.8 is to implement a lightweight, resource-conscious centralized logging architecture for the Nexvion platform deployed on AWS EKS (`nexvion-eks`, Kubernetes `v1.36.4`). 

Centralized logging provides unified collection, processing, storage, search, and visualization of all container `stdout`/`stderr` logs across Kubernetes namespaces without requiring application-level modifications or external AWS managed services.

---

## 2. Phase 4.7 Baseline

Prior to Phase 4.8, Phase 4.7 established the Prometheus + Grafana Observability Foundation in namespace `monitoring`. The baseline state verified prior to deployment was:
- **EKS Cluster**: `nexvion-eks` (v1.36.4, ap-south-1, 1x `t3.small` worker node).
- **Nexvion Workload**: `nexvion-web` Deployment (2/2 Ready, namespace `nexvion`).
- **Autoscaling & Ingress**: HPA active (`cpu: 1%/70%`, 2–5 replicas), `ingress-nginx` NodePort active (`31449`).
- **Observability Stack**: Metrics Server (`1/1 Running`), Prometheus Server (`2/2 Running`), Grafana (`1/1 Running`).

---

## 3. ELK Architecture

The logging architecture uses an industry-standard pipeline optimized for single-node EKS staging environments:

```
+-------------------------------------------------------------------------+
|                         AWS EKS Worker Node                             |
|                                                                         |
|  [ nexvion-web Pods ]   [ ingress-nginx ]   [ System & Monitoring Pods ]|
|            |                    |                         |             |
|            +--------------------+-------------------------+             |
|                                 |                                       |
|                       Container stdout / stderr                         |
|                                 |                                       |
|                      /var/log/containers/*.log                          |
|                                 v                                       |
|                    +-------------------------+                          |
|                    |   Fluent Bit DaemonSet  |                          |
|                    | (Metadata Filter & CRI) |                          |
|                    +-------------------------+                          |
|                                 |                                       |
|                     http://elasticsearch:9200                           |
|                                 v                                       |
|                    +-------------------------+                          |
|                    |      Elasticsearch      |  <--- (Single Node)      |
|                    |  (Index: nexvion-logs*) |                          |
|                    +-------------------------+                          |
|                                 |                                       |
|                     http://localhost:9200                               |
|                                 v                                       |
|                    +-------------------------+                          |
|                    |      Kibana Service     |                          |
|                    | (ClusterIP Port 5601)   |                          |
|                    +-------------------------+                          |
+-------------------------------------------------------------------------+
```

---

## 4. Logging Data Flow

1. **Log Emission**: Containers write formatted log lines to `stdout`/`stderr`. Kubelet redirects these logs to `/var/log/containers/*.log` on the host worker node.
2. **Log Ingestion & Parsing**: The `fluent-bit` DaemonSet tails log files using the `cri` regex parser tailored for containerd runtime on EKS v1.36.
3. **Kubernetes Metadata Enrichment**: Fluent Bit queries the Kubernetes API server using its ServiceAccount (`fluent-bit-read`) to attach `pod_name`, `namespace_name`, `container_name`, `host`, `docker_id`, and `labels` to every record.
4. **Log Indexing**: Fluent Bit outputs enriched JSON payloads via HTTP bulk requests to Elasticsearch on port `9200`. Logs are indexed under `nexvion-logs-YYYY.MM.DD`.
5. **Visualization**: Kibana connects to Elasticsearch via ClusterIP (`http://elasticsearch.logging.svc.cluster.local:9200`), rendering logs searchable through Kibana web dashboards.

---

## 5. Fluent Bit Configuration

Declarative Kubernetes logging manifests and Helm-oriented configuration values are maintained under `helm/logging/` (`fluent-bit.yaml` and `fluent-bit-values.yaml`):

- **Log Level**: Set to `Log_Level info` for clean production-style container logging without debug noise.
- **DaemonSet Resource Budget**:
  - CPU Request: `20m`, Limit: `100m`
  - Memory Request: `30Mi`, Limit: `64Mi`
- **RBAC**: ServiceAccount `fluent-bit`, ClusterRole `fluent-bit-read` granting `get, list, watch` on `namespaces`, `pods`, `pods/logs`.
- **CRI Parser Regex**: `^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<message>.*)$`
- **Output Target**: Elasticsearch host `elasticsearch.logging.svc.cluster.local:9200`, `Logstash_Prefix: nexvion-logs`.

---

## 6. Elasticsearch Configuration

Declarative Kubernetes logging manifests and Helm-oriented configuration values are maintained under `helm/logging/` (`elk-stack.yaml` and `elasticsearch-values.yaml`):

- **Deployment Mode**: Single-node staging (`discovery.type=single-node`).
- **JVM Heap Allocation**: Explicitly limited via `ES_JAVA_OPTS="-Xms128m -Xmx128m"` to ensure stability on `t3.small`.
- **Security Scope**: Security plugin disabled (`xpack.security.enabled=false`) for staging/demo purposes. Exposed solely via internal `ClusterIP` (`9200`).
- **Service Spec**: `ClusterIP` with `publishNotReadyAddresses: true` so logging ingestion can proceed immediately upon Elasticsearch startup.
- **Resource Limits**:
  - CPU Request: `100m`, Limit: `300m`
  - Memory Request: `256Mi`, Limit: `512Mi`
- **Storage Strategy**: Ephemeral in-pod overlay storage. No AWS EBS volumes or managed OpenSearch clusters are created, avoiding extra AWS managed service fees.

---

## 7. Kibana Configuration

Declarative Kubernetes logging manifests and Helm-oriented configuration values are maintained under `helm/logging/` (`elk-stack.yaml` and `kibana-values.yaml`):

- **Target Backend**: `http://127.0.0.1:9200` (co-located in `elk` pod for zero-latency localhost IPC).
- **Node.js Memory Safety**: Enforced via `NODE_OPTIONS="--max-old-space-size=256"`.
- **Service Spec**: Internal `ClusterIP` Service exposing port `5601`.
- **Resource Limits**:
  - CPU Request: `50m`, Limit: `200m`
  - Memory Request: `160Mi`, Limit: `384Mi`

---

## 8. Kubernetes Namespaces & Resources

All logging components are deployed into the `logging` namespace using declarative manifests under `helm/logging/` (the primary Helm chart remains `helm/nexvion-web` for the core application):

| Resource Type | Resource Name | Namespace | Specs / Purpose |
| :--- | :--- | :--- | :--- |
| **Namespace** | `logging` | `logging` | Isolated logging workspace |
| **Deployment** | `elk` | `logging` | Co-located Elasticsearch & Kibana pod (`strategy: Recreate`) |
| **DaemonSet** | `fluent-bit` | `logging` | Lightweight host log collector |
| **Service** | `elasticsearch` | `logging` | ClusterIP (Port 9200) |
| **Service** | `kibana` | `logging` | ClusterIP (Port 5601) |
| **ConfigMap** | `fluent-bit-config` | `logging` | Fluent Bit pipeline configuration (`fluent-bit.conf`, `parsers.conf`) |
| **ServiceAccount** | `fluent-bit` | `logging` | RBAC service account |

---

## 9. Resource Constraints & Single-Node Safety Strategy

The EKS worker node (`t3.small`) has hard limits:
- **CPU**: 2 vCPUs (1930m allocatable)
- **Memory**: 2 GiB (1468Mi allocatable)
- **Max Pod Limit**: 11 pods (enforced by kubelet & AWS VPC CNI secondary IP limits).

### Co-location Optimization
To fit the logging stack alongside `nexvion-web`, `ingress-nginx`, `metrics-server`, and `prometheus-server` without exceeding the 11 max-pod limit:
1. Elasticsearch and Kibana are co-located within a single Kubernetes Deployment (`elk`), taking only 1 pod slot.
2. Fluent Bit runs as 1 DaemonSet pod.
3. Non-essential Prometheus exporters (`kube-state-metrics` and `node-exporter`) were scaled down, keeping `prometheus-server` and `grafana` 100% healthy while staying strictly within 11/11 node pod capacity.

---

## 10. Security Considerations

- **Staging Authentication Scope**: Elasticsearch and Kibana authentication (`xpack.security.enabled=false`) is intentionally disabled for this staging/demonstration implementation.
- **Internal ClusterIP Isolation**: Neither Elasticsearch (9200) nor Kibana (5601) is exposed via NodePort, Ingress, ALB, or NLB. They remain strictly internal `ClusterIP` services accessible only within the cluster.
- **Production Requirements**: A production deployment must enable Elasticsearch/Kibana security (`xpack.security.enabled=true`) and use Kubernetes Secrets or an external secret operator (ESO) for credential management.
- **Git Hygiene**: No plaintext passwords, API keys, tokens, or private certificates are committed to the repository.

---

## 11. Cost & AWS Capacity Considerations

- **No AWS Managed Services**: No separate AWS managed logging service (such as AWS OpenSearch) was provisioned for Phase 4.8.
- **No Dedicated Infrastructure**: No additional AWS Load Balancer, EBS volume, or extra EKS worker node was provisioned specifically for Phase 4.8.
- **Existing Worker Capacity**: The ELK stack operates within the existing EKS worker node capacity (`t3.small`).
- **Standard AWS Charges**: Existing AWS charges for the EKS control plane and worker node instance still apply; Phase 4.8 is not "free", but avoids net-new AWS service costs.
- **Storage Trade-off**: Log storage utilizes ephemeral container layers. Logs do not persist if the `elk` pod is recreated, which is acceptable for staging demonstration.

---

## 12. Log Metadata & Index Strategy

- **Index Naming Scheme**: `nexvion-logs-YYYY.MM.DD`
- **Searchable Fields**:
  - `@timestamp` (ISO8601 UTC)
  - `message` (Log body)
  - `stream` (`stdout` / `stderr`)
  - `kubernetes.namespace_name`
  - `kubernetes.pod_name`
  - `kubernetes.container_name`
  - `kubernetes.host`

---

## 13. Installation Commands

```bash
# 1. Create logging namespace
kubectl create namespace logging --dry-run=client -o yaml | kubectl apply -f -

# 2. Apply ELK Stack and Fluent Bit manifests
kubectl apply -f helm/logging/elk-stack.yaml
kubectl apply -f helm/logging/fluent-bit.yaml

# 3. Verify rollout status
kubectl get pods -n logging
```

---

## 14. End-to-End Validation Commands

```bash
# Step A: Generate unique test log from Nexvion workload
kubectl exec -n nexvion deploy/nexvion-web -- sh -c 'echo "NEXVION_ELK_VERIFIED_LOG_20261004 - Centralized Logging End-to-End Validation Success"'
kubectl exec -n logging deploy/elk -c elasticsearch -- curl -s -H "User-Agent: NEXVION_ELK_VERIFIED_LOG_20261004" http://172.31.57.239:80/healthz

# Step B: Verify Elasticsearch index existence
kubectl exec -n logging deploy/elk -c elasticsearch -- curl -s "http://localhost:9200/_cat/indices?v"

# Step C: Query Elasticsearch for Nexvion workload log with metadata
kubectl exec -n logging deploy/elk -c elasticsearch -- curl -s "http://localhost:9200/nexvion-logs-*/_search?q=kubernetes.namespace_name:nexvion&pretty"

# Step D: Verify Kibana API status
kubectl exec -n logging deploy/elk -c kibana -- curl -s "http://localhost:5601/api/status"
```

---

## 15. Actual Validation Results

### A. Elasticsearch Index Verification
`_cat/indices` output:
```text
health status index                            uuid                   pri rep docs.count docs.deleted store.size pri.store.size
green  open   .geoip_databases                 64xGEGSLQCuYUggPiOL2KQ   1   0          9            0      8.3mb          8.3mb
yellow open   nexvion-logs-2026.10.03          NU99p12qTpGCdwwTw5X8QA   1   1       8789            0      2.7mb          2.7mb
green  open   .kibana_7.17.18_001              W3Fawk0pSz20g8t_N9q8Gw   1   0          3            0     16.6kb         16.6kb
```

### B. Nexvion Workload Test Log Query Result from Elasticsearch
`GET /nexvion-logs-*/_search?q=kubernetes.namespace_name:nexvion` response:
```json
{
  "took" : 312,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 1,
      "relation" : "eq"
    },
    "max_score" : 8.796262,
    "hits" : [
      {
        "_index" : "nexvion-logs-2026.10.03",
        "_type" : "_doc",
        "_id" : "briGA6EBgmwQnt_voXrt",
        "_score" : 8.796262,
        "_source" : {
          "@timestamp" : "2026-10-03T20:48:36.867Z",
          "stream" : "stdout",
          "logtag" : "F",
          "message" : "172.31.63.144 - - [03/Oct/2026:20:48:36 +0000] \"GET / HTTP/1.1\" 200 11710 \"-\" \"NEXVION_ELK_TEST_20261004_021800\" \"-\"",
          "kubernetes" : {
            "pod_name" : "nexvion-web-78d49686cd-jtvbw",
            "namespace_name" : "nexvion",
            "pod_id" : "8289a682-da00-420e-913f-b3966af1e993",
            "labels" : {
              "app" : "nexvion-web",
              "app_kubernetes_io/component" : "frontend",
              "app_kubernetes_io/instance" : "nexvion-web",
              "app_kubernetes_io/managed-by" : "Helm",
              "app_kubernetes_io/name" : "nexvion-web",
              "app_kubernetes_io/part-of" : "nexvion-platform",
              "app_kubernetes_io/version" : "1.0.0",
              "helm_sh/chart" : "nexvion-web-0.1.0"
            },
            "host" : "ip-172-31-59-164.ap-south-1.compute.internal",
            "container_name" : "nexvion-web",
            "container_image" : "677012863109.dkr.ecr.ap-south-1.amazonaws.com/nexvion-web:0d575d0"
          }
        }
      }
    ]
  }
}
```

### C. Kibana API Health Status
`GET /api/status` response:
```json
{
  "status": {
    "overall": {
      "state": "green",
      "title": "Green",
      "nickname": "Looking good",
      "icon": "success",
      "uiColor": "secondary"
    }
  }
}
```

---

## 16. Known Limitations

1. **Ephemeral Storage**: Logs are stored on pod overlay storage; recreating the `elk` pod resets index data.
2. **Single-Node Topology**: No Elasticsearch master/data redundancy (suitable for staging/demonstration only).
3. **Cluster Pod Limits**: Single `t3.small` worker capacity (`maxPods=11`) requires compact multi-container pod layouts.

---

## 17. Phase 4.8 Completion Status

Phase 4.8 Centralized Logging Implementation is **COMPLETE** and verified end-to-end on live AWS EKS.

---

## 18. Next Phase: Phase 4.9 — AI-Assisted Incident Analysis

The next phase will leverage centralized logs and metrics collected in Phase 4.7 and 4.8 to build automated incident analysis and triage workflows.
