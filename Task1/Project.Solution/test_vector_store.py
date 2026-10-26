
from src.loader import load_pdf, split_documents
from src.vector_store import create_vector_store

pdf_path = "data/Content Marketing Strategies.pdf"

documents = load_pdf(pdf_path)
chunks = split_documents(documents)

print("Creating FAISS vector store...")
vector_store = create_vector_store(chunks)

print("FAISS vector store created successfully!")

results = vector_store.similarity_search(
    "What are the key content marketing strategies?",
    k=3,
)

print("\nRelevant results:\n")

for i, result in enumerate(results, start=1):
    print(f"Result {i}:")
    print(result.page_content[:300])
    print("Metadata:", result.metadata)
    print("-" * 40)