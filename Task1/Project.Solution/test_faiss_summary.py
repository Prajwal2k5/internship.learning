
from src.vector_store import load_vector_store

def main():
    print("Loading FAISS index...")

    vector_store = load_vector_store()

    # Inspect all documents stored in FAISS
    stored_documents = list(
        vector_store.docstore._dict.values()
    )

    summaries = [
        doc for doc in stored_documents
        if doc.metadata.get("document_type") == "generated_summary"
    ]

    print(f"\nTotal stored documents: {len(stored_documents)}")
    print(f"Generated summaries found: {len(summaries)}")

    if not summaries:
        print("FAIL: No generated summary found in FAISS.")
        return

    print("\nSummary metadata:")
    for key, value in summaries[0].metadata.items():
        print(f"{key}: {value}")

    # Test similarity search
    query = "What are the main marketing strategies and key takeaways?"
    print(f"\nTesting retrieval for: {query}")

    results = vector_store.similarity_search(query, k=4)

    if not results:
        print("FAIL: No documents retrieved.")
        return

    print(f"\nPASS: Retrieved {len(results)} relevant document(s).")

    for i, doc in enumerate(results, start=1):
        print(f"\n--- Result {i} ---")
        print("Metadata:", doc.metadata)
        print("Content preview:", doc.page_content[:300])

    print("\nFAISS summary storage and retrieval test completed.")


if __name__ == "__main__":
    main()
