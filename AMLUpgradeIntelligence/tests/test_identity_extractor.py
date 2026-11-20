
from aml_upgrade.identity.identity_extractor import (
    build_identity_inventory,
    make_identity_key,
)


SNAPSHOTS = (
    "StandardSource",
    "CustomerSource",
    "StandardTarget",
)


def create_dataset(root):
    for snapshot in SNAPSHOTS:
        folder = root / "Customer_1" / snapshot
        folder.mkdir(parents=True)

    return root


def test_make_identity_key():
    assert make_identity_key("Part", "part-001") == "Part:part-001"
    assert make_identity_key("Part", None) is None
    assert make_identity_key(None, "part-001") is None


def test_inventory_extracts_top_level_identity(tmp_path):
    root = create_dataset(tmp_path)

    file_path = (
        root / "Customer_1" / "StandardSource" / "part.xml"
    )

    file_path.write_text(
        '<AML><Item type="Part" id="part-001" action="add">'
        '<name>Bolt</name></Item></AML>',
        encoding="utf-8",
    )

    inventory = build_identity_inventory(root)

    assert len(inventory.records) == 1

    record = inventory.records[0]

    assert record.item_type == "Part"
    assert record.item_id == "part-001"
    assert record.action == "add"
    assert record.identity_key == "Part:part-001"
    assert record.is_top_level is True


def test_inventory_extracts_relationship_identity(tmp_path):
    root = create_dataset(tmp_path)

    file_path = (
        root / "Customer_1" / "StandardSource" / "part.xml"
    )

    file_path.write_text(
        """
        <AML>
            <Item type="Part" id="part-001">
                <Relationships>
                    <Item type="Part BOM" id="bom-001">
                        <quantity>2</quantity>
                    </Item>
                </Relationships>
            </Item>
        </AML>
        """,
        encoding="utf-8",
    )

    inventory = build_identity_inventory(root)

    assert len(inventory.records) == 2

    relationship = next(
        record for record in inventory.records
        if record.item_type == "Part BOM"
    )

    assert relationship.identity_key == "Part BOM:bom-001"
    assert relationship.parent_identity_key == "Part:part-001"
    assert relationship.is_top_level is False


def test_inventory_detects_repeated_identity(tmp_path):
    root = create_dataset(tmp_path)

    folder = root / "Customer_1" / "StandardSource"

    (folder / "part_a.xml").write_text(
        '<AML><Item type="Part" id="part-001" action="add"/></AML>',
        encoding="utf-8",
    )

    (folder / "part_b.xml").write_text(
        '<AML><Item type="Part" id="part-001" action="edit"/></AML>',
        encoding="utf-8",
    )

    inventory = build_identity_inventory(root)

    assert len(inventory.duplicate_groups) == 1

    duplicate = inventory.duplicate_groups[0]

    assert duplicate.identity_key == "Part:part-001"
    assert len(duplicate.occurrences) == 2


def test_inventory_detects_missing_identity(tmp_path):
    root = create_dataset(tmp_path)

    file_path = (
        root / "Customer_1" / "StandardSource" / "part.xml"
    )

    file_path.write_text(
        '<AML><Item type="Part"><name>Bolt</name></Item></AML>',
        encoding="utf-8",
    )

    inventory = build_identity_inventory(root)

    assert len(inventory.missing_identity_records) == 1
    assert inventory.missing_identity_records[0].item_id is None

def test_inventory_classifies_get_items_as_queries(tmp_path):
    root = create_dataset(tmp_path)

    file_path = (
        root / "Customer_1" / "StandardSource" / "query.xml"
    )

    file_path.write_text(
        """
        <AML>
            <Item type="Part" id="part-001">
                <related_id>
                    <Item type="Part" action="get">
                        <item_number>PART-100</item_number>
                    </Item>
                </related_id>
            </Item>
        </AML>
        """,
        encoding="utf-8",
    )

    inventory = build_identity_inventory(root)

    assert len(inventory.query_records) == 1
    assert inventory.query_records[0].item_type == "Part"
    assert inventory.query_records[0].action == "get"
    assert inventory.query_records[0].is_query is True

    assert len(inventory.missing_identity_records) == 0
