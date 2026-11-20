from aml_upgrade.merge.merge_engine import merge_semantic_report


def make_record(classification, base, customer, target, identity="Item:A"):
    item_type, item_id = identity.split(":", 1)
    return {
        "customer_id": "Customer_1",
        "identity_key": identity,
        "item_type": item_type,
        "item_id": item_id,
        "classification": classification,
        "standard_source_payload": base,
        "customer_source_payload": customer,
        "standard_target_payload": target,
        "standard_source_occurrences": 1,
        "customer_source_occurrences": 1,
        "standard_target_occurrences": 1,
    }


def payload(**fields):
    return {
        "item_type": "Item",
        "item_id": "A",
        "attributes": {"id": "A", "type": "Item"},
        "fields": fields,
        "relationships": {},
    }


def test_vendor_only_change_is_applied():
    base = payload(name={"value": "Original"})
    customer = payload(name={"value": "Original"})
    target = payload(name={"value": "Updated"})

    result = merge_semantic_report({
        "records": [make_record("vendor_only_change", base, customer, target)]
    })

    assert result.items[0].payload["fields"]["name"]["value"] == "Updated"
    assert result.summary["generated_items"] == 1


def test_customer_only_change_is_preserved():
    base = payload(name={"value": "Original"})
    customer = payload(name={"value": "Customer"})
    target = payload(name={"value": "Original"})

    result = merge_semantic_report({
        "records": [make_record("customer_only_change", base, customer, target)]
    })

    assert result.items[0].payload["fields"]["name"]["value"] == "Customer"


def test_independent_changes_are_combined():
    base = payload(name={"value": "Original"}, description={"value": "Old"})
    customer = payload(name={"value": "Customer Name"}, description={"value": "Old"})
    target = payload(name={"value": "Original"}, description={"value": "Vendor Description"})

    result = merge_semantic_report({
        "records": [
            make_record(
                "customer_and_vendor_changes_no_conflict",
                base,
                customer,
                target,
            )
        ]
    })

    fields = result.items[0].payload["fields"]
    assert fields["name"]["value"] == "Customer Name"
    assert fields["description"]["value"] == "Vendor Description"
    assert result.summary["conflicts"] == 0


def test_same_field_conflict_preserves_customer_and_records_conflict():
    base = payload(name={"value": "Original"})
    customer = payload(name={"value": "Customer"})
    target = payload(name={"value": "Vendor"})

    result = merge_semantic_report({
        "records": [make_record("vendor_only_change", base, customer, target)]
    })

    # The classification normally comes from the analyzer. This test exercises
    # the recursive conflict guard even if an upstream report is inconsistent.
    assert result.items[0].payload["fields"]["name"]["value"] == "Customer"
    assert result.summary["conflicts"] == 1


def test_review_required_nested_item_is_not_added():
    base = payload()
    customer = payload()
    nested = {
        "item_type": "Field",
        "item_id": "REVIEW-1",
        "attributes": {"id": "REVIEW-1", "type": "Field"},
        "fields": {"name": {"value": "Image"}},
        "relationships": {},
    }
    target = payload()
    target["relationships"] = {"Field:REVIEW-1": nested}

    parent = make_record("vendor_only_change", base, customer, target)
    review = {
        "customer_id": "Customer_1",
        "identity_key": "Field:REVIEW-1",
        "classification": "presence_requires_review",
        "standard_source_payload": None,
        "customer_source_payload": None,
        "standard_target_payload": None,
        "standard_source_occurrences": 0,
        "customer_source_occurrences": 0,
        "standard_target_occurrences": 1,
    }

    result = merge_semantic_report({"records": [parent, review]})

    assert "Field:REVIEW-1" not in result.items[0].payload["relationships"]
    assert any(item.identity_key == "Field:REVIEW-1" for item in result.review_queue)
    assert any(op.operation == "skip_review_required" for op in result.operations)


def test_vendor_deletion_is_not_applied_automatically():
    base = payload(name={"value": "Original"})
    customer = payload(name={"value": "Original"})
    target = payload()
    target["fields"] = {}

    result = merge_semantic_report({
        "records": [make_record("vendor_only_change", base, customer, target)]
    })

    assert result.items[0].payload["fields"]["name"]["value"] == "Original"
    assert any(op.operation == "skip_vendor_deletion" for op in result.operations)


def test_review_classified_top_level_identity_is_not_generated():
    review = {
        "customer_id": "Customer_1",
        "identity_key": "Field:REPEATED",
        "classification": "ambiguous_repeated_identity",
        "standard_source_payload": None,
        "customer_source_payload": None,
        "standard_target_payload": None,
        "standard_source_occurrences": 2,
        "customer_source_occurrences": 2,
        "standard_target_occurrences": 2,
    }

    result = merge_semantic_report({"records": [review]})

    assert result.items == []
    assert len(result.review_queue) == 1



def test_semantic_conflict_is_added_to_conflict_queue():
    base = payload(name={"value": "Original"})
    customer = payload(name={"value": "Customer"})
    target = payload(name={"value": "Vendor"})
    record = make_record("conflict", base, customer, target)
    record["conflicting_fields"] = ["fields.name.value"]

    result = merge_semantic_report({"records": [record]})

    assert result.items[0].payload["fields"]["name"]["value"] == "Customer"
    assert len(result.conflicts) == 1
    assert result.conflicts[0].path == "fields.name.value"
    assert result.conflicts[0].customer_source_value == "Customer"
    assert result.conflicts[0].standard_target_value == "Vendor"
