import streamlit as st

from api import (
    get_parts,
    search_parts,
    create_part,
    update_part,
    delete_part,
    generate_part_ai_description
)


st.set_page_config(
    page_title="Part Management | MiniPLM",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Part Management")
st.write("Create, search, update and manage engineering parts.")

st.divider()

STATUSES = ["Draft", "In Review", "Released", "Obsolete"]


# -------------------------
# FETCH PARTS
# -------------------------

try:
    parts = get_parts()
except Exception as error:
    st.error(f"Unable to load parts: {error}")
    st.stop()


# -------------------------
# SEARCH PARTS
# -------------------------

st.subheader("🔍 Search Parts")

search_query = st.text_input(
    "Search by part name, part number, manufacturer or category",
    placeholder="Example: Industrial Water Pump"
)

if search_query.strip():
    try:
        displayed_parts = search_parts(search_query)
    except Exception as error:
        st.error(f"Search failed: {error}")
        displayed_parts = []
else:
    displayed_parts = parts


if displayed_parts:
    st.dataframe(
        [
            {
                "ID": part["id"],
                "Part Number": part["part_number"],
                "Name": part["name"],
                "Manufacturer": part["manufacturer"],
                "Category": part["category"],
                "Description": part["description"] or "",
                "Lifecycle Status": part["lifecycle_status"]
            }
            for part in displayed_parts
        ],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No matching parts found.")


st.divider()


# -------------------------
# CREATE NEW PART
# -------------------------

st.subheader("➕ Create New Part")

with st.form("create_part_form", clear_on_submit=True):

    name = st.text_input("Part Name")
    manufacturer = st.text_input("Manufacturer")
    category = st.text_input("Category")
    description = st.text_area("Description")

    status = st.selectbox(
        "Lifecycle Status",
        STATUSES,
        index=0
    )

    submitted = st.form_submit_button(
        "Create Part",
        use_container_width=True
    )

    if submitted:

        if not name.strip() or not manufacturer.strip() or not category.strip():
            st.warning("Please fill in the name, manufacturer and category.")

        else:
            part_data = {
                "name": name.strip(),
                "manufacturer": manufacturer.strip(),
                "category": category.strip(),
                "description": description.strip() or None,
                "lifecycle_status": status
            }

            try:
                result = create_part(part_data)

                st.success(
                    f"Part created successfully! "
                    f"Part Number: {result['part_number']}"
                )

                st.rerun()

            except Exception as error:
                st.error(f"Could not create part: {error}")


st.divider()


# -------------------------
# UPDATE EXISTING PART
# -------------------------

st.subheader("✏️ Update Part")

if parts:

    selected_id = st.selectbox(
        "Select a part to update",
        options=[part["id"] for part in parts],
        format_func=lambda part_id: next(
            (
                f"{part['part_number']} - {part['name']}"
                for part in parts
                if part["id"] == part_id
            ),
            str(part_id)
        ),
        key="update_part_selection"
    )

    selected_part = next(
        part for part in parts
        if part["id"] == selected_id
    )

    with st.form("update_part_form"):

        updated_name = st.text_input(
            "Part Name",
            value=selected_part["name"]
        )

        updated_manufacturer = st.text_input(
            "Manufacturer",
            value=selected_part["manufacturer"]
        )

        updated_category = st.text_input(
            "Category",
            value=selected_part["category"]
        )

        updated_description = st.text_area(
            "Description",
            value=selected_part["description"] or ""
        )

        current_status = selected_part["lifecycle_status"]

        updated_status = st.selectbox(
            "Lifecycle Status",
            STATUSES,
            index=STATUSES.index(current_status)
            if current_status in STATUSES else 0
        )

        update_submitted = st.form_submit_button(
            "Save Changes",
            use_container_width=True
        )

        if update_submitted:

            if (
                not updated_name.strip()
                or not updated_manufacturer.strip()
                or not updated_category.strip()
            ):
                st.warning("Name, manufacturer and category cannot be empty.")

            else:
                update_data = {
                    "name": updated_name.strip(),
                    "manufacturer": updated_manufacturer.strip(),
                    "category": updated_category.strip(),
                    "description": updated_description.strip() or None,
                    "lifecycle_status": updated_status
                }

                try:
                    update_part(selected_id, update_data)

                    st.success("Part updated successfully!")
                    st.rerun()

                except Exception as error:
                    st.error(f"Could not update part: {error}")

else:
    st.info("Create a part before trying to update one.")


st.divider()
# -------------------------
# AI PART DESCRIPTION
# -------------------------

st.divider()

st.subheader("🤖 AI Part Description Generator")

st.write(
    "Use Gemini AI to automatically generate "
    "professional technical descriptions for your parts."
)

if parts:

    ai_part_id = st.selectbox(
        "Select a part for AI description generation",
        options=[part["id"] for part in parts],
        format_func=lambda part_id: next(
            (
                f"{part['part_number']} - {part['name']}"
                for part in parts
                if part["id"] == part_id
            ),
            str(part_id)
        ),
        key="ai_part_selection"
    )

    selected_ai_part = next(
        part for part in parts
        if part["id"] == ai_part_id
    )

    st.write("**Current Description:**")

    st.info(
        selected_ai_part["description"]
        or "No description available."
    )

    if st.button(
        "✨ Generate AI Description",
        use_container_width=True
    ):

        with st.spinner(
            "Gemini is generating the technical description..."
        ):

            try:
                result = generate_part_ai_description(ai_part_id)

                st.success(
                    "AI description generated and saved successfully!"
                )

                st.subheader("Generated Description")

                st.write(result["description"])

                st.rerun()

            except Exception as error:
                st.error(
                    f"AI description generation failed: {error}"
                )

else:
    st.info("Create a part before generating an AI description.")

# -------------------------
# DELETE PART
# -------------------------

st.subheader("🗑️ Delete Part")

if parts:

    delete_id = st.selectbox(
        "Select a part to delete",
        options=[part["id"] for part in parts],
        format_func=lambda part_id: next(
            (
                f"{part['part_number']} - {part['name']}"
                for part in parts
                if part["id"] == part_id
            ),
            str(part_id)
        ),
        key="delete_part_selection"
    )

    confirm_delete = st.checkbox(
        "I confirm that I want to delete this part."
    )

    if st.button(
        "Delete Selected Part",
        type="primary",
        disabled=not confirm_delete
    ):

        try:
            result = delete_part(delete_id)

            st.success(result["message"])
            st.rerun()

        except Exception as error:
            st.error(f"Could not delete part: {error}")

else:
    st.info("No parts available to delete.")


st.divider()

st.caption("MiniPLM | Part Management")