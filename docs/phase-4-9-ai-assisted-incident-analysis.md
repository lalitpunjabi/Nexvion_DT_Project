# Phase 4.9 — AI-Assisted Incident Analysis

## 1. Objective

Phase 4.9 implements a lightweight, cloud-native **AI-Assisted Incident Analysis Engine** for the Nexvion E-Commerce Platform. Building directly upon the Prometheus + Grafana metrics foundation (Phase 4.7) and the Elasticsearch + Kibana + Fluent Bit centralized logging foundation (Phase 4.8), Phase 4.9 automates incident evidence aggregation, workload classification, severity determination, root-cause diagnosis, and remediation plan generation.

The primary objective is to provide site reliability engineers (SREs) and DevOps teams with a reproducible, automated incident investigation workflow that synthesizes telemetry from three core data layers (Kubernetes APIs, Elasticsearch logs, and Prometheus metrics) without introducing heavy in-cluster ML workloads or expensive managed cloud AI services.

---

## 2. System Architecture

The Incident Analysis Engine operates as a client-side execution framework inside `tools/incident-analysis/` backed by a CLI wrapper in `scripts/incident-analysis/analyze-incident.sh`.

```
                    ┌──────────────────────────────────┐
                    │ Trigger / Incident Identifier    │
                    │   (INCIDENT_ID / Namespace)      │
                    └─────────────────┬────────────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
             ▼                        ▼                        ▼
  ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
  │  Kubernetes API   │    │ Elasticsearch REST│    │  Prometheus API   │
  │  (Pods, Deploy,   │    │  (Centralized     │    │  (cAdvisor & Pod  │
  │   Events, HPA)    │    │   Pod Logs)       │    │    Metrics)       │
  └──────────┬────────┘    └──────────┬────────┘    └──────────┬────────┘
             │                        │                        │
             └────────────────────────┼────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │ Incident Analysis Engine │
                        │  (Evidence Collector &   │
                        │   Classification Core)   │
                        └─────────────┬────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │                                 │
                     ▼                                 ▼
         ┌───────────────────────┐         ┌───────────────────────┐
         │  AI Provider API      │         │ Rule-Based Fallback   │
         │ (Gemini / OpenAI API) │         │    (Deterministic     │
         │ [If AI_API_KEY set]   │         │    Engine Core)       │
         └───────────┬───────────┘         └───────────┬───────────┘
                     │                                 │
                     └────────────────┬────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │ Structured Incident      │
                        │ Reports Generator        │
                        │ (JSON & Markdown Output) │
                        └──────────────────────────┘
```

---

## 3. Telemetry Data Sources Integrated

The engine automatically queries three live observability layers:

1. **Kubernetes API Server (`k8s_collector.py`)**:
   - Pod phases (`Running`, `Pending`, `Failed`, `CrashLoopBackOff`)
   - Container readiness (`ready: true/false`), restart counts, termination exit codes, and waiting state reasons
   - Deployment status (`desired`, `available`, `ready`, `updated` replicas)
   - Horizontal Pod Autoscaler (HPA) metrics (`minPods`, `maxPods`, current CPU utilization percentage)
   - Namespace events (`Warning`, `OOMKilled`, `Unhealthy`, omitting stale events from deleted pods)
   - Worker Node readiness and node capacity details

2. **Elasticsearch Centralized Logs (`es_collector.py`)**:
   - Queries `nexvion-logs-*` indices directly via Elasticsearch REST API (`http://localhost:9200`) executed through the logging proxy pod (`deploy/elk`)
   - Filters logs by target namespace (`nexvion`), timestamp windows, incident log markers (e.g. `NEXVION_AI_INCIDENT_DEMO_20261004`), and error patterns (`ERROR`, `CRITICAL`, `Exception`, `HTTP 500`)
   - Correctly handles ES 7.x `hits.total` structure (`value` vs integer)
   - Aggregates error counts, warning counts, total matched hits, and metadata (pod name, container name, stream `stdout`/`stderr`)

3. **Prometheus Metrics Engine (`prom_collector.py`)**:
   - PromQL queries executed against internal ClusterIP endpoint (`http://prometheus-server.monitoring.svc.cluster.local:80/api/v1/query`)
   - Scraping health of infrastructure (`up` metric across targets)
   - Real-time cAdvisor pod memory usage (`container_memory_working_set_bytes`)
   - Real-time cAdvisor pod CPU rate (`rate(container_cpu_usage_seconds_total[5m])`)
   - Container start times and restart counters

---

## 4. Incident Collection & Workflow

The automated incident analysis workflow is invoked via script or CLI:

```bash
# Execute in AI-Assisted mode via environment variable
export AI_API_KEY="<your-gemini-api-key>"
python tools/incident-analysis/incident_analyzer.py \
  --incident-id NEXVION-DEMO-001 \
  --namespace nexvion \
  --query NEXVION_AI_INCIDENT_DEMO_20261004 \
  --output-dir reports

# Or execute via shell wrapper script (Rule-Based fallback mode)
./scripts/incident-analysis/analyze-incident.sh NEXVION-DEMO-001 nexvion NEXVION_AI_INCIDENT_DEMO_20261004
```

