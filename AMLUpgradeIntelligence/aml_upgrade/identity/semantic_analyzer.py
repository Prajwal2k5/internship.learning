from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator

from aml_upgrade.identity.identity_extractor import (
    SNAPSHOT_NAMES,
    build_identity_inventory,
)
from aml_upgrade.models.aml_item import (
    AMLField,
    AMLReference,
    NormalizedAMLItem,
)
from aml_upgrade.models.semantic import (
    SemanticChangeRecord,
    SemanticComparisonReport,
)
from aml_upgrade.parsers.aml_parser import parse_aml_file


MISSING = object()


# ---------------------------------------------------------
# 1. Traverse nested AML items
# ---------------------------------------------------------

def iter_field_items_with_paths(
    field: AMLField,
    base_path: str,
) -> Iterator[tuple[NormalizedAMLItem, str]]:
    """Visit AML items nested inside a field."""

    for index, item in enumerate(field.items):
        item_path = f"{base_path}/Item[{index}]"
        yield from iter_item_with_paths(item, item_path)

    for index, child in enumerate(field.children):
        child_path = f"{base_path}/Child[{index}]/{child.name}"
        yield from iter_field_items_with_paths(child, child_path)


def iter_item_with_paths(
    item: NormalizedAMLItem,
    path: str,
) -> Iterator[tuple[NormalizedAMLItem, str]]:
    """Visit an item and all its nested AML items."""

    yield item, path

    for index, relationship in enumerate(item.relationships):
        relationship_path = f"{path}/Relationships/Item[{index}]"
        yield from iter_item_with_paths(
            relationship,
            relationship_path,
        )

    for index, field in enumerate(item.fields):
        field_path = f"{path}/Field[{index}]/{field.name}"
        yield from iter_field_items_with_paths(
            field,
            field_path,
        )


# ---------------------------------------------------------
# 2. Canonicalize AML references
# ---------------------------------------------------------

def canonicalize_reference(
    reference: AMLReference | None,
) -> dict | None:
    """Convert an AML reference into a stable dictionary."""

    if reference is None:
        return None

    result = {"element_name": reference.element_name}

    optional_values = {
        "target_id": reference.target_id,
        "target_type": reference.target_type,
        "keyed_name": reference.keyed_name,
    }

    for key, value in optional_values.items():
        if value is not None:
            result[key] = value

    if reference.attributes:
        result["attributes"] = dict(
            sorted(reference.attributes.items())
        )

    return result


# ---------------------------------------------------------
# 3. Structure-aware field normalization
# ---------------------------------------------------------

def _canonicalize_field_collection(
    fields: list[AMLField],
    base_path: str,
    ambiguities: list[str],
) -> dict:
    """
    Normalize fields by field name instead of list position.

    Repeated field names are flagged because automatically
    distinguishing them could produce an unsafe comparison.
    """

    result = {}

    for field in fields:
        field_path = f"{base_path}.{field.name}"

        if field.name in result:
            ambiguities.append(
                f"{field_path}: repeated field name"
            )
            continue

        result[field.name] = canonicalize_field(
            field,
            ambiguities=ambiguities,
            path=field_path,
        )

    return dict(sorted(result.items()))


def _canonicalize_item_collection(
    items: list[NormalizedAMLItem],
    base_path: str,
    ambiguities: list[str],
) -> dict:
    """
    Normalize nested AML items by stable identity.

    Query operations with action='get' are excluded.
    Items without a stable identity and repeated identities
    are flagged for manual review.
    """

    result = {}

    for item in items:
        if (item.action or "").strip().lower() == "get":
            continue

        if not item.item_type or not item.item_id:
            ambiguities.append(
                f"{base_path}: nested item has no stable identity"
            )
            continue

        identity_key = f"{item.item_type}:{item.item_id}"
        item_path = f"{base_path}.{identity_key}"

        if identity_key in result:
            ambiguities.append(
                f"{item_path}: repeated nested item identity"
            )
            continue

        result[identity_key] = canonicalize_item(
            item,
            ambiguities=ambiguities,
            path=item_path,
        )

    return dict(sorted(result.items()))


