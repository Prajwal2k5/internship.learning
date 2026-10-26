
from pathlib import Path
from datetime import datetime

import streamlit as st

from config import VECTOR_STORE_DIR, SUMMARY_FILE
from src.loader import load_pdf, split_documents
from src.vector_store import (
    create_vector_store,
    add_summary_to_vector_store,
    load_vector_store,
)
from src.summarizer import summarize_documents, save_summary
from src.qa_engine import answer_question


# --------------------------------------------------
# 1. Project paths and Streamlit configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VECTOR_DIR = BASE_DIR / VECTOR_STORE_DIR
SUMMARY_PATH = BASE_DIR / SUMMARY_FILE

st.set_page_config(
    page_title="Webinar Transcript Summarizer & QA",
    page_icon="ðŸ“š",
    layout="wide",
)

st.title("ðŸ“š Automated Webinar Transcript Summarization & QA")
st.write(
    "Upload marketing webinar transcripts, generate summaries, "
    "and ask questions based on the indexed documents."
)


# --------------------------------------------------
# 2. Session state initialization
# --------------------------------------------------

if "summary" not in st.session_state:
    st.session_state.summary = ""

if "processed" not in st.session_state:
    st.session_state.processed = False

if "last_processed" not in st.session_state:
    st.session_state.last_processed = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------
# 3. Sidebar: PDF processing
# --------------------------------------------------

st.sidebar.header("ðŸ“‚ Webinar Documents")

st.sidebar.write("Place your webinar PDF files inside the `data` folder.")

if DATA_DIR.exists():
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))
else:
    pdf_files = []

if pdf_files:
    st.sidebar.success(f"{len(pdf_files)} PDF file(s) found.")

    for pdf_file in pdf_files:
        st.sidebar.write(f"ðŸ“„ {pdf_file.name}")
else:
    st.sidebar.warning(
        "No PDFs found. Create a 'data' folder and add your PDF files."
    )

process_button = st.sidebar.button(
    "Process PDFs",
    type="primary",
    disabled=not pdf_files,
    use_container_width=True,
)


# --------------------------------------------------
# 4. Process PDFs, create FAISS index and summarize
# --------------------------------------------------

if process_button:
    try:
        all_documents = []
        all_chunks = []

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Load each PDF
        for index, pdf_file in enumerate(pdf_files, start=1):
            status_text.info(
                f"Loading PDF {index}/{len(pdf_files)}: {pdf_file.name}"
            )

            documents = load_pdf(str(pdf_file))
            all_documents.extend(documents)

            progress_bar.progress(
                int((index / len(pdf_files)) * 30)
            )

        if not all_documents:
            st.error("No readable text was extracted from the PDFs.")
            st.stop()

        # Split documents into chunks
        status_text.info("Splitting documents into text chunks...")

        all_chunks = split_documents(all_documents)

        if not all_chunks:
            st.error("No text chunks were created.")
            st.stop()

        st.write(f"**PDF files loaded:** {len(pdf_files)}")
        st.write(f"**Pages loaded:** {len(all_documents)}")
        st.write(f"**Text chunks created:** {len(all_chunks)}")

        progress_bar.progress(40)

        # Create FAISS index from transcript chunks
        status_text.info("Creating FAISS vector store...")

        create_vector_store(
            all_chunks,
            persist_directory=str(VECTOR_DIR),
        )

        progress_bar.progress(55)

        # Generate a summary of the transcript chunks
        status_text.info(
            "Generating the marketing summary. This may take a while..."
        )

        summary = summarize_documents(all_chunks)

        if not summary or not summary.strip():
            st.error("The summarizer returned an empty summary.")
            st.stop()

        progress_bar.progress(85)

        # Save summary to a text file
        save_summary(
            summary=summary,
            title="Marketing Webinar Collection",
            output_file=str(SUMMARY_PATH),
        )

        # IMPORTANT: Save summary to FAISS with metadata
        status_text.info("Saving the generated summary into FAISS...")

        add_summary_to_vector_store(
            summary=summary,
            title="Marketing Webinar Collection",
            persist_directory=str(VECTOR_DIR),
        )

        # Update session state
        st.session_state.summary = summary
        st.session_state.processed = True
        st.session_state.last_processed = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Start a fresh chat after reprocessing the documents
        st.session_state.messages = []

        progress_bar.progress(100)
        status_text.success("All PDFs processed successfully!")

        st.success(
            "Processing complete! The summary was saved to summary.txt "
            "and added to the FAISS vector store."
        )

    except Exception as error:
        st.error(f"An error occurred during processing: {error}")
        st.exception(error)


# --------------------------------------------------
# 5. Display generated summary
# --------------------------------------------------

st.header("ðŸ“ Webinar Summary")

if st.session_state.summary:
    st.markdown(st.session_state.summary)

    st.download_button(
        label="Download Summary",
        data=st.session_state.summary,
        file_name="webinar_summary.txt",
        mime="text/plain",
    )

