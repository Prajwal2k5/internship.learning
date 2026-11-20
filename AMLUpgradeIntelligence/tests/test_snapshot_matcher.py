
from pathlib import Path

import pytest

from aml_upgrade.identity.snapshot_matcher import (
    classify_presence,
    match_snapshot_identities,
)


@pytest.mark.parametrize(
    ("in_ss", "in_cs", "in_st", "expected"),
    [
        (True, True, True, "present_in_all"),
        (True, True, False, "missing_from_standard_target"),
        (True, False, True, "missing_from_customer_source"),
        (
            True,
            False,
            False,
            "missing_from_customer_and_target",
        ),
        (False, True, True, "added_in_customer_and_target"),
        (False, True, False, "customer_only_addition"),
        (False, False, True, "standard_target_only_addition"),
    ],
)
def test_classify_presence(
    in_ss,
    in_cs,
    in_st,
    expected,
):
    assert classify_presence(in_ss, in_cs, in_st) == expected


def write_aml_file(
    folder: Path,
    items: list[str],
) -> None:
    folder.mkdir(parents=True, exist_ok=True)

    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<AML>"
        + "".join(items)
        + "</AML>"
    )

    (folder / "items.xml").write_text(
        content,
        encoding="utf-8",
    )


def make_item(
    item_id: str,
    action: str = "edit",
) -> str:
    return (
        f'<Item type="Part" id="{item_id}" '
        f'action="{action}">'
        f"<name>{item_id}</name>"
        "</Item>"
    )


def test_matcher_matches_identities_across_snapshots(
    tmp_path,
):
    root = tmp_path / "input_data"
    customer = root / "Customer_1"

    snapshot_items = {
        "StandardSource": [
            make_item("common", "add"),
            make_item("common", "edit"),
            make_item("vendor_removed"),
            make_item("customer_removed"),
            make_item("baseline_only"),
            (
                '<Item type="Method" action="get">'
                "<name>Lookup</name>"
                "</Item>"
            ),
            (
                '<Item type="Part" action="edit">'
                "<name>Missing identity</name>"
                "</Item>"
            ),
        ],
        "CustomerSource": [
            make_item("common"),
            make_item("vendor_removed"),
            make_item("customer_only"),
            make_item("both_added"),
        ],
        "StandardTarget": [
            make_item("common"),
            make_item("customer_removed"),
            make_item("target_only"),
            make_item("both_added"),
        ],
    }

    for snapshot_name, items in snapshot_items.items():
        write_aml_file(
            customer / snapshot_name,
            items,
        )

    report = match_snapshot_identities(root)

    assert report.total_matched_identities == 7

    assert report.query_records_excluded == 1
    assert report.missing_identity_records_excluded == 1

    assert report.repeated_identity_groups == 1

    matches = {
        match.identity_key: match
        for match in report.matches
    }

    assert (
        matches["Part:common"].classification
        == "present_in_all"
    )

    assert (
        matches["Part:vendor_removed"].classification
        == "missing_from_standard_target"
    )

    assert (
        matches["Part:customer_removed"].classification
        == "missing_from_customer_source"
    )

    assert (
        matches["Part:baseline_only"].classification
        == "missing_from_customer_and_target"
    )

    assert (
        matches["Part:customer_only"].classification
        == "customer_only_addition"
    )

    assert (
        matches["Part:target_only"].classification
        == "standard_target_only_addition"
    )

    assert (
        matches["Part:both_added"].classification
        == "added_in_customer_and_target"
    )

    # The two operations for "common" in SS must both be preserved.
    common = matches["Part:common"]

    assert common.has_repeated_occurrences is True
    assert len(common.standard_source) == 2
    assert len(common.customer_source) == 1
    assert len(common.standard_target) == 1