def canonicalize_field(
    field: AMLField,
    ambiguities: list[str] | None = None,
    path: str = "$",
) -> dict:
    """
    Convert an AML field into a structure-aware representation.

    Missing/empty structural values are omitted. Explicit empty
    strings are retained because they may be meaningful AML values.
    """

    if ambiguities is None:
        ambiguities = []

    result = {}

    if field.value is not None:
        result["value"] = field.value

    if field.attributes:
        result["attributes"] = dict(
            sorted(field.attributes.items())
        )

    reference = canonicalize_reference(field.reference)
    if reference is not None:
        result["reference"] = reference

    children = _canonicalize_field_collection(
        field.children,
        f"{path}.children",
        ambiguities,
    )
    if children:
        result["children"] = children

    items = _canonicalize_item_collection(
        field.items,
        f"{path}.items",
        ambiguities,
    )
    if items:
        result["items"] = items

    return result


# ---------------------------------------------------------
# 4. Structure-aware AML item normalization
# ---------------------------------------------------------

def canonicalize_item(
    item: NormalizedAMLItem,
    ambiguities: list[str] | None = None,
    path: str = "$",
) -> dict:
    """
    Convert an AML item into a deterministic representation.

    Fields are keyed by field name.
    Relationships are keyed by item type and item ID.
    The action attribute is excluded because it describes
    an AML operation rather than the item's business content.
    """

    if ambiguities is None:
        ambiguities = []

    attributes = {
        key: value
        for key, value in item.attributes.items()
        if key.lower() != "action"
    }

    result = {
        "item_type": item.item_type,
        "item_id": item.item_id,
    }

    if attributes:
        result["attributes"] = dict(sorted(attributes.items()))

    fields = _canonicalize_field_collection(
        item.fields,
        f"{path}.fields",
        ambiguities,
    )
    if fields:
        result["fields"] = fields

    relationships = _canonicalize_item_collection(
        item.relationships,
        f"{path}.relationships",
        ambiguities,
    )
    if relationships:
        result["relationships"] = relationships

    return result


# ---------------------------------------------------------
# 5. Flatten normalized structures for comparison
# ---------------------------------------------------------

