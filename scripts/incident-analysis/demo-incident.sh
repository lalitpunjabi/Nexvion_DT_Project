#!/usr/bin/env bash
# Nexvion Controlled Demonstration Incident Trigger & Analysis Script

set -e

INCIDENT_ID="NEXVION-DEMO-001"
NAMESPACE="nexvion"
POD_NAME="nexvion-demo-incident-pod"

echo "======================================================================"
echo " Phase 4.9 — Controlled Demonstration Incident Execution"
echo "======================================================================"

echo "[1/4] Triggering controlled demonstration incident log markers..."
kubectl run ${POD_NAME} --image=alpine -n ${NAMESPACE} --restart=Never -- sh -c '
echo "[CRITICAL] NEXVION_AI_INCIDENT_DEMO_20261004: Connection failure to database host db-replica-01.nexvion.internal:5432"
echo "[ERROR] NEXVION_AI_INCIDENT_DEMO_20261004: HTTP 500 Internal Server Error in payment checkout handler"
echo "[WARNING] NEXVION_AI_INCIDENT_DEMO_20261004: Memory usage threshold exceeded 85% limit on container"
sleep 5
'

echo "[2/4] Waiting 10s for Fluent Bit & Elasticsearch log ingestion..."
sleep 10

echo "[3/4] Running Incident Analysis Engine..."
python tools/incident-analysis/incident_analyzer.py --incident-id "${INCIDENT_ID}" --namespace "${NAMESPACE}" --query "NEXVION_AI_INCIDENT_DEMO_20261004"

echo "[4/4] Cleaning up demonstration pod..."
kubectl delete pod ${POD_NAME} -n ${NAMESPACE} --ignore-not-found

echo "======================================================================"
echo " Demonstration Complete! Check reports/${INCIDENT_ID}.md"
echo "======================================================================"