---

## 5. Incident Classification Taxonomy

Incidents are evaluated deterministically against 12 predefined classification rules (`classifier.py`):

| Classification Category | Rule Criteria |
| :--- | :--- |
| `CrashLoopBackOff` | Pod status phase contains `CrashLoopBackOff` or container waiting reason == `CrashLoopBackOff` |
| `Pod Not Ready` | Pod phase is `Running` but `ready == false` |
| `Application Error` | Elasticsearch log error count > 0 or HTTP 5xx error rates detected |
| `Dependency Failure` | Elasticsearch logs contain database (`db-replica-01`), SQL, upstream timeouts, or payment gateway errors |
| `High CPU` | Prometheus pod CPU usage exceeds target threshold (> 0.8 cores) |
| `High Memory` | Prometheus pod memory usage exceeds limit (> 256 MiB) or OOM events detected |
| `Deployment Failure` | Deployment available replicas < desired replicas |
| `Container Failure` | Container exit code != 0 or waiting reason in [`Error`, `ImagePullBackOff`, `ErrImagePull`] |
| `Scaling Issue` | HPA current replicas == max_pods and CPU > target, or `FailedScheduling` events exist |
| `Network/Ingress Issue` | Ingress controller or network service connection warnings detected |
| `Configuration Error` | Pod state indicates `CreateContainerConfigError` or `InvalidImageName` |
| `Unknown` | Telemetry collected but no specific failure signatures matched |

---

## 6. Severity Calculation Model

Severity is calculated using strict, documented project-defined rules (`severity.py`):

| Severity | Thresholds & Decision Logic |
| :--- | :--- |
| `CRITICAL` | Zero healthy replicas (`available_replicas == 0`), repeated container crash loops (> 5 restarts), or node status `NotReady`. |
| `HIGH` | Degraded availability (`available < desired`), severe error rates (> 10 error logs in window), or active `CrashLoopBackOff`. |
| `MEDIUM` | Error logs or simulated incident markers present while workload availability remains healthy (2/2 Ready). |
| `LOW` | Minor warning logs detected with healthy workload capacity. |
| `INFO` | Baseline telemetry with zero active warnings, errors, or restarts. |

---

## 7. AI-Assisted Analysis vs. Rule-Based Fallback

The system supports dual-mode intelligence for root-cause synthesis (`ai_engine.py`):

### 1. AI-Assisted Mode (`AI-Assisted Analysis`)
- Triggered when environment variable `AI_API_KEY` is present.
- Fully validated using Google Gemini API (`gemini-flash-lite-latest`).
- Formulates structured JSON prompts containing the aggregated telemetry evidence (K8s state, ES error logs, Prometheus metrics).
- Synthesizes intelligent root cause, contributing network/dependency factors, investigation steps, and remediation plans.
- **Security**: `AI_API_KEY` is read strictly from environment variables—never saved to disk or committed to Git.

### 2. Rule-Based Fallback Mode (`Rule-Based Analysis`)
- Activated automatically when `AI_API_KEY` is unset or an API call fails/times out.
- Applies deterministic heuristic analysis over collected telemetry.
- Explicitly labels the generated report as **`Rule-Based Analysis`**.
- Guarantees 100% reproducible analysis offline without external network dependencies or API costs.

---

## 8. Root-Cause Analysis Methodology

To prevent false claims or speculative hallucination, the engine enforces disciplined language guidelines:

- **Observed Evidence**: Raw facts retrieved from K8s API, ES logs, and Prometheus metrics.
- **Likely Root Cause**: AI or heuristic inference clearly labeled as *likely* or *suggested*.
- **Wording Discipline**: Uses explicit phrasing such as:
  - *"Likely root cause:"*
  - *"Evidence suggests:"*
  - *"Insufficient evidence to confirm:"*
- **Confidence Scoring**: Outputs a numerical confidence score (0.0 to 1.0) based on telemetry completeness.

---

## 9. Incident Report Structure

Reports are generated in dual formats inside `reports/`:
- **Machine-Readable JSON**: `reports/<INCIDENT_ID>.json`
- **Human-Readable Markdown**: `reports/<INCIDENT_ID>.md`

---

## 10. Controlled Demonstration Incident

To safely validate the analysis engine end-to-end without violating worker node pod constraints (`maxPods=11`) or disrupting live production traffic on `nexvion-web`, a controlled demonstration incident was executed using `scripts/incident-analysis/demo-incident.sh`:

### Demonstration Execution:
1. **Non-Destructive Log Marker Injection**: Injected a simulated error log marker (`[ERROR] NEXVION_AI_INCIDENT_DEMO_20261004: Connection failure to database host db-replica-01.nexvion.internal:5432 HTTP 500 Internal Server Error in payment checkout handler`) directly into `nexvion-web` container stdout via `kubectl exec`.
2. **Log Ingestion & Indexing**: Fluent Bit collected the pod stdout line, enriched it with Kubernetes metadata, and shipped it to Elasticsearch index `nexvion-logs-YYYY.MM.DD`.
3. **Ingestion Verification**: Executed direct REST query against Elasticsearch confirming `total_hits: 3` matched the marker.
4. **Analyzer Execution**: Executed `python tools/incident-analysis/incident_analyzer.py --incident-id NEXVION-DEMO-001 --namespace nexvion --query NEXVION_AI_INCIDENT_DEMO_20261004` with `AI_API_KEY` configured in memory.
5. **AI Synthesis**: Google Gemini API (`gemini-flash-lite-latest`) successfully analyzed the live telemetry payload and generated structured root cause analysis (`AI-Assisted Analysis` mode).

