from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_python_script(script_name: str, args: list[str]) -> dict[str, object]:
    command = [sys.executable, str(PROJECT_ROOT / "ner_kb" / script_name), *args]
    result = subprocess.run(command, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    print(f"--- {script_name} ---")
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    return {
        "script": script_name,
        "returncode": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full Buoi 12 workflow: predict -> evaluate -> reload graph.")
    parser.add_argument("--data-dir", default="ner_kb", help="Directory containing metadata.csv and content.csv.")
    parser.add_argument("--max-pairs", type=int, default=20, help="Maximum pairs to send to Gemini.")
    parser.add_argument("--predictions-output", default="ner_kb/predicted_relationships.csv", help="CSV file for LLM predictions.")
    parser.add_argument("--evaluation-output", default="ner_kb/evaluation_report.json", help="JSON file storing evaluation metrics.")
    parser.add_argument("--reload-output", default="ner_kb/merged_relationships.csv", help="Merged graph-ready relationship CSV.")
    parser.add_argument("--api-key", default="", help="Optional Gemini API key; otherwise use GEMINI_API_KEY env var.")
    parser.add_argument("--dry-run", action="store_true", help="Only show the pipeline steps without contacting Gemini or Neo4j.")
    parser.add_argument("--skip-reload", action="store_true", help="Skip Neo4j re-import step.")
    args = parser.parse_args()

    api_key = (args.api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not args.dry_run and not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY. Pass --api-key or set the environment variable.")

    data_dir = str(args.data_dir)
    predictions_out = str(args.predictions_output)
    reload_out = str(args.reload_output)

    print("Starting full Buoi 12 pipeline: predict -> evaluate -> reload")

    if args.dry_run:
        print("Dry-run mode enabled. No actual Gemini/Neo4j calls will be made.")
        print("Step 1: predict_relationships.py --data-dir ... --max-pairs ... --output ... --dry-run")
        print("Step 2: evaluate_predictions.py --ground-truth ... --predictions ...")
        print("Step 3: reload_predicted_graph.py --data-dir ... --predictions ... --output ... --dry-run")
        return

    predict_result = run_python_script(
        "predict_relationships.py",
        [
            "--data-dir",
            data_dir,
            "--max-pairs",
            str(args.max_pairs),
            "--output",
            predictions_out,
            "--api-key",
            api_key,
        ],
    )
    if predict_result["returncode"] != 0:
        raise RuntimeError(f"Predict step failed: {predict_result['stderr'] or predict_result['stdout']}")

    evaluate_result = run_python_script(
        "evaluate_predictions.py",
        [
            "--ground-truth",
            str(Path(data_dir) / "relationships.csv"),
            "--predictions",
            predictions_out,
        ],
    )
    if evaluate_result["returncode"] != 0:
        raise RuntimeError(f"Evaluate step failed: {evaluate_result['stderr'] or evaluate_result['stdout']}")

    metrics = json.loads(evaluate_result["stdout"] or "{}")
    with Path(args.evaluation_output).open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)
    print(f"Saved evaluation metrics to {args.evaluation_output}")

    if args.skip_reload:
        print("Reload skipped by flag --skip-reload.")
        return

    reload_result = run_python_script(
        "reload_predicted_graph.py",
        [
            "--data-dir",
            data_dir,
            "--predictions",
            predictions_out,
            "--output",
            reload_out,
        ],
    )
    if reload_result["returncode"] != 0:
        raise RuntimeError(f"Reload step failed: {reload_result['stderr'] or reload_result['stdout']}")

    print("Full Buoi 12 pipeline completed successfully.")


if __name__ == "__main__":
    main()