elif SUMMARY_PATH.exists():
    saved_text = SUMMARY_PATH.read_text(encoding="utf-8")
    st.info(
        "A previously saved summary was found. "
        "Process the PDFs to load it into this session."
    )
    st.text_area(
        "Saved Summary",
        value=saved_text,
        height=300,
        disabled=True,
    )

else:
    st.info("Click **Process PDFs** in the sidebar to generate a summary.")


# --------------------------------------------------
# 6. Display processing and storage information
# --------------------------------------------------

st.sidebar.divider()
st.sidebar.header("ðŸ“Š Processing Information")

st.sidebar.write(
    f"**FAISS index folder:** `{VECTOR_DIR.name}`"
)

st.sidebar.write(
    f"**Summary file:** `{SUMMARY_PATH.name}`"
)

if st.session_state.last_processed:
    st.sidebar.write(
        f"**Last processed:** {st.session_state.last_processed}"
    )

if VECTOR_DIR.exists():
    st.sidebar.success("FAISS index folder exists.")
else:
    st.sidebar.info("FAISS index has not been created yet.")

if SUMMARY_PATH.exists():
    st.sidebar.success("Summary file exists.")
else:
    st.sidebar.info("Summary file has not been created yet.")


# --------------------------------------------------
# 7. Question-answering interface
# --------------------------------------------------

st.divider()
st.header("ðŸ’¬ Ask Questions About the Webinars")

st.write(
    "Ask questions about the uploaded webinar transcripts. "
    "Answers are generated using relevant chunks retrieved from FAISS."
)

if not VECTOR_DIR.exists():
    st.warning("Process the PDFs before asking questions.")

# Display existing conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("sources"):
            with st.expander("View retrieved sources"):
                for source in message["sources"]:
                    st.write(
                        f"- {source['source']} "
                        f"(Page {source['page']})"
                    )

# Chat input
question = st.chat_input(
    "Ask a question about the webinar transcripts...",
    disabled=not VECTOR_DIR.exists(),
)

if question:
    # Display and save the user's question
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    # Retrieve relevant chunks and generate an answer
    with st.chat_message("assistant"):
        with st.spinner("Searching transcripts and generating an answer..."):
            try:
                result = answer_question(question)

                # Handle the dictionary returned by qa_engine.py
                if isinstance(result, dict):
                    answer = result.get(
                        "answer",
                        "No answer was returned.",
                    )
                    sources = result.get("sources", [])
                else:
                    answer = str(result)
                    sources = []

                st.markdown(answer)

                if sources:
                    with st.expander("View retrieved sources"):
                        for source in sources:
                            st.write(
                                f"- {source['source']} "
                                f"(Page {source['page']})"
                            )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

            except Exception as error:
                error_message = (
                    f"Unable to answer the question: {error}"
                )
                st.error(error_message)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )
# --------------------------------------------------
# 8. FAISS Metadata Inspector
# --------------------------------------------------

st.divider()
st.header("ðŸ” FAISS Metadata Inspector")

st.write(
    "Inspect the documents stored in FAISS, including transcript "
    "chunks and the generated summary with its metadata."
)

if st.button("Inspect FAISS Index", use_container_width=True):
    try:
        vector_store = load_vector_store(
            persist_directory=str(VECTOR_DIR)
        )

        # Retrieve the stored documents from the FAISS docstore
        stored_documents = list(
            vector_store.docstore._dict.values()
        )

        if not stored_documents:
            st.warning("The FAISS index contains no documents.")
        else:
            summary_documents = [
                doc for doc in stored_documents
                if doc.metadata.get("document_type")
                == "generated_summary"
            ]

            transcript_documents = [
                doc for doc in stored_documents
                if doc.metadata.get("document_type")
                != "generated_summary"
            ]

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Total Stored Documents",
                len(stored_documents),
            )

            col2.metric(
                "Transcript Chunks",
                len(transcript_documents),
            )

            col3.metric(
                "Generated Summaries",
                len(summary_documents),
            )

            st.subheader("Stored Document Metadata")

            for index, document in enumerate(
                stored_documents,
                start=1,
            ):
                metadata = document.metadata

                with st.expander(
                    f"Document {index}: "
                    f"{metadata.get('source', 'Unknown source')}"
                ):
                    st.json(metadata)

                    st.caption("Stored text preview")

                    st.write(
                        document.page_content[:500]
                        + (
                            "..."
                            if len(document.page_content) > 500
                            else ""
                        )
                    )

            if summary_documents:
                st.success(
                    "Generated summary found in the FAISS index."
                )
            else:
                st.warning(
                    "No generated summary was found. "
                    "Click Process PDFs to generate and store one."
                )

    except Exception as error:
        st.error(
            f"Unable to inspect the FAISS index: {error}"
        )
