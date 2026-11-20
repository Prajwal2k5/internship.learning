from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from aml_upgrade.merge.merge_engine import merge_semantic_report


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def run_merge(
    semantic_report_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """
    Run the deterministic merge and write reviewable JSON artifacts.

    This stage writes normalized candidates and audit records only.
    It does not create or modify AML XML source files.
    """
    report_path = Path(semantic_report_path).resolve()
    destination = Path(output_dir).resolve()

    if not report_path.is_file():
        raise FileNotFoundError(f"Semantic report not found: {report_path}")

    # Prevent accidental replacement of the semantic report itself.
    if destination == report_path.parent or report_path.is_relative_to(destination):
        raise ValueError(
            "Output directory must not contain or replace the semantic report."
        )

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    merge_result = merge_semantic_report(report_data)
    result_data = merge_result.model_dump(mode="json")

    journal = [
        {
            "sequence": index,
            "customer_id": operation.customer_id,
            "identity_key": operation.identity_key,
            "operation": operation.operation,
            "path": operation.path,
            "reason": operation.reason,
        }
        for index, operation in enumerate(merge_result.operations, start=1)
    ]

    review_queue = [
        item.model_dump(mode="json")
        for item in merge_result.review_queue
    ]
    conflicts = [
        item.model_dump(mode="json")
        for item in merge_result.conflicts
    ]

    artifacts = {
        "merged_candidates.json": {
            "description": "Normalized Customer Target candidate items; not AML XML.",
            "items": [item.model_dump(mode="json") for item in merge_result.items],
        },
        "operation_journal.json": {
            "description": "Ordered record of deterministic merge decisions.",
            "operations": journal,
        },
        "review_queue.json": {
            "description": "Items withheld from automatic merge and requiring review.",
            "items": review_queue,
        },
        "conflicts.json": {
            "description": "Detected merge conflicts requiring resolution.",
            "items": conflicts,
        },
        "merge_summary.json": {
            "input_report": str(report_path),
            "input_report_sha256": _sha256(report_path),
            "summary": merge_result.summary,
            "classification_summary": report_data.get("classification_summary", {}),
            "source_xml_modified": False,
            "aml_xml_generated": False,
        },
        "merge_result.json": result_data,
    }

    destination.mkdir(parents=True, exist_ok=True)
    for filename, payload in artifacts.items():
        _write_json(destination / filename, payload)

    return {
        "output_dir": str(destination),
        "files_written": sorted(artifacts),
        "summary": merge_result.summary,
        "review_items": len(review_queue),
        "conflicts": len(conflicts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run deterministic AML merge and write JSON audit artifacts."
    )
    parser.add_argument(
        "--report",
        default="reports/semantic_comparison_report.json",
        help="Path to semantic_comparison_report.json",
    )
    parser.add_argument(
        "--output",
        default="outputs/merge_run",
        help="Directory for generated merge JSON artifacts",
    )
    args = parser.parse_args()

    result = run_merge(args.report, args.output)
    print("MERGE RUN COMPLETED")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
