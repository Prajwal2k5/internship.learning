
import hashlib
import json
from pathlib import Path

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from aml_upgrade.models.manifest import (
    CustomerRecord,
    FileRecord,
    ScanManifest,
    SnapshotRecord,
)


SNAPSHOT_NAMES = (
    "StandardSource",
    "CustomerSource",
    "StandardTarget",
)


def calculate_sha256(file_path: Path) -> str:
    """Calculate a file's SHA-256 hash without loading it entirely."""
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_xml(file_path: Path) -> tuple[bool, str | None, str | None]:
    """
    Securely parse XML and verify that its root element is AML.
    Returns: (is_valid, root_element, error_message)
    """
    try:
        tree = SafeET.parse(
            str(file_path),
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )

        root = tree.getroot()
        root_name = root.tag.rsplit("}", 1)[-1]

        if root_name != "AML":
            return (
                False,
                root_name,
                f"Expected AML root element, found '{root_name}'",
            )

        return True, root_name, None

    except (
        DefusedXmlException,
        SafeET.ParseError,
        OSError,
        ValueError,
    ) as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def scan_file(
    file_path: Path,
    input_root: Path,
    customer_id: str,
    snapshot_name: str,
) -> FileRecord:
    """Create a provenance and validation record for one XML file."""
    xml_valid, root_element, validation_error = validate_xml(file_path)

    return FileRecord(
        customer_id=customer_id,
        snapshot_name=snapshot_name,
        relative_path=file_path.relative_to(input_root).as_posix(),
        file_name=file_path.name,
        size_bytes=file_path.stat().st_size,
        sha256=calculate_sha256(file_path),
        xml_valid=xml_valid,
        root_element=root_element,
        validation_error=validation_error,
    )


def scan_snapshots(input_root: str | Path) -> ScanManifest:
    """
    Discover customer snapshots and generate a read-only input manifest.
    Expected structure:
        input_root/
            Customer_1/
                StandardSource/
                CustomerSource/
                StandardTarget/
    """
    root = Path(input_root).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Input directory does not exist: {root}")

    manifest = ScanManifest(input_root=str(root))

    customer_dirs = sorted(
        (
            path for path in root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ),
        key=lambda path: path.name.lower(),
    )

    if not customer_dirs:
        manifest.errors.append("No customer directories were found.")
        return manifest

    for customer_dir in customer_dirs:
        customer = CustomerRecord(customer_id=customer_dir.name)

        for snapshot_name in SNAPSHOT_NAMES:
            snapshot_dir = customer_dir / snapshot_name

            if not snapshot_dir.is_dir():
                customer.errors.append(
                    f"Missing snapshot directory: {snapshot_name}"
                )

                customer.snapshots.append(
                    SnapshotRecord(
                        snapshot_name=snapshot_name,
                        directory_present=False,
                        errors=["Snapshot directory is missing."],
                    )
                )
                continue

            snapshot = SnapshotRecord(
                snapshot_name=snapshot_name,
                directory_present=True,
            )

            xml_files = sorted(
                (
                    path for path in snapshot_dir.rglob("*")
                    if path.is_file() and path.suffix.lower() == ".xml"
                ),
                key=lambda path: str(path).lower(),
            )

            if not xml_files:
                snapshot.errors.append("No XML files found in snapshot.")

            for file_path in xml_files:
                record = scan_file(
                    file_path=file_path,
                    input_root=root,
                    customer_id=customer_dir.name,
                    snapshot_name=snapshot_name,
                )

                snapshot.files.append(record)

                if not record.xml_valid:
                    snapshot.errors.append(
                        f"Invalid XML: {record.relative_path}"
                    )

            customer.snapshots.append(snapshot)

        manifest.customers.append(customer)

    return manifest


def write_manifest(
    manifest: ScanManifest,
    output_path: str | Path,
) -> Path:
    """Write the scan manifest as formatted JSON."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        json.dumps(
            manifest.model_dump(mode="json"),
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return destination
