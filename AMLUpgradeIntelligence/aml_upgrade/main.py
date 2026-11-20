
import argparse
from pathlib import Path

from aml_upgrade.scanner.snapshot_scanner import (
    scan_snapshots,
    write_manifest,
)


def main():
    parser = argparse.ArgumentParser(
        description="Scan AML customer snapshots and generate a manifest."
    )

    parser.add_argument(
        "--input-root",
        required=True,
        help="Path containing Customer_1, Customer_2, etc.",
    )

    parser.add_argument(
        "--output",
        default="reports/input_manifest.json",
        help="Output JSON manifest path.",
    )

    args = parser.parse_args()

    input_root = Path(args.input_root).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    # Prevent writing generated files into the original AML input directory.
    if output_path == input_root or input_root in output_path.parents:
        parser.exit(
            1,
            "Scan failed: Output manifest must be outside the input directory.\n",
        )

    try:
        manifest = scan_snapshots(input_root)
        output_path = write_manifest(manifest, output_path)

    except (ValueError, OSError) as exc:
        parser.exit(1, f"Scan failed: {exc}\n")

    total_files = 0
    valid_files = 0
    invalid_files = 0

    for customer in manifest.customers:
        for snapshot in customer.snapshots:
            total_files += len(snapshot.files)
            valid_files += sum(file.xml_valid for file in snapshot.files)
            invalid_files += sum(not file.xml_valid for file in snapshot.files)

    print("\nAML Snapshot Scan Completed")
    print("---------------------------")
    print(f"Run ID               : {manifest.run_id}")
    print(f"Customers discovered : {len(manifest.customers)}")
    print(f"XML files discovered : {total_files}")
    print(f"Valid XML files      : {valid_files}")
    print(f"Invalid XML files    : {invalid_files}")
    print(f"Manifest saved to    : {output_path}")

    if manifest.errors:
        print("\nScan warnings:")
        for error in manifest.errors:
            print(f"- {error}")

    for customer in manifest.customers:
        for error in customer.errors:
            print(f"- {customer.customer_id}: {error}")

        for snapshot in customer.snapshots:
            for error in snapshot.errors:
                print(f"- {customer.customer_id}/{snapshot.snapshot_name}: {error}")


if __name__ == "__main__":
    main()
