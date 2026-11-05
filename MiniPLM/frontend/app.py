import streamlit as st
import pandas as pd

from api import (
    check_backend,
    get_parts,
    get_documents
)


# -------------------------
# PAGE CONFIGURATION
# -------------------------

st.set_page_config(
    page_title="MiniPLM",
    page_icon="⚙️",
    layout="wide"
)


# -------------------------
# APPLICATION HEADER
# -------------------------

st.title("⚙️ MiniPLM")
st.subheader("AI-Powered Part and Document Management System")

st.write(
    "Manage engineering parts, technical documents, "
    "lifecycle statuses and AI-powered document insights."
)

st.divider()


# -------------------------
# BACKEND CONNECTION
# -------------------------

try:
    health = check_backend()

    if health.get("status") == "healthy":
        st.success("Backend connected successfully")
    else:
        st.warning("Backend is responding, but its health status is unexpected.")

except Exception as error:
    st.error(f"Cannot connect to FastAPI backend: {error}")
    st.info(
        "Start the backend in another terminal using: "
        "uvicorn backend.main:app --reload"
    )
    st.stop()


# -------------------------
# FETCH DATABASE DATA
# -------------------------

try:
    parts = get_parts()
    documents = get_documents()

except Exception as error:
    st.error(f"Unable to load dashboard data: {error}")
    st.stop()


# -------------------------
# DASHBOARD METRICS
# -------------------------

st.subheader("Dashboard Overview")

total_parts = len(parts)
total_documents = len(documents)

released_parts = sum(
    1 for part in parts
    if part["lifecycle_status"] == "Released"
)

draft_parts = sum(
    1 for part in parts
    if part["lifecycle_status"] == "Draft"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Parts", total_parts)
col2.metric("Total Documents", total_documents)
col3.metric("Released Parts", released_parts)
col4.metric("Draft Parts", draft_parts)


st.divider()


# -------------------------
# RECENT PARTS TABLE
# -------------------------

st.subheader("Part Inventory")

if parts:
    parts_table = [
        {
            "ID": part["id"],
            "Part Number": part["part_number"],
            "Name": part["name"],
            "Manufacturer": part["manufacturer"],
            "Category": part["category"],
            "Status": part["lifecycle_status"]
        }
        for part in parts
    ]

    st.dataframe(
        pd.DataFrame(parts_table),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No parts found. Add your first part using Part Management.")


# -------------------------
# DOCUMENT TABLE
# -------------------------

st.subheader("Uploaded Documents")

if documents:
    document_table = [
        {
            "Document ID": document["id"],
            "Filename": document["filename"],
            "Content Type": document["content_type"]
        }
        for document in documents
    ]

    st.dataframe(
        pd.DataFrame(document_table),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No documents have been uploaded yet.")


st.divider()

st.caption("MiniPLM | AI-Powered Part and Document Management System")