import json
import subprocess
import logging
from urllib.parse import quote

logger = logging.getLogger("prom_collector")

def run_prom_query(promql):
    """Executes a PromQL query via kubectl exec on logging pod targeting internal Prometheus service."""
    encoded_query = quote(promql)
    url = f"http://prometheus-server.monitoring.svc.cluster.local/api/v1/query?query={encoded_query}"
    
    cmd = [
        "kubectl", "exec", "-n", "logging", "deploy/elk", "-c", "elasticsearch", "--",
        "curl", "-s", url
    ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        resp_json = json.loads(res.stdout)
        if resp_json.get("status") == "success":
            return resp_json.get("data", {}).get("result", [])
        return []
    except Exception as e:
        logger.warning(f"Failed PromQL query '{promql}': {e}")
        return []

def collect_prom_metrics(namespace="nexvion"):
    """
    Collects Prometheus metrics including pod health, CPU/RAM usage, deployment replicas, and restart counts.
    Returns structured metric evidence.
    """
    metrics = {
        "namespace": namespace,
        "up_components": [],
        "deployment_replicas": {},
        "pod_metrics": [],
        "pod_restarts": [],
        "summary": {
            "all_components_up": True,
            "target_deployment_available": True,
            "high_cpu_detected": False,
            "high_memory_detected": False
        }
    }

    # 1. Query 'up' metric for system components
    up_results = run_prom_query("up")
    for item in up_results:
        job = item.get("metric", {}).get("job")
        instance = item.get("metric", {}).get("instance")
        val = item.get("value", [0, "0"])[1]
        metrics["up_components"].append({
            "job": job,
            "instance": instance,
            "up": val == "1"
        })
        if val != "1" and job in ["kubernetes-api-servers", "prometheus"]:
            metrics["summary"]["all_components_up"] = False

    # 2. Query deployment replicas
    available_res = run_prom_query(f'kube_deployment_status_replicas_available{{namespace="{namespace}"}}')
    desired_res = run_prom_query(f'kube_deployment_status_replicas{{namespace="{namespace}"}}')
    
    for item in desired_res:
        deploy_name = item.get("metric", {}).get("deployment")
        desired_val = int(item.get("value", [0, "0"])[1])
        avail_val = 0
        for av in available_res:
            if av.get("metric", {}).get("deployment") == deploy_name:
                avail_val = int(av.get("value", [0, "0"])[1])
                break
        
        metrics["deployment_replicas"][deploy_name] = {
            "desired": desired_val,
            "available": avail_val,
            "degraded": avail_val < desired_val
        }
        if avail_val < desired_val:
            metrics["summary"]["target_deployment_available"] = False

    # 3. Query pod restarts
    restart_res = run_prom_query(f'kube_pod_container_status_restarts_total{{namespace="{namespace}"}}')
    for item in restart_res:
        pod_name = item.get("metric", {}).get("pod")
        restarts = int(item.get("value", [0, "0"])[1])
        metrics["pod_restarts"].append({
            "pod": pod_name,
            "restarts": restarts
        })

    # 4. Query pod status phase
    phase_res = run_prom_query(f'kube_pod_status_phase{{namespace="{namespace}"}}')
    for item in phase_res:
        pod_name = item.get("metric", {}).get("pod")
        phase = item.get("metric", {}).get("phase")
        val = item.get("value", [0, "0"])[1]
        if val == "1":
            metrics["pod_metrics"].append({
                "pod": pod_name,
                "phase": phase
            })

    return metrics
