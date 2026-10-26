
from src.loader import load_pdf, split_documents

pdf_path = "data/Content Marketing Strategies.pdf"

documents = load_pdf(pdf_path)
chunks = split_documents(documents)

print("Pages loaded:", len(documents))
print("Chunks created:", len(chunks))
print("\nFirst chunk preview:\n")
print(chunks[0].page_content[:500])
print("\nMetadata:", chunks[0].metadata)
