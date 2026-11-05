
import streamlit as st

from api import (
    get_parts,
    get_documents,
    get_part_documents,
    upload_document,
    summarize_document,
    extract_document_info,
    index_document,
    ask_document,
    delete_document,
    get_document_download_url
)


# -------------------------
# PAGE CONFIGURATION
# -------------------------

st.set_page_config(
    page_title="Document Management | MiniPLM",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Document Management")
st.write(
    "Upload, manage and analyze engineering PDF documents "
    "using Gemini AI and RAG."
)

st.divider()


# -------------------------
# FETCH PARTS AND DOCUMENTS
# -------------------------

try:
    parts = get_parts()
    documents = get_documents()

except Exception as error:
    st.error(f"Unable to load data: {error}")
    st.stop()


if not parts:
    st.warning("Create a part before uploading a document.")
    st.stop()


# -------------------------
# UPLOAD PDF
# -------------------------

st.subheader("📤 Upload PDF Document")

part_options = {
    part["id"]: (
        f'{part["part_number"]} - {part["name"]}'
    )
    for part in parts
}

with st.form("upload_document_form", clear_on_submit=True):

    selected_part_id = st.selectbox(
        "Select the part associated with this document",
        options=list(part_options.keys()),
        format_func=lambda part_id: part_options[part_id]
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Only PDF files up to 10 MB are accepted."
    )

    upload_submitted = st.form_submit_button(
        "Upload Document",
        use_container_width=True
    )

    if upload_submitted:

        if uploaded_file is None:
            st.warning("Please select a PDF file.")

        elif uploaded_file.size > 10 * 1024 * 1024:
            st.error("File size must not exceed 10 MB.")

        else:
            try:
                result = upload_document(
                    selected_part_id,
                    uploaded_file
                )

                st.success(
                    f'Document "{result["filename"]}" uploaded successfully! '
                    f'Document ID: {result["id"]}'
                )

                st.rerun()

            except Exception as error:
                st.error(f"Upload failed: {error}")


st.divider()


# -------------------------
# VIEW UPLOADED DOCUMENTS
# -------------------------

st.subheader("📚 Uploaded Documents")

if documents:

    document_table = []

    for document in documents:
        document_table.append({
            "Document ID": document["id"],
            "Filename": document["filename"],
            "Content Type": document["content_type"]
        })

    st.dataframe(
        document_table,
        use_container_width=True,
        hide_index=True
    )

    st.write(f"**Total documents:** {len(documents)}")

else:
    st.info("No documents uploaded yet.")


st.divider()


# -------------------------
# FILTER DOCUMENTS BY PART
# -------------------------

st.subheader("🔗 Documents Associated with a Part")

filter_part_id = st.selectbox(
    "Select a part to view its documents",
    options=list(part_options.keys()),
    format_func=lambda part_id: part_options[part_id],
    key="filter_part"
)

if st.button("View Part Documents"):

    try:
        linked_documents = get_part_documents(filter_part_id)

        if linked_documents:
            st.dataframe(
                [
                    {
                        "Document ID": doc["id"],
                        "Filename": doc["filename"],
                        "Content Type": doc["content_type"]
                    }
                    for doc in linked_documents
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No documents are associated with this part.")

    except Exception as error:
        st.error(f"Unable to fetch linked documents: {error}")


st.divider()


# -------------------------
# SELECT A DOCUMENT
# -------------------------

st.subheader("🤖 AI Document Assistant")

if not documents:
    st.info("Upload a document to use the AI features.")

else:

    document_options = {
        doc["id"]: doc["filename"]
        for doc in documents
    }

    selected_document_id = st.selectbox(
        "Select a document",
        options=list(document_options.keys()),
        format_func=lambda doc_id: (
            f'ID {doc_id} - {document_options[doc_id]}'
        ),
        key="selected_document"
    )

    selected_filename = document_options[selected_document_id]

    st.caption(f"Selected document: {selected_filename}")


    # -------------------------
    # DOWNLOAD DOCUMENT
    # -------------------------

    st.subheader("⬇️ Download PDF")

    st.link_button(
        "Download Selected PDF",
        get_document_download_url(selected_document_id)
    )


    # -------------------------
    # AI SUMMARY
    # -------------------------

    st.subheader("📝 Generate Document Summary")

    if st.button("Generate AI Summary"):

        with st.spinner("Gemini AI is summarizing the document..."):

            try:
                result = summarize_document(selected_document_id)

                st.session_state[
                    f"summary_{selected_document_id}"
                ] = result

            except Exception as error:
                st.error(f"Summary generation failed: {error}")

    summary_key = f"summary_{selected_document_id}"

    if summary_key in st.session_state:
        summary_result = st.session_state[summary_key]

        st.markdown("**AI Generated Summary**")
        st.write(summary_result["summary"])

        st.caption(
            f'Pages processed: {summary_result["total_pages"]}'
        )


    # -------------------------
    # EXTRACT TECHNICAL INFORMATION
    # -------------------------

    st.divider()

    st.subheader("🔍 Extract Technical Information")

    if st.button("Extract Technical Information"):

        with st.spinner("Gemini AI is extracting technical details..."):

            try:
                result = extract_document_info(selected_document_id)

                st.session_state[
                    f"extraction_{selected_document_id}"
                ] = result

            except Exception as error:
                st.error(f"Information extraction failed: {error}")

    extraction_key = f"extraction_{selected_document_id}"

    if extraction_key in st.session_state:
        extraction_result = st.session_state[extraction_key]

        st.markdown("**Extracted Information**")
        st.write(extraction_result["extracted_information"])

        st.caption(
            f'Pages processed: {extraction_result["total_pages"]}'
        )


    # -------------------------
    # RAG DOCUMENT INDEXING
    # -------------------------

    st.divider()

    st.subheader("🧠 Index Document for RAG")

    st.write(
        "Index the PDF to enable question answering based on its content."
    )

    if st.button("Index Document"):

        with st.spinner(
            "Extracting text, creating embeddings and indexing..."
        ):

            try:
                result = index_document(selected_document_id)

                st.session_state[
                    f"index_{selected_document_id}"
                ] = result

                st.success(result.get(
                    "message",
                    "Document indexed successfully."
                ))

            except Exception as error:
                st.error(f"Document indexing failed: {error}")

    index_key = f"index_{selected_document_id}"

    if index_key in st.session_state:
        index_result = st.session_state[index_key]

        st.write("**Indexing Details**")

        st.json(index_result)


    # -------------------------
    # RAG QUESTION ANSWERING
    # -------------------------

    st.divider()

    st.subheader("💬 Ask Questions About the PDF")

    with st.form("document_question_form"):

        question = st.text_input(
            "Enter your question",
            placeholder="Example: What is the main purpose of this document?"
        )

        ask_submitted = st.form_submit_button(
            "Ask AI",
            use_container_width=True
        )

        if ask_submitted:

            if not question.strip():
                st.warning("Please enter a question.")

            else:
                with st.spinner(
                    "Searching document content and generating an answer..."
                ):

                    try:
                        result = ask_document(
                            selected_document_id,
                            question.strip()
                        )

                        st.session_state[
                            f"answer_{selected_document_id}"
                        ] = result

                    except Exception as error:
                        st.error(f"Question answering failed: {error}")

    answer_key = f"answer_{selected_document_id}"

    if answer_key in st.session_state:

        answer_result = st.session_state[answer_key]

        st.markdown("**AI Answer**")
        st.write(answer_result["answer"])

        if answer_result.get("sources"):
            st.markdown("**Reference Pages**")

            for source in answer_result["sources"]:
                st.write(
                    f'Page {source["page"]} '
                    f'| Similarity: {source["similarity_score"]}'
                )


    # -------------------------
    # DELETE DOCUMENT
    # -------------------------

    st.divider()

    st.subheader("🗑️ Delete Document")

    confirm_delete = st.checkbox(
        "I confirm that I want to permanently delete this document.",
        key=f"confirm_delete_{selected_document_id}"
    )

    if st.button(
        "Delete Selected Document",
        disabled=not confirm_delete
    ):

        try:
            result = delete_document(selected_document_id)

            st.success(result["message"])
            st.rerun()

        except Exception as error:
            st.error(f"Document deletion failed: {error}")


st.divider()

st.caption("MiniPLM | Document Management")
