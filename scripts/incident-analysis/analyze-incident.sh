#!/usr/bin/env bash
# Nexvion AI-Assisted Incident Analysis Pipeline Wrapper Script

set -e

INCIDENT_ID="${1:-NEXVION-DEMO-001}"
NAMESPACE="${2:-nexvion}"
QUERY="${3:-}"

echo "======================================================================"
echo " Starting Incident Analysis Pipeline"
echo " Incident ID : ${INCIDENT_ID}"
echo " Namespace   : ${NAMESPACE}"
echo "======================================================================"

PYTHON_BIN="python"
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_BIN="python3"
    else
        echo "Error: Python runtime not found."
        exit 1
    fi
fi

if [ -n "${QUERY}" ]; then
    ${PYTHON_BIN} tools/incident-analysis/incident_analyzer.py --incident-id "${INCIDENT_ID}" --namespace "${NAMESPACE}" --query "${QUERY}"
else
    ${PYTHON_BIN} tools/incident-analysis/incident_analyzer.py --incident-id "${INCIDENT_ID}" --namespace "${NAMESPACE}"
fi

echo "======================================================================"
echo " Analysis Complete!"
echo " Reports generated in reports/${INCIDENT_ID}.json & reports/${INCIDENT_ID}.md"
echo "======================================================================"