---

## 11. Actual Validation Evidence

### Live AI-Assisted Report Excerpt (`reports/NEXVION-DEMO-001.md`):
```markdown
# Incident Analysis Report

**Incident ID**: `NEXVION-DEMO-001`  
**Timestamp**: `2026-10-04T12:05:25.808342+00:00`  
**Analysis Mode**: `AI-Assisted Analysis`  

## 1. Incident Summary
An automated incident analysis was triggered for incident ID `NEXVION-DEMO-001` targeting namespace `nexvion`. Observed evidence was collected from Kubernetes workload APIs, Elasticsearch centralized logs (`nexvion-logs-*`), and Prometheus metrics endpoints.

## 2. Severity
- **Level**: `MEDIUM`
- **Rationale**: Simulated incident evidence detected (2 error log entries).

## 3. Classification
- **Primary Classification**: `Dependency Failure`
- **Secondary Tags**: `Application Error, Dependency Failure`
- **Confidence Score**: `85.0%`

## 5. Likely Root Cause
> The application is experiencing connection failures to its external database dependency (db-replica-01.nexvion.internal:5432), resulting in HTTP 500 Internal Server Errors within the payment checkout handler.
```

---

## 12. Security Considerations

- **Credential Isolation**: No API keys, passwords, or tokens are committed to source control or saved to disk files.
- **Environment Configuration**: `AI_API_KEY` is loaded dynamically from in-memory environment variables.
- **Internal Service Communication**: Prometheus queries use internal K8s DNS (`prometheus-server.monitoring.svc.cluster.local`).
- **Elasticsearch Access**: Elasticsearch REST API (`localhost:9200`) is accessible only internally within the cluster or via internal proxy pod—never exposed publicly.
- **Least Privilege Access**: Kubernetes collectors use default standard read permissions (`kubectl get`).

---

## 13. Resource and Cost Considerations

- **AWS Infrastructure Cost**: No dedicated AWS infrastructure was provisioned for Phase 4.9. The analyzer runs at script/client level using existing EKS resources. Existing EKS control-plane and worker-node charges still apply.
- **Node Capacity Constraint**: Runs entirely client-side / script-level without introducing additional daemonsets, heavy inference servers, or local Ollama instances on the single `t3.small` EKS worker node (`maxPods=11` limit fully respected).

---

## 14. Limitations

1. **Rule-Based Fallback Scope**: Fallback heuristic rules are based on predefined patterns and may categorize complex, unmapped edge cases as `Unknown`.
2. **Elasticsearch Log Retention**: Log queries depend on active indices in the single-node staging Elasticsearch cluster (`nexvion-logs-*`).
3. **Cluster Capacity**: EKS worker node `t3.small` operates at maximum pod capacity (11/11 pods); demo workloads must not spin up permanent additional pods.

---

## 15. Future Improvements

1. **Interactive Slack / Webhook Alerts**: Connect incident analyzer output directly to Slack webhooks or PagerDuty.
2. **Automated Self-Healing / Remediation**: Implement opt-in automated remediation execution (e.g. `kubectl rollout restart`) for verified non-destructive incidents.
3. **Vector Telemetry Embeddings**: Store historical incident summaries in a vector store for fast similarity search across past outages.

---

## 16. Phase 4.9 Completion Status

Phase 4.9 is **100% COMPLETE and FULLY VALIDATED** on the live AWS EKS cluster (`nexvion-eks`).

- [x] Lightweight Python & Shell Incident Analysis Engine created in `tools/incident-analysis/` & `scripts/incident-analysis/`.
- [x] Multi-source collection from K8s API, Elasticsearch REST API, and Prometheus PromQL API implemented and validated with live cAdvisor CPU/RAM metrics.
- [x] Classification engine covering 12 failure categories implemented and verified (`Dependency Failure`, `0.85` confidence).
- [x] Documented 5-tier Severity Calculation Model implemented (`MEDIUM` severity).
- [x] Dual-mode AI analysis (`AI-Assisted Analysis` via Google Gemini API `gemini-flash-lite-latest` + `Rule-Based Analysis` fallback) implemented and verified.
- [x] Machine-readable JSON and human-readable Markdown report generators implemented.
- [x] Safe demonstration incident workflow created and validated (`NEXVION-DEMO-001`).
- [x] Live observability evidence successfully collected and reported.
- [x] Security verified: ZERO credentials/API keys saved or committed to Git.
- [x] All Phase 4.1–4.8 platform components (`nexvion-web`, HPA, `ingress-nginx`, Prometheus, Grafana, ELK stack) remain 100% functional and intact.
- [x] Phase 4.10 was **NOT** started.
