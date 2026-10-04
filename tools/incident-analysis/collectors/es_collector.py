import json
import subprocess
import logging
from urllib.parse import quote

logger = logging.getLogger("es_collector")

def collect_es_logs(query_term=None, namespace="nexvion", limit=30, index_pattern="nexvion-logs-*"):
    """
    Collects logs from Elasticsearch by querying the internal cluster via kubectl exec on the logging pod.
    Returns structured log evidence including metadata and timestamps.
    """
    logs_data = {
        "index_pattern": index_pattern,
        "query_term": query_term,
        "total_hits": 0,
        "matched_logs": [],
        "error_count": 0,
        "warning_count": 0
    }

    # Build query string
    q_parts = []
    if namespace:
        q_parts.append(f"kubernetes.namespace_name:{namespace}")
    if query_term:
        q_parts.append(f"({query_term})")
    
    q_str = " AND ".join(q_parts) if q_parts else "*"
    encoded_q = quote(q_str)
    
    url = f"http://localhost:9200/{index_pattern}/_search?q={encoded_q}&size={limit}&sort=@timestamp:desc"

    cmd = [
        "kubectl", "exec", "-n", "logging", "deploy/elk", "-c", "elasticsearch", "--",
        "curl", "-s", url
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        resp_json = json.loads(res.stdout)
        
        hits_data = resp_json.get("hits", {})
        logs_data["total_hits"] = hits_data.get("total", {}).get("value", 0)
        
        for hit in hits_data.get("hits", []):
            src = hit.get("_source", {})
            msg = src.get("message", "")
            stream = src.get("stream", "")
            k8s_meta = src.get("kubernetes", {})
            
            msg_upper = str(msg).upper()
            if "ERROR" in msg_upper or "CRITICAL" in msg_upper or "EXCEPTION" in msg_upper or stream == "stderr":
                logs_data["error_count"] += 1
            elif "WARN" in msg_upper:
                logs_data["warning_count"] += 1
            
            logs_data["matched_logs"].append({
                "timestamp": src.get("@timestamp"),
                "pod_name": k8s_meta.get("pod_name"),
                "container_name": k8s_meta.get("container_name"),
                "namespace": k8s_meta.get("namespace_name"),
                "stream": stream,
                "message": msg
            })
            
    except Exception as e:
        logger.warning(f"Failed to query Elasticsearch logs: {e}")

    return logs_data