def flatten_payload(
    value: Any,
    path: str = "",
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Flatten dictionaries into stable semantic paths.

    Empty dictionaries are ignored because they do not represent
    meaningful AML content. Lists remain atomic values and are
    never compared using numeric indexes.
    """

    if result is None:
        result = {}

    if isinstance(value, dict):
        if not value:
            return result

        for key, child in sorted(value.items()):
            child_path = (
                f"{path}.{key}" if path else str(key)
            )
            flatten_payload(
                child,
                child_path,
                result,
            )

    elif isinstance(value, list):
        result[path or "$"] = value

    else:
        result[path or "$"] = value

    return result


# ---------------------------------------------------------
# 6. Detect changed semantic paths
# ---------------------------------------------------------

def _nested_item_roots(path: str) -> list[str]:
    """Return nested AML item identity roots found in a semantic path.

    Handles both root-level paths such as
    ``relationships.Type:id.fields.name.value`` and deeper paths such as
    ``relationships.Parent:id.relationships.Child:id.fields.name.value``.
    """

    segments = path.split(".")
    roots = []

    for index in range(len(segments) - 1):
        if segments[index] in {"relationships", "items"}:
            identity = segments[index + 1]
            if identity:
                roots.append(".".join(segments[: index + 2]))

    return roots


def changed_paths(
    baseline: dict[str, Any],
    updated: dict[str, Any],
) -> list[str]:
    """Return semantic paths whose values differ.

    If an entire nested AML item is added or removed, report its identity
    path once instead of reporting every property. Changes inside an
    existing nested item remain field-level.
    """

    paths = set(baseline) | set(updated)

    changed = {
        path
        for path in paths
        if baseline.get(path, MISSING) != updated.get(path, MISSING)
    }

    collapsed_roots = set()

    for path in changed:
        for item_root in _nested_item_roots(path):
            baseline_has_item = any(
                key == item_root or key.startswith(item_root + ".")
                for key in baseline
            )
            updated_has_item = any(
                key == item_root or key.startswith(item_root + ".")
                for key in updated
            )

            if (
                not baseline_has_item and updated_has_item
            ) or (
                baseline_has_item and not updated_has_item
            ):
                collapsed_roots.add(item_root)

    # A wholly added/removed parent item subsumes its nested items.
    minimal_roots = {
        root
        for root in collapsed_roots
        if not any(
            other != root and root.startswith(other + ".")
            for other in collapsed_roots
        )
    }

    for item_root in minimal_roots:
        changed = {
            path
            for path in changed
            if not (
                path == item_root
                or path.startswith(item_root + ".")
            )
        }

    changed.update(minimal_roots)
    return sorted(changed)


# ---------------------------------------------------------
# 7. Three-way comparison
# ---------------------------------------------------------

def compare_payloads(
    standard_source: dict,
    customer_source: dict,
    standard_target: dict,
) -> tuple[str, list[str], list[str], list[str], list[str]]:
    """
    Compare customer and vendor changes against Standard Source.

    A conflict occurs when both sides change the same semantic
    path to different values.
    """

    ss = flatten_payload(standard_source)
    cs = flatten_payload(customer_source)
    st = flatten_payload(standard_target)

    customer_changes = changed_paths(ss, cs)
    vendor_changes = changed_paths(ss, st)

    overlapping_paths = (
        set(customer_changes) & set(vendor_changes)
    )

    conflicting_fields = sorted(
        path
        for path in overlapping_paths
        if cs.get(path, MISSING) != st.get(path, MISSING)
    )

    convergent_fields = sorted(
        path
        for path in overlapping_paths
        if cs.get(path, MISSING) == st.get(path, MISSING)
    )

    if not customer_changes and not vendor_changes:
        classification = "unchanged"

    elif customer_changes and not vendor_changes:
        classification = "customer_only_change"

    elif vendor_changes and not customer_changes:
        classification = "vendor_only_change"

    elif conflicting_fields:
        classification = "conflict"

    else:
        classification = (
            "customer_and_vendor_changes_no_conflict"
        )

    return (
        classification,
        customer_changes,
        vendor_changes,
        conflicting_fields,
        convergent_fields,
    )


# ---------------------------------------------------------
# 8. Collect items from all three snapshots
# ---------------------------------------------------------

def collect_snapshot_items(
    input_root: str | Path,
) -> dict:
    """
    Parse all snapshots and collect AML item occurrences.

    Grouping key:
        customer_id + identity_key + snapshot_name

    All occurrences are preserved.
    """

    root = Path(input_root).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError(
            f"Input directory does not exist: {root}"
        )

    grouped = defaultdict(
        lambda: {
            snapshot_name: []
            for snapshot_name in SNAPSHOT_NAMES
        }
    )

    customer_dirs = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
        ),
        key=lambda path: path.name.lower(),
    )

    for customer_dir in customer_dirs:
        customer_id = customer_dir.name

        for snapshot_name in SNAPSHOT_NAMES:
            snapshot_dir = customer_dir / snapshot_name

            if not snapshot_dir.is_dir():
                continue

            xml_files = sorted(
                (
                    path
                    for path in snapshot_dir.rglob("*.xml")
                    if path.is_file()
                ),
                key=lambda path: str(path).lower(),
            )

            for xml_file in xml_files:
                document = parse_aml_file(xml_file)

                for index, top_item in enumerate(document.items):
                    top_path = f"Item[{index}]"

                    for item, nesting_path in iter_item_with_paths(
                        top_item,
                        top_path,
                    ):
                        if (
                            (item.action or "").strip().lower()
                            == "get"
                        ):
                            continue

                        if not item.item_type or not item.item_id:
                            continue

                        identity_key = (
                            f"{item.item_type}:{item.item_id}"
                        )

                        group_key = (
                            customer_id,
                            identity_key,
                        )

                        grouped[group_key][snapshot_name].append(
                            {
                                "item": item,
                                "source_file": (
                                    xml_file.relative_to(root).as_posix()
                                ),
                                "nesting_path": nesting_path,
                            }
                        )

    return grouped


# ---------------------------------------------------------
# 9. Run semantic comparison for all customers
# ---------------------------------------------------------

def analyze_semantic_changes(
    input_root: str | Path,
) -> SemanticComparisonReport:
    """
    Compare uniquely occurring identities across SS, CS and ST.

    Repeated identities, non-common identities, and ambiguous
    structures are retained for review rather than automatically
    compared.
    """

    inventory = build_identity_inventory(input_root)
    grouped = collect_snapshot_items(input_root)

    report = SemanticComparisonReport(
        query_records_excluded=len(inventory.query_records),
        missing_identity_records_excluded=len(
            inventory.missing_identity_records
        ),
    )

    for (customer_id, identity_key), snapshots in sorted(
        grouped.items()
    ):
        ss_records = snapshots["StandardSource"]
        cs_records = snapshots["CustomerSource"]
        st_records = snapshots["StandardTarget"]

        ss_count = len(ss_records)
        cs_count = len(cs_records)
        st_count = len(st_records)

        # Multiple occurrences make automatic comparison unsafe.
        if max(ss_count, cs_count, st_count) > 1:
            first = (
                ss_records
                or cs_records
                or st_records
            )[0]["item"]

            report.records.append(
                SemanticChangeRecord(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    item_type=first.item_type,
                    item_id=first.item_id,
                    classification="ambiguous_repeated_identity",
                    standard_source_occurrences=ss_count,
                    customer_source_occurrences=cs_count,
                    standard_target_occurrences=st_count,
                )
            )

            report.skipped_repeated_identities += 1
            continue

        # Compare content only when the identity exists exactly
        # once in all three snapshots.
        if not (
            ss_count == 1
            and cs_count == 1
            and st_count == 1
        ):
            from aml_upgrade.identity.snapshot_matcher import (
                classify_presence,
            )

            presence = classify_presence(
                in_ss=ss_count == 1,
                in_cs=cs_count == 1,
                in_st=st_count == 1,
            )

            first = (
                ss_records
                or cs_records
                or st_records
            )[0]["item"]

            report.records.append(
                SemanticChangeRecord(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    item_type=first.item_type,
                    item_id=first.item_id,
                    classification="presence_requires_review",
                    presence_classification=presence,
                    standard_source_occurrences=ss_count,
                    customer_source_occurrences=cs_count,
                    standard_target_occurrences=st_count,
                )
            )

            report.skipped_non_common_identities += 1
            continue

        ss_item = ss_records[0]["item"]
        cs_item = cs_records[0]["item"]
        st_item = st_records[0]["item"]

        # Normalize each snapshot independently so ambiguity in
        # any one snapshot prevents an unsafe automatic comparison.
        ss_ambiguities: list[str] = []
        cs_ambiguities: list[str] = []
        st_ambiguities: list[str] = []

        ss_payload = canonicalize_item(
            ss_item,
            ambiguities=ss_ambiguities,
        )
        cs_payload = canonicalize_item(
            cs_item,
            ambiguities=cs_ambiguities,
        )
        st_payload = canonicalize_item(
            st_item,
            ambiguities=st_ambiguities,
        )

        all_ambiguities = sorted(
            set(
                [f"StandardSource: {path}" for path in ss_ambiguities]
                + [f"CustomerSource: {path}" for path in cs_ambiguities]
                + [f"StandardTarget: {path}" for path in st_ambiguities]
            )
        )

        if all_ambiguities:
            report.records.append(
                SemanticChangeRecord(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    item_type=ss_item.item_type,
                    item_id=ss_item.item_id,
                    classification="ambiguous_structure_requires_review",
                    ambiguous_structure_paths=all_ambiguities,
                    standard_source_payload=ss_payload,
                    customer_source_payload=cs_payload,
                    standard_target_payload=st_payload,
                    standard_source_occurrences=ss_count,
                    customer_source_occurrences=cs_count,
                    standard_target_occurrences=st_count,
                )
            )

            report.skipped_ambiguous_structures += 1
            continue

        (
            classification,
            customer_changes,
            vendor_changes,
            conflicting_fields,
            convergent_fields,
        ) = compare_payloads(
            ss_payload,
            cs_payload,
            st_payload,
        )

        report.records.append(
            SemanticChangeRecord(
                customer_id=customer_id,
                identity_key=identity_key,
                item_type=ss_item.item_type,
                item_id=ss_item.item_id,
                classification=classification,
                customer_changed_fields=customer_changes,
                vendor_changed_fields=vendor_changes,
                conflicting_fields=conflicting_fields,
                convergent_fields=convergent_fields,
                standard_source_payload=ss_payload,
                customer_source_payload=cs_payload,
                standard_target_payload=st_payload,
                standard_source_occurrences=ss_count,
                customer_source_occurrences=cs_count,
                standard_target_occurrences=st_count,
            )
        )

    # Build classification totals.
    summary = defaultdict(int)

    for record in report.records:
        summary[record.classification] += 1

    report.total_identities = len(report.records)

    report.compared_identities = sum(
        record.classification not in {
            "ambiguous_repeated_identity",
            "presence_requires_review",
            "ambiguous_structure_requires_review",
        }
        for record in report.records
    )

    report.classification_summary = dict(sorted(summary.items()))

    return report
