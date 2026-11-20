
from pathlib import Path

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from aml_upgrade.models.aml_item import (
    AMLDocument,
    AMLField,
    AMLReference,
    NormalizedAMLItem,
)


class AMLParseError(ValueError):
    """Raised when an AML document cannot be parsed safely."""


def get_local_name(tag: str) -> str:
    """Remove an XML namespace from an element name."""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def parse_field(element) -> AMLField:
    """Convert an XML property element into a structured AMLField."""

    name = get_local_name(element.tag)
    attributes = dict(element.attrib)

    direct_text = (element.text or "").strip()

    reference = None

    # AML references commonly contain type/keyed_name attributes.
    if "type" in attributes or "keyed_name" in attributes:
        reference = AMLReference(
            element_name=name,
            target_id=direct_text or None,
            target_type=attributes.get("type"),
            keyed_name=attributes.get("keyed_name"),
            attributes=attributes,
        )

    child_fields = []
    child_items = []

    for child in list(element):
        child_name = get_local_name(child.tag)

        if child_name == "Item":
            child_items.append(parse_item(child))
        else:
            child_fields.append(parse_field(child))

    return AMLField(
        name=name,
        value=direct_text or None,
        attributes=attributes,
        reference=reference,
        children=child_fields,
        items=child_items,
    )


def parse_item(element) -> NormalizedAMLItem:
    """Convert an XML Item element into a NormalizedAMLItem."""

    attributes = dict(element.attrib)

    fields = []
    relationships = []

    for child in list(element):
        child_name = get_local_name(child.tag)

        if child_name == "Relationships":
            # Relationship Items are stored separately from normal fields.
            for relationship in list(child):
                if get_local_name(relationship.tag) == "Item":
                    relationships.append(parse_item(relationship))
                else:
                    fields.append(parse_field(relationship))

        elif child_name == "Item":
            # Preserve directly nested Items as nested items.
            relationships.append(parse_item(child))

        else:
            fields.append(parse_field(child))

    return NormalizedAMLItem(
        item_type=attributes.get("type"),
        item_id=attributes.get("id"),
        action=attributes.get("action"),
        attributes=attributes,
        fields=fields,
        relationships=relationships,
    )


def parse_aml_file(file_path: str | Path) -> AMLDocument:
    """Safely parse an AML XML file into a normalized document."""

    path = Path(file_path)

    if not path.is_file():
        raise AMLParseError(f"AML file does not exist: {path}")

    try:
        tree = SafeET.parse(
            str(path),
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )

        root = tree.getroot()
        root_name = get_local_name(root.tag)

        if root_name != "AML":
            raise AMLParseError(
                f"Expected AML root element, found '{root_name}'"
            )

        items = []

        for element in list(root):
            if get_local_name(element.tag) == "Item":
                items.append(parse_item(element))

        return AMLDocument(
            source_file=str(path),
            root_element=root_name,
            items=items,
        )

    except AMLParseError:
        raise

    except (
        DefusedXmlException,
        SafeET.ParseError,
        OSError,
        ValueError,
    ) as exc:
        raise AMLParseError(
            f"Could not safely parse '{path}': "
            f"{type(exc).__name__}: {exc}"
        ) from exc
