import pytest

from aml_upgrade.identity.semantic_analyzer import (
    canonicalize_item,
    compare_payloads,
    flatten_payload,
)
from aml_upgrade.models.aml_item import (
    AMLField,
    NormalizedAMLItem,
)


# ---------------------------------------------------------
# Existing three-way comparison tests
# ---------------------------------------------------------

@pytest.mark.parametrize(
    (
        "ss",
        "cs",
        "st",
        "expected",
        "expected_conflicts",
    ),
    [
        (
            {"name": "Original"},
            {"name": "Original"},
            {"name": "Original"},
            "unchanged",
            [],
        ),
        (
            {"name": "Original"},
            {"name": "Customer Version"},
            {"name": "Original"},
            "customer_only_change",
            [],
        ),
        (
            {"name": "Original"},
            {"name": "Original"},
            {"name": "Vendor Version"},
            "vendor_only_change",
            [],
        ),
        (
            {"name": "Original"},
            {"name": "Customer Version"},
            {"name": "Vendor Version"},
            "conflict",
            ["name"],
        ),
        (
            {"name": "Original", "description": "Old"},
            {
                "name": "Customer Version",
                "description": "Old",
            },
            {
                "name": "Original",
                "description": "Vendor Description",
            },
            "customer_and_vendor_changes_no_conflict",
            [],
        ),
        (
            {"name": "Original"},
            {"name": "Updated"},
            {"name": "Updated"},
            "customer_and_vendor_changes_no_conflict",
            [],
        ),
    ],
)
def test_compare_payloads(
    ss,
    cs,
    st,
    expected,
    expected_conflicts,
):
    (
        classification,
        customer_changes,
        vendor_changes,
        conflicting_fields,
        convergent_fields,
    ) = compare_payloads(ss, cs, st)

    assert classification == expected
    assert conflicting_fields == expected_conflicts


def test_conflict_detected_only_on_same_field():
    ss = {
        "name": "Original",
        "description": "Old",
    }

    cs = {
        "name": "Customer Name",
        "description": "Old",
    }

    st = {
        "name": "Vendor Name",
        "description": "Vendor Description",
    }

    result = compare_payloads(ss, cs, st)

    assert result[0] == "conflict"
    assert result[3] == ["name"]
    assert result[1] == ["name"]
    assert result[2] == ["description", "name"]


# ---------------------------------------------------------
# Structure-aware comparison tests
# ---------------------------------------------------------

def create_item(
    item_type,
    item_id,
    fields=None,
    relationships=None,
):
    """Helper to create normalized AML items for testing."""

    return NormalizedAMLItem(
        item_type=item_type,
        item_id=item_id,
        fields=fields or [],
        relationships=relationships or [],
    )


def test_field_insertion_does_not_shift_existing_fields():
    """Adding a field must not falsely change existing fields."""

    ss_item = create_item(
        "Part",
        "part-1",
        [
            AMLField(name="name", value="Water Pump"),
            AMLField(name="description", value="Original"),
        ],
    )

    cs_item = create_item(
        "Part",
        "part-1",
        [
            AMLField(name="name", value="Water Pump"),
            AMLField(name="description", value="Original"),
        ],
    )

    st_item = create_item(
        "Part",
        "part-1",
        [
            AMLField(name="new_property", value="Vendor Addition"),
            AMLField(name="name", value="Water Pump"),
            AMLField(name="description", value="Original"),
        ],
    )

    result = compare_payloads(
        canonicalize_item(ss_item),
        canonicalize_item(cs_item),
        canonicalize_item(st_item),
    )

    assert result[0] == "vendor_only_change"
    assert result[1] == []
    assert result[2]
    assert all("new_property" in path for path in result[2])


def test_nested_relationship_addition_is_detected():
    """A newly added relationship must be detected."""

    ss_item = create_item("Part", "parent-1")
    cs_item = create_item("Part", "parent-1")

    new_relationship = create_item(
        "Part BOM",
        "relationship-1",
        [
            AMLField(name="quantity", value="2"),
        ],
    )

    st_item = create_item(
        "Part",
        "parent-1",
        relationships=[new_relationship],
    )

    result = compare_payloads(
        canonicalize_item(ss_item),
        canonicalize_item(cs_item),
        canonicalize_item(st_item),
    )

    assert result[0] == "vendor_only_change"
    assert result[1] == []
    assert result[2] == [
        "relationships.Part BOM:relationship-1"
    ]


