def calculate_severity(k8s_state, es_logs, prom_metrics, primary_classification):
    """
    Calculates incident severity based on project-defined rules:
    - CRITICAL: Complete outage, 0 ready replicas, persistent CrashLoopBackOff across all pods.
    - HIGH: Partial degradation, available < desired replicas, active OOMKilled / Container failures.
    - MEDIUM: Error logs present with healthy workload replicas available, minor pod restarts.
    - LOW: Isolated warnings, non-impacting transient events.
    - INFO: Controlled demonstration test or informational event without production impact.
    """
    pods_summary = k8s_state.get("summary", {})
    total_pods = pods_summary.get("total_pods", 0)
    ready_pods = pods_summary.get("ready_pods", 0)
    total_restarts = pods_summary.get("total_restarts", 0)
    warning_events = pods_summary.get("warning_event_count", 0)
    es_errors = es_logs.get("error_count", 0)
    
    # Check if this is a controlled demonstration test
    matched_msgs = " ".join([l.get("message", "") for l in es_logs.get("matched_logs", [])])
    is_demo = "NEXVION_AI_INCIDENT_DEMO" in matched_msgs or "DEMO" in matched_msgs.upper()

    # Outage checks
    if total_pods > 0 and ready_pods == 0:
        return "CRITICAL", "Total workload outage: 0 ready pods available in namespace."

    if primary_classification in ["CrashLoopBackOff", "Deployment Failure"] and ready_pods == 0:
        return "CRITICAL", "Complete workload deployment failure with no active serving replicas."

    # High severity checks
    if total_pods > 0 and ready_pods < total_pods:
        return "HIGH", f"Degraded workload capacity: {ready_pods}/{total_pods} pods are ready."

    if total_restarts > 5 or primary_classification in ["Container Failure", "CrashLoopBackOff"]:
        return "HIGH", f"Elevated container failures detected ({total_restarts} restarts)."

    # Medium severity checks
    if es_errors > 0 or warning_events > 0:
        if is_demo:
            return "MEDIUM", f"Simulated incident evidence detected ({es_errors} error log entries)."
        return "MEDIUM", f"Application error logs or warning events detected ({es_errors} errors, {warning_events} events)."

    # Low / Info severity
    if es_logs.get("warning_count", 0) > 0:
        return "LOW", "Minor warning logs detected with healthy workload capacity."

    if is_demo:
        return "INFO", "Controlled demonstration scenario with no production impact."

    return "INFO", "Informational event: All workloads healthy and operating normally."
