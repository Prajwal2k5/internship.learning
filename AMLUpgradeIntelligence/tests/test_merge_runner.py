import json
from pathlib import Path

from aml_upgrade.merge.merge_runner import run_merge


def _sample_payload():
    return {
        "item_type": "Item",
        "item_id": "A",
        "attributes": {"id": "A", "type": "Item"},
        "fields": {"name": {"value": "Original"}},
        "relationships": {},
    }


def test_run_merge_writes_expected_artifacts_and_keeps_input_unchanged(tmp_path):
    report_path = tmp_path / "semantic_report.json"
    output_dir = tmp_path / "outputs" / "merge_run"

    record = {
        "customer_id": "Customer_1",
        "identity_key": "Item:A",
        "item_type": "Item",
        "item_id": "A",
        "classification": "vendor_only_change",
        "presence_classification": "present_in_all",
        "customer_changed_fields": [],
        "vendor_changed_fields": ["fields.name.value"],
        "conflicting_fields": [],
        "convergent_fields": [],
        "ambiguous_structure_paths": [],
        "standard_source_payload": _sample_payload(),
        "customer_source_payload": _sample_payload(),
        "standard_target_payload": {
            **_sample_payload(),
            "fields": {"name": {"value": "Vendor update"}},
        },
        "standard_source_occurrences": 1,
        "customer_source_occurrences": 1,
        "standard_target_occurrences": 1,
    }
    report = {
        "records": [record],
        "classification_summary": {"vendor_only_change": 1},
    }
    original_bytes = json.dumps(report, indent=2).encode("utf-8")
    report_path.write_bytes(original_bytes)

    result = run_merge(report_path, output_dir)

    expected_files = {
        "merged_candidates.json",
        "operation_journal.json",
        "review_queue.json",
        "conflicts.json",
        "merge_summary.json",
        "merge_result.json",
    }

    assert set(result["files_written"]) == expected_files
    assert {p.name for p in output_dir.iterdir()} == expected_files
    assert report_path.read_bytes() == original_bytes

    candidates = json.loads(
        (output_dir / "merged_candidates.json").read_text(encoding="utf-8")
    )
    assert candidates["items"][0]["payload"]["fields"]["name"]["value"] == "Vendor update"

    summary = json.loads(
        (output_dir / "merge_summary.json").read_text(encoding="utf-8")
    )
    assert summary["source_xml_modified"] is False
    assert summary["aml_xml_generated"] is False


def test_run_merge_rejects_missing_report(tmp_path):
    try:
        run_merge(tmp_path / "missing.json", tmp_path / "out")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_run_merge_rejects_output_directory_containing_report(tmp_path):
    report_path = tmp_path / "reports" / "semantic_report.json"
    report_path.parent.mkdir()
    report_path.write_text('{"records": []}', encoding="utf-8")

    try:
        run_merge(report_path, tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
