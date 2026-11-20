
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from aml_upgrade.models.aml_item import AMLField, NormalizedAMLItem
from aml_upgrade.models.identity import (
    AMLIdentityRecord,
    DuplicateIdentityGroup,
    IdentityInventory,
)
from aml_upgrade.parsers.aml_parser import parse_aml_file


SNAPSHOT_NAMES = (
    "StandardSource",
    "CustomerSource",
    "StandardTarget",
)


def make_identity_key(
    item_type: str | None,
    item_id: str | None,
) -> str | None:
    """
    Create a stable identity key using AML item type and ID.

    Example:
        Part + part-001 -> Part:part-001

    Returns None when type or ID is missing.
    """

    if not item_type or not item_id:
        return None

    return f"{item_type}:{item_id}"


def iter_field_items(
    field: AMLField,
) -> Iterator[NormalizedAMLItem]:
    """
    Find AML Items nested inside a field and its child fields.
    """

    for item in field.items:
        yield from iter_item_tree(item)

    for child in field.children:
        yield from iter_field_items(child)


def iter_item_tree(
    item: NormalizedAMLItem,
) -> Iterator[NormalizedAMLItem]:
    """
    Visit an AML item and all its nested items.

    This includes relationship items and items nested inside fields.
    """

    yield item

    for relationship in item.relationships:
        yield from iter_item_tree(relationship)

    for field in item.fields:
        yield from iter_field_items(field)


def extract_item_records(
    item: NormalizedAMLItem,
    customer_id: str,
    snapshot_name: str,
    source_file: str,
    nesting_path: str,
    parent_identity_key: str | None = None,
    is_top_level: bool = False,
) -> list[AMLIdentityRecord]:
    """
    Extract identity information recursively from an AML item.

    Query items such as action='get' are preserved and classified
    separately from ordinary AML item definitions.
    """

    identity_key = make_identity_key(
        item.item_type,
        item.item_id,
    )

    is_query = (
        (item.action or "").strip().lower() == "get"
    )

    record = AMLIdentityRecord(
        customer_id=customer_id,
        snapshot_name=snapshot_name,
        source_file=source_file,
        item_type=item.item_type,
        item_id=item.item_id,
        action=item.action,
        identity_key=identity_key,
        parent_identity_key=parent_identity_key,
        nesting_path=nesting_path,
        is_top_level=is_top_level,
        is_query=is_query,
    )

    records = [record]

    # Extract nested relationship items.
    for index, relationship in enumerate(item.relationships):
        records.extend(
            extract_item_records(
                item=relationship,
                customer_id=customer_id,
                snapshot_name=snapshot_name,
                source_file=source_file,
                nesting_path=(
                    f"{nesting_path}/Relationships/Item[{index}]"
                ),
                parent_identity_key=identity_key,
            )
        )

    # Extract items nested inside normal fields.
    for field_index, field in enumerate(item.fields):
        records.extend(
            extract_field_records(
                field=field,
                customer_id=customer_id,
                snapshot_name=snapshot_name,
                source_file=source_file,
                nesting_path=(
                    f"{nesting_path}/Field[{field_index}]/{field.name}"
                ),
                parent_identity_key=identity_key,
            )
        )

    return records


def extract_field_records(
    field: AMLField,
    customer_id: str,
    snapshot_name: str,
    source_file: str,
    nesting_path: str,
    parent_identity_key: str | None,
) -> list[AMLIdentityRecord]:
    """
    Find and extract AML items nested inside fields.
    """

    records = []

    for index, nested_item in enumerate(field.items):
        records.extend(
            extract_item_records(
                item=nested_item,
                customer_id=customer_id,
                snapshot_name=snapshot_name,
                source_file=source_file,
                nesting_path=f"{nesting_path}/Item[{index}]",
                parent_identity_key=parent_identity_key,
            )
        )

    for index, child in enumerate(field.children):
        records.extend(
            extract_field_records(
                field=child,
                customer_id=customer_id,
                snapshot_name=snapshot_name,
                source_file=source_file,
                nesting_path=(
                    f"{nesting_path}/Child[{index}]/{child.name}"
                ),
                parent_identity_key=parent_identity_key,
            )
        )

    return records


def build_identity_inventory(
    input_root: str | Path,
) -> IdentityInventory:
    """
    Build an identity inventory for all customer snapshots.

    The inventory:
    - Extracts top-level and nested AML items.
    - Classifies action='get' items as query records.
    - Tracks non-query records missing identity.
    - Detects repeated identities without assuming they are invalid.
    """

    root = Path(input_root).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError(
            f"Input directory does not exist: {root}"
        )

    inventory = IdentityInventory()

    # Discover customer directories.
    customer_dirs = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ),
        key=lambda path: path.name.lower(),
    )

    for customer_dir in customer_dirs:
        customer_id = customer_dir.name

        # Discover the three required snapshots.
        for snapshot_name in SNAPSHOT_NAMES:
            snapshot_dir = customer_dir / snapshot_name

            if not snapshot_dir.is_dir():
                continue

            xml_files = sorted(
                (
                    path
                    for path in snapshot_dir.rglob("*")
                    if path.is_file()
                    and path.suffix.lower() == ".xml"
                ),
                key=lambda path: str(path).lower(),
            )

            for xml_file in xml_files:
                # Parse the AML file.
                document = parse_aml_file(xml_file)

                relative_path = (
                    xml_file.relative_to(root).as_posix()
                )

                # Extract each top-level AML Item.
                for index, item in enumerate(document.items):
                    records = extract_item_records(
                        item=item,
                        customer_id=customer_id,
                        snapshot_name=snapshot_name,
                        source_file=relative_path,
                        nesting_path=f"Item[{index}]",
                        is_top_level=True,
                    )

                    inventory.records.extend(records)

    # ---------------------------------------------------------
    # Classify records and group repeated identities.
    # ---------------------------------------------------------

    grouped = defaultdict(list)

    for record in inventory.records:

        # action='get' represents an AML retrieval/query operation.
        # Preserve it separately from item definitions.
        if record.is_query:
            inventory.query_records.append(record)
            continue

        # Non-query records without type or ID need investigation.
        if record.identity_key is None:
            inventory.missing_identity_records.append(record)
            continue

        group_key = (
            record.customer_id,
            record.snapshot_name,
            record.identity_key,
        )

        grouped[group_key].append(record)

    # Record repeated identities.
    # Do not delete or automatically reject repeated occurrences.
    for (
        customer_id,
        snapshot_name,
        identity_key,
    ), occurrences in grouped.items():

        if len(occurrences) > 1:
            inventory.duplicate_groups.append(
                DuplicateIdentityGroup(
                    customer_id=customer_id,
                    snapshot_name=snapshot_name,
                    identity_key=identity_key,
                    occurrences=occurrences,
                )
            )

    return inventory
