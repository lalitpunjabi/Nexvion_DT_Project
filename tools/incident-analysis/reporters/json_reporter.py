import json
import os

def generate_json_report(report_payload, output_path):
    """
    Writes machine-readable JSON incident analysis report.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)
    return output_path
