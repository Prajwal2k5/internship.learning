from __future__ import annotations

from copy import deepcopy
from typing import Any

from aml_upgrade.models.merge import (
    MergeConflict,
    MergeOperation,
    MergeResult,
    MergeReviewItem,
    MergedItem,
)
from aml_upgrade.merge.merge_policy import identity_from_payload


_MISSING = object()


def _as_dict(report: Any) -> dict[str, Any]:
    if hasattr(report, "model_dump"):
        return report.model_dump(mode="python")
    if isinstance(report, dict):
        return deepcopy(report)
    raise TypeError("report must be a SemanticComparisonReport or dictionary")


def _review_registry(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    registry = {}
    for record in records:
        if record.get("classification") in {
            "ambiguous_repeated_identity",
            "ambiguous_structure_requires_review",
            "presence_requires_review",
        }:
            registry[(record["customer_id"], record["identity_key"])] = record
    return registry


def _lookup_path(payload: Any, path: str) -> Any:
    current = payload
    normalized = path.removeprefix("$.")
    for segment in normalized.split("."):
        if not isinstance(current, dict) or segment not in current:
            return _MISSING
        current = current[segment]
    return current


def _append_conflict(
    context: dict[str, Any],
    path: str,
    base: Any,
    customer: Any,
    target: Any,
    reason: str,
) -> None:
    context["conflicts"].append(
        MergeConflict(
            customer_id=context["customer_id"],
            identity_key=context["identity_key"],
            path=path,
            standard_source_value=None if base is _MISSING else deepcopy(base),
            customer_source_value=None if customer is _MISSING else deepcopy(customer),
            standard_target_value=None if target is _MISSING else deepcopy(target),
            reason=reason,
        )
    )


def _merge_value(
    base: Any,
    customer: Any,
    target: Any,
    *,
    path: str,
    context: dict[str, Any],
) -> Any:
    """
    Conservative recursive three-way merge.

    AML collection dictionaries (for example fields and relationships) are
    traversed by key. This is important: treating an entire relationship
    dictionary as one value could accidentally include a review-required child.
    """
    base_identity = identity_from_payload(base)
    target_identity = identity_from_payload(target)

    # A new nested AML Item is accepted only if it is not marked for review.
    # Unknown nested additions are also held for review by default.
    if target_identity and base is _MISSING and customer is _MISSING:
        reason = (
            f"Nested AML identity {target_identity} is marked for review."
            if target_identity in context["review_identities"]
            else f"Nested AML identity {target_identity} has no baseline; manual review is required."
        )
        context["operations"].append(
            MergeOperation(
                customer_id=context["customer_id"],
                identity_key=context["identity_key"],
                operation="skip_review_required",
                path=path,
                reason=reason,
            )
        )
        return _MISSING

    # Vendor removal of an existing AML Item requires lineage proof.
    if base_identity and target is _MISSING and customer == base:
        context["operations"].append(
            MergeOperation(
                customer_id=context["customer_id"],
                identity_key=context["identity_key"],
                operation="skip_vendor_deletion",
                path=path,
                reason=f"Vendor deletion of {base_identity} requires lineage proof; preserved Customer Source item.",
            )
        )
        return deepcopy(customer)

    if target == base:
        return deepcopy(customer) if customer is not _MISSING else _MISSING

    if customer == base:
        # A vendor deletion of any existing value is conservative-review only.
        if target is _MISSING and base is not _MISSING:
            context["operations"].append(
                MergeOperation(
                    customer_id=context["customer_id"],
                    identity_key=context["identity_key"],
                    operation="skip_vendor_deletion",
                    path=path,
                    reason="Vendor deletion requires lineage proof; preserved Customer Source value.",
                )
            )
            return deepcopy(customer)

        # Recurse into containers so nested identities are checked individually.
        if isinstance(target, dict) and (
            base is _MISSING or isinstance(base, dict)
        ) and (customer is _MISSING or isinstance(customer, dict)):
            base_dict = {} if base is _MISSING else base
            customer_dict = {} if customer is _MISSING else customer
            target_dict = target
            merged = {}
            keys = sorted(set(base_dict) | set(customer_dict) | set(target_dict))
            for key in keys:
                child = _merge_value(
                    base_dict.get(key, _MISSING),
                    customer_dict.get(key, _MISSING),
                    target_dict.get(key, _MISSING),
                    path=f"{path}.{key}",
                    context=context,
                )
                if child is not _MISSING:
                    merged[key] = child
            return merged

        context["operations"].append(
            MergeOperation(
                customer_id=context["customer_id"],
                identity_key=context["identity_key"],
                operation="apply_vendor_change",
                path=path,
                reason="Only Standard Target changed this value.",
            )
        )
        return deepcopy(target) if target is not _MISSING else _MISSING

    if customer == target:
        return deepcopy(customer) if customer is not _MISSING else _MISSING

    # Combine independent dictionary-level changes recursively.
    if all(value is _MISSING or isinstance(value, dict) for value in (base, customer, target)):
        base_dict = {} if base is _MISSING else base
        customer_dict = {} if customer is _MISSING else customer
        target_dict = {} if target is _MISSING else target
        merged = {}
        keys = sorted(set(base_dict) | set(customer_dict) | set(target_dict))

        for key in keys:
            child = _merge_value(
                base_dict.get(key, _MISSING),
                customer_dict.get(key, _MISSING),
                target_dict.get(key, _MISSING),
                path=f"{path}.{key}",
                context=context,
            )
            if child is not _MISSING:
                merged[key] = child

        return merged

    _append_conflict(
        context,
        path,
        base,
        customer,
        target,
        "Customer Source and Standard Target changed the same value differently; Customer Source was preserved.",
    )
    return deepcopy(customer) if customer is not _MISSING else _MISSING


def _add_review_item(record: dict[str, Any], result: MergeResult) -> None:
    result.review_queue.append(
        MergeReviewItem(
            customer_id=record["customer_id"],
            identity_key=record["identity_key"],
            classification=record.get("classification", "requires_review"),
            reason=(
                "Identity is repeated, ambiguous, or not common across the three snapshots. "
                "It was not automatically merged."
            ),
            standard_source_occurrences=record.get("standard_source_occurrences", 0),
            customer_source_occurrences=record.get("customer_source_occurrences", 0),
            standard_target_occurrences=record.get("standard_target_occurrences", 0),
        )
    )


def merge_semantic_report(report: Any) -> MergeResult:
    """
    Build normalized Customer Target items from a semantic comparison report.

    This function does not read or write source AML XML files. It operates only
    on the normalized payloads already present in the semantic report.
    """
    report_data = _as_dict(report)
    records = report_data.get("records", [])
    review_registry = _review_registry(records)
    review_ids_by_customer = {
        customer_id: {
            identity_key
            for (registered_customer, identity_key) in review_registry
            if registered_customer == customer_id
        }
        for customer_id, _ in review_registry
    }

    result = MergeResult()

    for record in records:
        customer_id = record["customer_id"]
        identity_key = record["identity_key"]
        classification = record.get("classification", "")

        if classification in {
            "ambiguous_repeated_identity",
            "ambiguous_structure_requires_review",
            "presence_requires_review",
        }:
            _add_review_item(record, result)
            result.operations.append(
                MergeOperation(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    operation="skip_ambiguous",
                    reason="The semantic analyzer marked this identity as requiring review.",
                )
            )
            continue

        base = record.get("standard_source_payload")
        customer = record.get("customer_source_payload")
        target = record.get("standard_target_payload")

        if not isinstance(customer, dict):
            # No trustworthy CS payload means we cannot safely construct CT.
            result.operations.append(
                MergeOperation(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    operation="skip_ambiguous",
                    reason="Customer Source payload is unavailable; no output item was generated.",
                )
            )
            continue

        if classification == "unchanged":
            merged_payload = deepcopy(customer)
            result.operations.append(
                MergeOperation(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    operation="preserve_customer",
                    reason="No semantic changes were detected.",
                )
            )

        elif classification in {"customer_only_change", "customer_only"}:
            merged_payload = deepcopy(customer)
            result.operations.append(
                MergeOperation(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    operation="preserve_customer",
                    reason="Only the customer changed this identity.",
                )
            )

        elif classification in {"vendor_only_change", "customer_and_vendor_changes_no_conflict"}:
            context = {
                "customer_id": customer_id,
                "identity_key": identity_key,
                "review_identities": review_ids_by_customer.get(customer_id, set()),
                "operations": result.operations,
                "conflicts": result.conflicts,
            }

            merged_payload = _merge_value(
                base if isinstance(base, dict) else {},
                customer,
                target if isinstance(target, dict) else {},
                path="$",
                context=context,
            )

            if not isinstance(merged_payload, dict):
                merged_payload = deepcopy(customer)

            operation = (
                "combine_changes"
                if classification == "customer_and_vendor_changes_no_conflict"
                else "apply_vendor_change"
            )
            result.operations.append(
                MergeOperation(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    operation=operation,
                    reason="Applied the recursive three-way merge policy; nested review items and vendor deletions are guarded.",
                )
            )

        elif classification in {"conflict", "customer_and_vendor_changes_with_conflict"}:
            merged_payload = deepcopy(customer)

            conflict_paths = record.get("conflicting_fields", []) or ["$"]
            for conflict_path in conflict_paths:
                base_value = _lookup_path(base, conflict_path) if isinstance(base, dict) else _MISSING
                customer_value = _lookup_path(customer, conflict_path)
                target_value = _lookup_path(target, conflict_path) if isinstance(target, dict) else _MISSING
                _append_conflict(
                    {
                        "customer_id": customer_id,
                        "identity_key": identity_key,
                        "conflicts": result.conflicts,
                    },
                    conflict_path,
                    base_value,
                    customer_value,
                    target_value,
                    "The semantic analyzer detected different customer and vendor changes; Customer Source was preserved pending review.",
                )

            result.operations.append(
                MergeOperation(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    operation="skip_conflict",
                    reason="The semantic analyzer detected a conflict; Customer Source was preserved pending review.",
                )
            )

        else:
            _add_review_item(record, result)
            result.operations.append(
                MergeOperation(
                    customer_id=customer_id,
                    identity_key=identity_key,
                    operation="skip_ambiguous",
                    reason=f"Unsupported or unrecognized classification: {classification}",
                )
            )
            continue

        result.items.append(
            MergedItem(
                customer_id=customer_id,
                identity_key=identity_key,
                payload=merged_payload,
            )
        )

    result.summary = {
        "input_records": len(records),
        "generated_items": len(result.items),
        "review_items": len(result.review_queue),
        "conflicts": len(result.conflicts),
        "operations": len(result.operations),
    }
    return result
