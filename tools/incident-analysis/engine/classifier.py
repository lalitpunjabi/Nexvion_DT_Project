import re

VALID_CLASSIFICATIONS = [
    "Application Error",
    "Container Failure",
    "CrashLoopBackOff",
    "Pod Not Ready",
    "High CPU",
    "High Memory",
    "Deployment Failure",
    "Scaling Issue",
    "Network/Ingress Issue",
    "Dependency Failure",
    "Configuration Error",
    "Unknown"
]

def classify_incident(k8s_state, es_logs, prom_metrics):
    """
    Classifies the incident based on concrete evidence gathered from K8s, ES logs, and Prometheus metrics.
    Returns (primary_classification, list_of_secondary_tags, confidence_score).
    """
    tags = []
    
    # Check K8s Pods for CrashLoopBackOff & Container Failures
    has_crashloop = False
    has_oom = False
    has_container_failure = False
    has_not_ready = False
    
    for pod in k8s_state.get("pods", []):
        if not pod.get("ready"):
            has_not_ready = True
        for c in pod.get("containers", []):
            reason = c.get("waiting_reason") or c.get("terminated_reason") or ""
            if "CrashLoopBackOff" in reason:
                has_crashloop = True
            if "OOMKilled" in reason:
                has_oom = True
            if c.get("exit_code") and c.get("exit_code") != 0:
                has_container_failure = True
                
    if has_crashloop:
        tags.append("CrashLoopBackOff")
    if has_oom:
        tags.append("High Memory")
        tags.append("Container Failure")
    if has_container_failure:
        tags.append("Container Failure")
    if has_not_ready:
        tags.append("Pod Not Ready")

    # Check Deployments
    for dep in k8s_state.get("deployments", []):
        if dep.get("available_replicas", 0) < dep.get("desired_replicas", 0):
            tags.append("Deployment Failure")

    # Check ES Log messages
    log_messages = [log.get("message", "") for log in es_logs.get("matched_logs", [])]
    all_logs_text = " ".join(log_messages).lower()
    
    if "connection refused" in all_logs_text or "timeout" in all_logs_text or "502 bad gateway" in all_logs_text:
        tags.append("Network/Ingress Issue")
        
    if "database" in all_logs_text or "sql" in all_logs_text or "upstream" in all_logs_text or "payment-gateway" in all_logs_text:
        tags.append("Dependency Failure")
        
    if "error" in all_logs_text or "exception" in all_logs_text or "failed" in all_logs_text or "500" in all_logs_text:
        tags.append("Application Error")

    if "cpu" in all_logs_text or prom_metrics.get("summary", {}).get("high_cpu_detected"):
        tags.append("High CPU")

    # Determine Primary Classification
    primary = "Unknown"
    confidence = 0.5

    if "CrashLoopBackOff" in tags:
        primary = "CrashLoopBackOff"
        confidence = 0.95
    elif "Deployment Failure" in tags:
        primary = "Deployment Failure"
        confidence = 0.90
    elif "Container Failure" in tags:
        primary = "Container Failure"
        confidence = 0.90
    elif "Dependency Failure" in tags:
        primary = "Dependency Failure"
        confidence = 0.85
    elif "Application Error" in tags:
        primary = "Application Error"
        confidence = 0.85
    elif "Network/Ingress Issue" in tags:
        primary = "Network/Ingress Issue"
        confidence = 0.80
    elif "Pod Not Ready" in tags:
        primary = "Pod Not Ready"
        confidence = 0.80
    elif "High CPU" in tags:
        primary = "High CPU"
        confidence = 0.75
    elif "High Memory" in tags:
        primary = "High Memory"
        confidence = 0.75

    return primary, list(set(tags)), confidence
