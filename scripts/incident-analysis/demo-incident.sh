#!/usr/bin/env bash
# Nexvion Controlled Demonstration Incident Trigger & Analysis Script

set -e

INCIDENT_ID="NEXVION-DEMO-001"
NAMESPACE="nexvion"
MARKER="NEXVION_AI_INCIDENT_DEMO_20261004"

echo "======================================================================"
echo " Phase 4.9 — Controlled Demonstration Incident Execution"
echo "======================================================================"

echo "[1/4] Injecting controlled demonstration incident log markers into nexvion workload stdout..."
kubectl exec -n ${NAMESPACE} deploy/nexvion-web -c nexvion-web -- sh -c \
  "echo '[ERROR] ${MARKER}: Connection failure to database host db-replica-01.nexvion.internal:5432 HTTP 500 Internal Server Error in payment checkout handler' > /proc/1/fd/1"

kubectl exec -n ${NAMESPACE} deploy/nexvion-web -c nexvion-web -- sh -c \
  "echo '[WARNING] ${MARKER}: High memory threshold advisory 82% allocation on container nexvion-web' > /proc/1/fd/1"

echo "[2/4] Waiting 10s for Fluent Bit & Elasticsearch log ingestion..."
sleep 10

echo "[3/4] Verifying Elasticsearch log marker ingestion..."
kubectl exec -n logging deploy/elk -c elasticsearch -- \
  curl -s "http://localhost:9200/nexvion-logs-*/_search?q=${MARKER}&pretty"

echo "[4/4] Running Incident Analysis Engine..."
python tools/incident-analysis/incident_analyzer.py --incident-id "${INCIDENT_ID}" --namespace "${NAMESPACE}" --query "${MARKER}" --output-dir reports

echo "======================================================================"
echo " Demonstration Complete! Structured reports generated:"
echo " - reports/${INCIDENT_ID}.json"
echo " - reports/${INCIDENT_ID}.md"
echo "======================================================================"

