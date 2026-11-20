
from pathlib import Path

from aml_upgrade.scanner.snapshot_scanner import scan_snapshots

SNAPSHOTS = (
    "StandardSource",
    "CustomerSource",
    "StandardTarget",
)


def create_test_dataset(root: Path) -> Path:
    for snapshot in SNAPSHOTS:
        snapshot_dir = root / "Customer_1" / snapshot
        snapshot_dir.mkdir(parents=True)

        (snapshot_dir / "sample.xml").write_text(
            '<AML><Item type="Part" id="123" /></AML>',
            encoding="utf-8",
        )

    return root


def test_scanner_discovers_customer_and_snapshots(tmp_path):
    dataset = create_test_dataset(tmp_path)
    manifest = scan_snapshots(dataset)

    assert len(manifest.customers) == 1
    assert manifest.customers[0].customer_id == "Customer_1"
    assert len(manifest.customers[0].snapshots) == 3

    for snapshot in manifest.customers[0].snapshots:
        assert snapshot.directory_present is True
        assert len(snapshot.files) == 1
        assert snapshot.files[0].xml_valid is True


def test_scanner_calculates_sha256(tmp_path):
    dataset = create_test_dataset(tmp_path)
    manifest = scan_snapshots(dataset)

    file_record = manifest.customers[0].snapshots[0].files[0]

    assert len(file_record.sha256) == 64
    assert file_record.size_bytes > 0


def test_scanner_detects_malformed_xml(tmp_path):
    dataset = create_test_dataset(tmp_path)
    bad_file = dataset / "Customer_1" / "StandardSource" / "sample.xml"

    bad_file.write_text("<AML><Item>", encoding="utf-8")

    manifest = scan_snapshots(dataset)
    record = manifest.customers[0].snapshots[0].files[0]

    assert record.xml_valid is False
    assert record.validation_error is not None


def test_scanner_detects_missing_snapshot(tmp_path):
    dataset = create_test_dataset(tmp_path)
    missing_dir = dataset / "Customer_1" / "StandardTarget"

    for file in missing_dir.iterdir():
        file.unlink()

    missing_dir.rmdir()

    manifest = scan_snapshots(dataset)

    target_snapshot = next(
        snapshot
        for snapshot in manifest.customers[0].snapshots
        if snapshot.snapshot_name == "StandardTarget"
    )

    assert target_snapshot.directory_present is False
    assert target_snapshot.errors
