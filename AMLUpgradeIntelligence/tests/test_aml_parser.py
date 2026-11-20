
import pytest

from aml_upgrade.parsers.aml_parser import (
    AMLParseError,
    parse_aml_file,
)


def test_parser_extracts_item_details_and_fields(tmp_path):
    aml_file = tmp_path / "sample.xml"

    aml_file.write_text(
        """
        <AML>
            <Item type="Part" id="part-001" action="add">
                <item_number>PART-100</item_number>
                <name>Industrial Bolt</name>
                <propertytype_id
                    type="Property"
                    keyed_name="Part Number"
                >property-001</propertytype_id>
            </Item>
        </AML>
        """,
        encoding="utf-8",
    )

    document = parse_aml_file(aml_file)

    assert document.root_element == "AML"
    assert len(document.items) == 1

    item = document.items[0]

    assert item.item_type == "Part"
    assert item.item_id == "part-001"
    assert item.action == "add"

    item_number = next(
        field for field in item.fields
        if field.name == "item_number"
    )

    assert item_number.value == "PART-100"


def test_parser_extracts_references(tmp_path):
    aml_file = tmp_path / "reference.xml"

    aml_file.write_text(
        """
        <AML>
            <Item type="Part" id="part-001">
                <propertytype_id
                    type="Property"
                    keyed_name="Part Number"
                >property-001</propertytype_id>
            </Item>
        </AML>
        """,
        encoding="utf-8",
    )

    document = parse_aml_file(aml_file)
    item = document.items[0]

    reference_field = next(
        field for field in item.fields
        if field.name == "propertytype_id"
    )

    assert reference_field.reference is not None
    assert reference_field.reference.target_id == "property-001"
    assert reference_field.reference.target_type == "Property"
    assert reference_field.reference.keyed_name == "Part Number"


def test_parser_extracts_nested_relationships(tmp_path):
    aml_file = tmp_path / "relationship.xml"

    aml_file.write_text(
        """
        <AML>
            <Item type="Part" id="part-001">
                <Relationships>
                    <Item type="Part BOM" id="relationship-001">
                        <quantity>4</quantity>
                        <related_id
                            type="Part"
                            keyed_name="Bolt"
                        >part-002</related_id>
                    </Item>
                </Relationships>
            </Item>
        </AML>
        """,
        encoding="utf-8",
    )

    document = parse_aml_file(aml_file)
    parent = document.items[0]

    assert len(parent.relationships) == 1

    relationship = parent.relationships[0]

    assert relationship.item_type == "Part BOM"
    assert relationship.item_id == "relationship-001"

    quantity = next(
        field for field in relationship.fields
        if field.name == "quantity"
    )

    assert quantity.value == "4"


def test_parser_handles_multiple_top_level_items(tmp_path):
    aml_file = tmp_path / "multiple.xml"

    aml_file.write_text(
        """
        <AML>
            <Item type="Part" id="part-001" />
            <Item type="Property" id="property-001" />
        </AML>
        """,
        encoding="utf-8",
    )

    document = parse_aml_file(aml_file)

    assert len(document.items) == 2
    assert document.items[0].item_type == "Part"
    assert document.items[1].item_type == "Property"


def test_parser_rejects_wrong_root(tmp_path):
    aml_file = tmp_path / "wrong_root.xml"

    aml_file.write_text(
        "<Root><Item type='Part' id='123'/></Root>",
        encoding="utf-8",
    )

    with pytest.raises(AMLParseError):
        parse_aml_file(aml_file)


def test_parser_rejects_malformed_xml(tmp_path):
    aml_file = tmp_path / "malformed.xml"

    aml_file.write_text(
        "<AML><Item type='Part'>",
        encoding="utf-8",
    )

    with pytest.raises(AMLParseError):
        parse_aml_file(aml_file)


def test_parser_rejects_dtd_declarations(tmp_path):
    aml_file = tmp_path / "unsafe.xml"

    aml_file.write_text(
        """<!DOCTYPE AML [<!ENTITY example "unsafe">]>
        <AML><Item type="Part" id="123">&example;</Item></AML>""",
        encoding="utf-8",
    )

    with pytest.raises(AMLParseError):
        parse_aml_file(aml_file)
