import json
import subprocess
import logging

logger = logging.getLogger("k8s_collector")

def run_kubectl(args):
    """Executes a kubectl command and returns parsed JSON output or raw stdout."""
    cmd = ["kubectl"] + args
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if "-o" in args and args.index("-o") + 1 < len(args) and args[args.index("-o") + 1] == "json":
            return json.loads(res.stdout)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.warning(f"kubectl command {' '.join(cmd)} failed: {e.stderr.strip()}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from kubectl command output: {e}")
        return None

def collect_k8s_state(namespace="nexvion", include_all_namespaces=True):
    """
    Collects Kubernetes workload state including Pods, Deployments, HPA, Events, and Node status.
    Returns a structured dictionary of observed K8s state.
    """
    state = {
        "namespace": namespace,
        "pods": [],
        "deployments": [],
        "hpa": [],
        "events": [],
        "nodes": [],
        "summary": {
            "total_pods": 0,
            "ready_pods": 0,
            "failed_pods": 0,
            "total_restarts": 0,
            "warning_event_count": 0,
            "node_count": 0,
            "node_ready_count": 0
        }
    }

    # 1. Collect Pods
    pod_args = ["get", "pods", "-n", namespace, "-o", "json"]
    pod_data = run_kubectl(pod_args)
    if pod_data and "items" in pod_data:
        for item in pod_data["items"]:
            pod_name = item["metadata"]["name"]
            phase = item.get("status", {}).get("phase", "Unknown")
            container_statuses = item.get("status", {}).get("containerStatuses", [])
            
            restarts = 0
            ready = False
            container_details = []
            
            for cs in container_statuses:
                restarts += cs.get("restartCount", 0)
                if cs.get("ready"):
                    ready = True
                
                state_info = cs.get("state", {})
                waiting = state_info.get("waiting", {})
                terminated = state_info.get("terminated", {})
                
                container_details.append({
                    "name": cs.get("name"),
                    "ready": cs.get("ready", False),
                    "restart_count": cs.get("restartCount", 0),
                    "waiting_reason": waiting.get("reason"),
                    "waiting_message": waiting.get("message"),
                    "terminated_reason": terminated.get("reason"),
                    "exit_code": terminated.get("exitCode")
                })
            
            state["pods"].append({
                "name": pod_name,
                "phase": phase,
                "ready": ready,
                "restarts": restarts,
                "containers": container_details,
                "node": item.get("spec", {}).get("nodeName")
            })
            
            state["summary"]["total_pods"] += 1
            if ready:
                state["summary"]["ready_pods"] += 1
            else:
                state["summary"]["failed_pods"] += 1
            state["summary"]["total_restarts"] += restarts

    # 2. Collect Deployments
    deploy_args = ["get", "deployment", "-n", namespace, "-o", "json"]
    deploy_data = run_kubectl(deploy_args)
    if deploy_data and "items" in deploy_data:
        for item in deploy_data["items"]:
            status = item.get("status", {})
            spec = item.get("spec", {})
            state["deployments"].append({
                "name": item["metadata"]["name"],
                "desired_replicas": spec.get("replicas", 0),
                "available_replicas": status.get("availableReplicas", 0),
                "ready_replicas": status.get("readyReplicas", 0),
                "updated_replicas": status.get("updatedReplicas", 0)
            })

    # 3. Collect HPA
    hpa_args = ["get", "hpa", "-n", namespace, "-o", "json"]
    hpa_data = run_kubectl(hpa_args)
    if hpa_data and "items" in hpa_data:
        for item in hpa_data["items"]:
            status = item.get("status", {})
            spec = item.get("spec", {})
            state["hpa"].append({
                "name": item["metadata"]["name"],
                "min_pods": spec.get("minReplicas"),
                "max_pods": spec.get("maxReplicas"),
                "current_replicas": status.get("currentReplicas"),
                "desired_replicas": status.get("desiredReplicas"),
                "current_metrics": status.get("currentMetrics", [])
            })

    # 4. Collect Warning Events
    event_args = ["get", "events", "-n", namespace, "--sort-by=.metadata.creationTimestamp", "-o", "json"]
    event_data = run_kubectl(event_args)
    if event_data and "items" in event_data:
        for item in event_data["items"]:
            event_type = item.get("type", "Normal")
            reason = item.get("reason", "")
            message = item.get("message", "")
            component = item.get("involvedObject", {}).get("name", "")
            
            # Omit stale events from deleted temporary demo pods
            if "demo-incident-pod" in component:
                continue

            if event_type == "Warning" or reason in ["OOMKilled", "BackOff", "FailedScheduling", "Unhealthy", "Killing"]:
                state["events"].append({
                    "type": event_type,
                    "reason": reason,
                    "object": component,
                    "message": message,
                    "timestamp": item.get("lastTimestamp") or item.get("firstTimestamp")
                })
                state["summary"]["warning_event_count"] += 1

    # 5. Collect Node Status
    node_args = ["get", "nodes", "-o", "json"]
    node_data = run_kubectl(node_args)
    if node_data and "items" in node_data:
        for item in node_data["items"]:
            node_name = item["metadata"]["name"]
            status_conditions = item.get("status", {}).get("conditions", [])
            is_ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in status_conditions)
            
            state["nodes"].append({
                "name": node_name,
                "ready": is_ready,
                "instance_type": item.get("metadata", {}).get("labels", {}).get("node.kubernetes.io/instance-type", "unknown")
            })
            state["summary"]["node_count"] += 1
            if is_ready:
                state["summary"]["node_ready_count"] += 1

    return state
