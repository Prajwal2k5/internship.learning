
from src.loader import load_pdf, split_documents
from src.summarizer import summarize_documents, save_summary

pdf_path = "data/Content Marketing Strategies.pdf"

documents = load_pdf(pdf_path)
chunks = split_documents(documents)

print("Generating summary...")
summary = summarize_documents(chunks)

metadata = save_summary(
    summary,
    title="Content Marketing Strategies",
)

print("\nSUMMARY\n")
print(summary)

print("\nMETADATA\n")
print(metadata)

print("\nSaved to summary.txt")
