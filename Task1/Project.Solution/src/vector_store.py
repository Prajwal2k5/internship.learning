
from pathlib import Path
from datetime import datetime, timezone

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

from config import OLLAMA_EMBEDDING_MODEL, VECTOR_STORE_DIR


# --------------------------------------------------
# 1. Initialize the embedding model
# --------------------------------------------------

def get_embeddings():
    """
    Return the Ollama embedding model used to convert
    transcript chunks and summaries into vectors.
    """
    return OllamaEmbeddings(
        model=OLLAMA_EMBEDDING_MODEL
    )


# --------------------------------------------------
# 2. Create and save the FAISS vector store
# --------------------------------------------------

def create_vector_store(
    chunks,
    persist_directory=VECTOR_STORE_DIR,
):
    """
    Create a FAISS index from document chunks and save it locally.
    """
    if not chunks:
        raise ValueError(
            "Cannot create a vector store without document chunks."
        )

    embeddings = get_embeddings()

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings,
    )

    vector_store.save_local(
        str(persist_directory)
    )

    print(
        f"FAISS vector store created and saved to: "
        f"{persist_directory}"
    )

    print(
        f"Number of indexed transcript chunks: {len(chunks)}"
    )

    return vector_store


# --------------------------------------------------
# 3. Load an existing FAISS vector store
# --------------------------------------------------

def load_vector_store(
    persist_directory=VECTOR_STORE_DIR,
):
    """
    Load a previously saved FAISS index from local storage.
    """
    index_path = Path(persist_directory)

    if not index_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found at '{index_path}'. "
            "Process the PDFs to create the index first."
        )

    index_file = index_path / "index.faiss"
    metadata_file = index_path / "index.pkl"

    if not index_file.exists() or not metadata_file.exists():
        raise FileNotFoundError(
            f"The FAISS index files are missing from '{index_path}'. "
            "Please process the PDFs again to rebuild the index."
        )

    embeddings = get_embeddings()

    vector_store = FAISS.load_local(
        str(index_path),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    return vector_store


# --------------------------------------------------
# 4. Add the generated summary to FAISS
# --------------------------------------------------

def add_summary_to_vector_store(
    summary,
    title,
    persist_directory=VECTOR_STORE_DIR,
):
    """
    Add the generated summary to the existing FAISS index.

    Metadata includes:
    - document_type
    - webinar_title
    - timestamp
    - source
    """

    if not summary or not summary.strip():
        raise ValueError(
            "Cannot store an empty summary."
        )

    if not title or not title.strip():
        raise ValueError(
            "Please provide a title for the summary."
        )

    # Load the existing transcript index
    vector_store = load_vector_store(
        persist_directory=persist_directory
    )

    # Create a summary document with metadata
    summary_document = Document(
        page_content=summary,
        metadata={
            "document_type": "generated_summary",
            "webinar_title": title,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "summary.txt",
        },
    )

    # Add the summary to the existing FAISS index
    vector_store.add_documents(
        documents=[summary_document]
    )

    # Save the updated index, including the summary
    vector_store.save_local(
        str(persist_directory)
    )

    print("Generated summary added to FAISS successfully.")
    print(f"Webinar title: {title}")
    print("Metadata: document_type, webinar_title, timestamp, source")

    return vector_store


# --------------------------------------------------
# 5. Search the FAISS index
# --------------------------------------------------

def search_documents(
    query,
    k=4,
    persist_directory=VECTOR_STORE_DIR,
):
    """
    Retrieve the most relevant transcript chunks or summaries.
    """
    if not query or not query.strip():
        raise ValueError(
            "Please provide a search query."
        )

    vector_store = load_vector_store(
        persist_directory=persist_directory
    )

    results = vector_store.similarity_search(
        query,
        k=k,
    )

    return results
