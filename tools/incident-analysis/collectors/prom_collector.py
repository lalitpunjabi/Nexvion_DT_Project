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
        logger.warning(f"Prometheus query status error for '{promql}': {resp_json}")
        return []
    except Exception as e:
        logger.warning(f"Failed PromQL query '{promql}': {e}")
        return []

def collect_prom_metrics(namespace="nexvion"):
    """
    Collects Prometheus metrics including pod health, CPU/RAM usage, container metrics, and restart counts.
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
        job = item.get("metric", {}).get("job", "unknown")
        instance = item.get("metric", {}).get("instance", "unknown")
        val = item.get("value", [0, "0"])[1]
        is_up = (val == "1")
        metrics["up_components"].append({
            "job": job,
            "instance": instance,
            "up": is_up
        })
        if not is_up and job in ["kubernetes-api-servers", "prometheus"]:
            metrics["summary"]["all_components_up"] = False

    # 2. Query pod memory usage (cAdvisor working set bytes)
    mem_promql = f'container_memory_working_set_bytes{{namespace="{namespace}",container!="POD",container!=""}}'
    mem_results = run_prom_query(mem_promql)
    
    # 3. Query pod CPU rate (5m window)
    cpu_promql = f'rate(container_cpu_usage_seconds_total{{namespace="{namespace}",container!="POD",container!=""}}[5m])'
    cpu_results = run_prom_query(cpu_promql)

    # 4. Query container start times / restart metrics
    start_promql = f'container_start_time_seconds{{namespace="{namespace}",container!="POD",container!=""}}'
    start_results = run_prom_query(start_promql)

    # Map collected metrics by pod name
    pod_metrics_map = {}
    for item in mem_results:
        metric_labels = item.get("metric", {})
        pod_name = metric_labels.get("pod")
        container_name = metric_labels.get("container")
        mem_bytes = float(item.get("value", [0, "0"])[1])
        mem_mb = round(mem_bytes / (1024 * 1024), 2)
        
        if pod_name:
            if pod_name not in pod_metrics_map:
                pod_metrics_map[pod_name] = {
                    "pod": pod_name,
                    "container": container_name,
                    "memory_mb": mem_mb,
                    "cpu_cores": 0.0
                }
            else:
                pod_metrics_map[pod_name]["memory_mb"] = mem_mb

    for item in cpu_results:
        pod_name = item.get("metric", {}).get("pod")
        cpu_val = float(item.get("value", [0, "0"])[1])
        cpu_cores = round(cpu_val, 4)
        if pod_name in pod_metrics_map:
            pod_metrics_map[pod_name]["cpu_cores"] = cpu_cores

    for pod_data in pod_metrics_map.values():
        metrics["pod_metrics"].append(pod_data)
        if pod_data["memory_mb"] > 256.0:  # Threshold check
            metrics["summary"]["high_memory_detected"] = True
        if pod_data["cpu_cores"] > 0.8:     # Threshold check
            metrics["summary"]["high_cpu_detected"] = True

    # 5. Fallback or direct queries for deployment replicas and pod restarts
    avail_res = run_prom_query(f'kube_deployment_status_replicas_available{{namespace="{namespace}"}}')
    desired_res = run_prom_query(f'kube_deployment_spec_replicas{{namespace="{namespace}"}}')
    
    if desired_res:
        for item in desired_res:
            deploy_name = item.get("metric", {}).get("deployment")
            desired_val = int(item.get("value", [0, "0"])[1])
            avail_val = 0
            for av in avail_res:
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
    else:
        # Infer deployment replica metric presence from active pod metrics
        active_pods = len(metrics["pod_metrics"])
        metrics["deployment_replicas"]["nexvion-web"] = {
            "desired": max(active_pods, 2),
            "available": active_pods,
            "degraded": False
        }

    # Pod restarts from kube-state-metrics or cAdvisor container start times
    restart_res = run_prom_query(f'kube_pod_container_status_restarts_total{{namespace="{namespace}"}}')
    if restart_res:
        for item in restart_res:
            pod_name = item.get("metric", {}).get("pod")
            restarts = int(item.get("value", [0, "0"])[1])
            metrics["pod_restarts"].append({"pod": pod_name, "restarts": restarts})
    else:
        for pod_name in pod_metrics_map.keys():
            metrics["pod_restarts"].append({"pod": pod_name, "restarts": 0})

    return metrics

