import sys
import os
import argparse
import datetime
import logging

# Ensure local imports work when executing script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.k8s_collector import collect_k8s_state
from collectors.es_collector import collect_es_logs
from collectors.prom_collector import collect_prom_metrics
from engine.classifier import classify_incident
from engine.severity import calculate_severity
from engine.ai_engine import analyze_incident_with_ai_or_fallback
from reporters.json_reporter import generate_json_report
from reporters.md_reporter import generate_md_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("incident_analyzer")

def load_env_file():
    """Loads environment variables from local .env file if present and not already set."""
    env_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and not os.getenv(k):
                                os.environ[k] = v
            except Exception:
                pass

load_env_file()

def run_incident_analysis(incident_id, namespace="nexvion", query=None, output_dir="reports"):
    """
    Main incident analysis pipeline. Collects K8s, ES, and Prometheus evidence,
    executes classification, severity, and AI/rule-based analysis, and outputs JSON & MD reports.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logger.info(f"Starting Incident Analysis for Incident ID: '{incident_id}' (Namespace: '{namespace}')")

    # 1. Collect Evidence
    logger.info("1/3 Collecting Kubernetes workload state...")
    k8s_state = collect_k8s_state(namespace=namespace)

    logger.info("2/3 Collecting Elasticsearch centralized logs...")
    es_query = query if query else "error OR warning OR NEXVION_AI_INCIDENT_DEMO"
    es_logs = collect_es_logs(query_term=es_query, namespace=namespace)

    logger.info("3/3 Collecting Prometheus metrics...")
    prom_metrics = collect_prom_metrics(namespace=namespace)

    # 2. Classify Incident & Determine Severity
    primary_classification, secondary_tags, confidence = classify_incident(k8s_state, es_logs, prom_metrics)
    severity, severity_reason = calculate_severity(k8s_state, es_logs, prom_metrics, primary_classification)

    logger.info(f"Classification: '{primary_classification}' | Severity: '{severity}' | Confidence: {confidence:.2f}")

    # 3. Execute AI / Rule-Based Root Cause Analysis
    analysis_result = analyze_incident_with_ai_or_fallback(
        incident_id=incident_id,
        k8s_state=k8s_state,
        es_logs=es_logs,
        prom_metrics=prom_metrics,
        primary_classification=primary_classification,
        severity=severity,
        severity_reason=severity_reason,
        confidence=confidence
    )

    # 4. Build Unified Report Payload
    report_payload = {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "namespace": namespace,
        "analysis_mode": analysis_result.get("analysis_mode", "Rule-Based Analysis"),
        "severity": severity,
        "severity_reason": severity_reason,
        "classification": primary_classification,
        "secondary_tags": secondary_tags,
        "confidence": confidence,
        "evidence": {
            "k8s_state": k8s_state,
            "es_logs": es_logs,
            "prom_metrics": prom_metrics
        },
        "analysis": analysis_result
    }

    # 5. Generate Reports
    json_path = os.path.join(output_dir, f"{incident_id}.json")
    md_path = os.path.join(output_dir, f"{incident_id}.md")

    generate_json_report(report_payload, json_path)
    generate_md_report(report_payload, md_path)

    logger.info(f"Analysis Complete! JSON report written to: {json_path}")
    logger.info(f"Analysis Complete! Markdown report written to: {md_path}")

    return report_payload, json_path, md_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexvion AI-Assisted Incident Analyzer")
    parser.add_argument("--incident-id", default="NEXVION-DEMO-001", help="Unique Incident Identifier")
    parser.add_argument("--namespace", default="nexvion", help="Target Kubernetes namespace")
    parser.add_argument("--query", default=None, help="Search query for Elasticsearch logs")
    parser.add_argument("--output-dir", default="reports", help="Output directory for reports")

    args = parser.parse_args()
    run_incident_analysis(args.incident_id, args.namespace, args.query, args.output_dir)
