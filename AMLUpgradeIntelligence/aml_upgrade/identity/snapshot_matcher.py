
from collections import defaultdict
from pathlib import Path
from typing import Any

from aml_upgrade.identity.identity_extractor import (
    build_identity_inventory,
)
from aml_upgrade.models.matching import (
    SnapshotIdentityMatch,
    SnapshotMatchingReport,
)


SNAPSHOT_NAMES = (
    "StandardSource",
    "CustomerSource",
    "StandardTarget",
)


def classify_presence(
    in_ss: bool,
    in_cs: bool,
    in_st: bool,
) -> str:
    """
    Classify an identity according to its presence in SS, CS and ST.

    This function checks identity presence only. It does not compare
    the actual field values or determine whether an item was modified.
    """

    presence = (in_ss, in_cs, in_st)

    classifications = {
        (True, True, True): "present_in_all",
        (True, True, False): "missing_from_standard_target",
        (True, False, True): "missing_from_customer_source",
        (True, False, False): "missing_from_customer_and_target",
        (False, True, True): "added_in_customer_and_target",
        (False, True, False): "customer_only_addition",
        (False, False, True): "standard_target_only_addition",
    }

    return classifications.get(presence, "not_present")


def match_snapshot_identities(
    input_root: str | Path,
) -> SnapshotMatchingReport:
    """
    Match AML identities across StandardSource, CustomerSource
    and StandardTarget for every discovered customer.

    Repeated occurrences are preserved in their respective lists.
    Query records and records without identity keys are excluded
    from identity matching but counted in the report.
    """

    inventory = build_identity_inventory(input_root)

    # Structure:
    # (customer_id, identity_key) -> snapshot -> occurrences
    grouped: dict[
        tuple[str, str],
        dict[str, list[dict[str, Any]]],
    ] = defaultdict(
        lambda: {
            snapshot_name: []
            for snapshot_name in SNAPSHOT_NAMES
        }
    )

    for record in inventory.records:

        # Query operations are not ordinary item definitions.
        if record.is_query:
            continue

        # Records without a complete identity cannot be matched.
        if not record.identity_key:
            continue

        if record.snapshot_name not in SNAPSHOT_NAMES:
            continue

        group_key = (
            record.customer_id,
            record.identity_key,
        )

        # Keep every occurrence. Do not collapse repeated add/edit
        # operations into a single record.
        grouped[group_key][record.snapshot_name].append(
            record.model_dump()
        )

    matches: list[SnapshotIdentityMatch] = []

    classification_summary: dict[str, int] = defaultdict(int)

    for (customer_id, identity_key), snapshots in sorted(
        grouped.items()
    ):

        ss_records = snapshots["StandardSource"]
        cs_records = snapshots["CustomerSource"]
        st_records = snapshots["StandardTarget"]

        classification = classify_presence(
            in_ss=bool(ss_records),
            in_cs=bool(cs_records),
            in_st=bool(st_records),
        )

        # Read item details from the first available occurrence.
        # All occurrences are still preserved in the snapshot lists.
        first_record = (
            ss_records
            or cs_records
            or st_records
        )[0]

        has_repeated_occurrences = any(
            len(records) > 1
            for records in (ss_records, cs_records, st_records)
        )

        match = SnapshotIdentityMatch(
            customer_id=customer_id,
            identity_key=identity_key,
            item_type=first_record.get("item_type"),
            item_id=first_record.get("item_id"),
            standard_source=ss_records,
            customer_source=cs_records,
            standard_target=st_records,
            classification=classification,
            has_repeated_occurrences=has_repeated_occurrences,
        )

        matches.append(match)
        classification_summary[classification] += 1

    return SnapshotMatchingReport(
        matches=matches,
        total_matched_identities=len(matches),
        query_records_excluded=len(inventory.query_records),
        missing_identity_records_excluded=len(
            inventory.missing_identity_records
        ),
        repeated_identity_groups=len(inventory.duplicate_groups),
        classification_summary=dict(
            sorted(classification_summary.items())
        ),
    )
