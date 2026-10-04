import os

def generate_md_report(data, output_path):
    """
    Generates human-readable Markdown incident analysis report adhering strictly to Requirement #10.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    incident_id = data.get("incident_id", "NEXVION-INCIDENT")
    timestamp = data.get("timestamp", "")
    analysis_mode = data.get("analysis_mode", "Rule-Based Analysis")
    severity = data.get("severity", "UNKNOWN")
    severity_reason = data.get("severity_reason", "")
    classification = data.get("classification", "Unknown")
    secondary_tags = ", ".join(data.get("secondary_tags", []))
    confidence = f"{float(data.get('confidence', 0.5)) * 100:.1f}%"
    
    k8s = data.get("evidence", {}).get("k8s_state", {})
    es = data.get("evidence", {}).get("es_logs", {})
    prom = data.get("evidence", {}).get("prom_metrics", {})
    
    analysis = data.get("analysis", {})
    root_cause = analysis.get("likely_root_cause", "Under investigation")
    factors = analysis.get("contributing_factors", [])
    investigation = analysis.get("investigation_steps", [])
    remediation = analysis.get("recommended_remediation", [])
    verification = analysis.get("verification_plan", [])
    limitations = analysis.get("limitations", [])

    # Format Pod Table
    pod_rows = []
    for p in k8s.get("pods", []):
        pod_rows.append(f"| `{p.get('name')}` | `{p.get('phase')}` | `{p.get('ready')}` | `{p.get('restarts')}` | `{p.get('node')}` |")
    pod_table = "\n".join(pod_rows) if pod_rows else "| No pods evaluated | - | - | - | - |"

    # Format ES Logs
    log_rows = []
    for l in es.get("matched_logs", [])[:5]:
        log_rows.append(f"- **[{l.get('timestamp')}]** `{l.get('pod_name')}` ({l.get('stream')}): `{l.get('message')}`")
    log_section = "\n".join(log_rows) if log_rows else "- No relevant error/warning logs found."

    # Format Factors & Steps
    factors_list = "\n".join([f"- {f}" for f in factors]) if factors else "- None identified."
    investigation_list = "\n".join([f"{step}" if step.startswith("1") or step.startswith("2") or step.startswith("3") else f"- {step}" for step in investigation])
    remediation_list = "\n".join([f"{step}" if step.startswith("1") or step.startswith("2") or step.startswith("3") else f"- {step}" for step in remediation])
    verification_list = "\n".join([f"{step}" if step.startswith("1") or step.startswith("2") or step.startswith("3") else f"- {step}" for step in verification])
    limitations_list = "\n".join([f"- {l}" for l in limitations])

    content = f"""# Incident Analysis Report

**Incident ID**: `{incident_id}`  
**Timestamp**: `{timestamp}`  
**Analysis Mode**: `{analysis_mode}`  

---

## 1. Incident Summary
An automated incident analysis was triggered for incident ID `{incident_id}` targeting namespace `{k8s.get('namespace', 'nexvion')}`. Observed evidence was collected from Kubernetes workload APIs, Elasticsearch centralized logs (`nexvion-logs-*`), and Prometheus metrics endpoints.

---

## 2. Severity
- **Level**: `{severity}`
- **Rationale**: {severity_reason}

---

## 3. Classification
- **Primary Classification**: `{classification}`
- **Secondary Tags**: `{secondary_tags if secondary_tags else 'None'}`
- **Confidence Score**: `{confidence}`

---

## 4. Observed Evidence

### A. Kubernetes Workload State
- **Namespace**: `{k8s.get('namespace')}`
- **Total Pods**: `{k8s.get('summary', {}).get('total_pods')}` | **Ready Pods**: `{k8s.get('summary', {}).get('ready_pods')}` | **Total Restarts**: `{k8s.get('summary', {}).get('total_restarts')}`
- **Warning Events**: `{k8s.get('summary', {}).get('warning_event_count')}`

| Pod Name | Phase | Ready | Restarts | Node |
| :--- | :--- | :--- | :--- | :--- |
{pod_table}

### B. Elasticsearch Centralized Logs
- **Index Pattern**: `{es.get('index_pattern')}`
- **Total Matched Hits**: `{es.get('total_hits')}`
- **Error Count**: `{es.get('error_count')}` | **Warning Count**: `{es.get('warning_count')}`

**Sample Log Records**:
{log_section}

### C. Prometheus Metrics
- **System Components Status**: `{'Healthy' if prom.get('summary', {}).get('all_components_up') else 'Degraded'}`
- **Target Deployment Available**: `{'Yes' if prom.get('summary', {}).get('target_deployment_available') else 'No'}`
- **High Resource Usage**: CPU: `{'Yes' if prom.get('summary', {}).get('high_cpu_detected') else 'No'}`, Memory: `{'Yes' if prom.get('summary', {}).get('high_memory_detected') else 'No'}`

---

## 5. Likely Root Cause
> {root_cause}

---

## 6. Contributing Factors
{factors_list}

---

## 7. Recommended Investigation Steps
{investigation_list}

---

## 8. Recommended Remediation
{remediation_list}

---

## 9. Verification Plan
{verification_list}

---

## 10. Observability References
- **Elasticsearch Index**: `nexvion-logs-*` (Namespace: `{k8s.get('namespace')}`)
- **Prometheus PromQL Queries**: `up`, `kube_deployment_status_replicas_available`, `kube_pod_container_status_restarts_total`
- **Grafana Dashboard**: `Nexvion EKS Platform Observability`

---

## 11. Limitations
{limitations_list}
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return output_path