def test_nested_relationship_field_modification_is_detected():
    """A changed field inside an existing relationship is detected."""

    ss_relationship = create_item(
        "Part BOM",
        "relationship-1",
        [AMLField(name="quantity", value="2")],
    )

    cs_relationship = create_item(
        "Part BOM",
        "relationship-1",
        [AMLField(name="quantity", value="2")],
    )

    st_relationship = create_item(
        "Part BOM",
        "relationship-1",
        [AMLField(name="quantity", value="5")],
    )

    ss = canonicalize_item(
        create_item(
            "Part",
            "parent-1",
            relationships=[ss_relationship],
        )
    )

    cs = canonicalize_item(
        create_item(
            "Part",
            "parent-1",
            relationships=[cs_relationship],
        )
    )

    st = canonicalize_item(
        create_item(
            "Part",
            "parent-1",
            relationships=[st_relationship],
        )
    )

    result = compare_payloads(ss, cs, st)

    assert result[0] == "vendor_only_change"
    assert any("quantity.value" in path for path in result[2])


def test_repeated_field_names_are_flagged():
    """Repeated field names must be marked ambiguous."""

    item = create_item(
        "Part",
        "part-1",
        [
            AMLField(name="name", value="First"),
            AMLField(name="name", value="Second"),
        ],
    )

    ambiguities = []
    canonicalize_item(item, ambiguities=ambiguities)

    assert any(
        "repeated field name" in message
        for message in ambiguities
    )


def test_repeated_nested_item_identities_are_flagged():
    """Repeated nested identities must be marked ambiguous."""

    first_relationship = create_item(
        "Part BOM",
        "relationship-1",
    )

    second_relationship = create_item(
        "Part BOM",
        "relationship-1",
    )

    item = create_item(
        "Part",
        "parent-1",
        relationships=[
            first_relationship,
            second_relationship,
        ],
    )

    ambiguities = []
    canonicalize_item(item, ambiguities=ambiguities)

    assert any(
        "repeated nested item identity" in message
        for message in ambiguities
    )


# ---------------------------------------------------------
# Regression tests for compact semantic paths
# ---------------------------------------------------------

def test_added_nested_relationship_is_reported_once():
    """A complete nested item addition should produce one change path."""

    ss_item = create_item("Part", "parent-1")
    cs_item = create_item("Part", "parent-1")

    new_relationship = create_item(
        "Part BOM",
        "relationship-1",
        [
            AMLField(name="quantity", value="2"),
            AMLField(name="notes", value="New relationship"),
        ],
    )

    st_item = create_item(
        "Part",
        "parent-1",
        relationships=[new_relationship],
    )

    result = compare_payloads(
        canonicalize_item(ss_item),
        canonicalize_item(cs_item),
        canonicalize_item(st_item),
    )

    assert result[0] == "vendor_only_change"
    assert result[1] == []
    assert result[2] == [
        "relationships.Part BOM:relationship-1"
    ]


def test_removed_nested_relationship_is_reported_once():
    """A complete nested item removal should produce one change path."""

    old_relationship = create_item(
        "Part BOM",
        "relationship-1",
        [
            AMLField(name="quantity", value="2"),
            AMLField(name="notes", value="Old relationship"),
        ],
    )

    ss_item = create_item(
        "Part",
        "parent-1",
        relationships=[old_relationship],
    )

    cs_item = create_item(
        "Part",
        "parent-1",
        relationships=[old_relationship],
    )

    st_item = create_item("Part", "parent-1")

    result = compare_payloads(
        canonicalize_item(ss_item),
        canonicalize_item(cs_item),
        canonicalize_item(st_item),
    )

    assert result[0] == "vendor_only_change"
    assert result[1] == []
    assert result[2] == [
        "relationships.Part BOM:relationship-1"
    ]


def test_empty_field_structures_do_not_create_change_paths():
    """Empty AML field structures should not produce meaningless paths."""

    item = create_item(
        "Part",
        "part-1",
        [AMLField(name="empty_property")],
    )

    payload = canonicalize_item(item)
    flattened = flatten_payload(payload)

    assert not any(
        "empty_property" in path
        for path in flattened
    )
