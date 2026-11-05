
from backend.services.pdf_service import extract_pdf_text


PDF_PATH = input("Enter PDF file path: ").strip().strip('"')

try:
    result = extract_pdf_text(PDF_PATH)

    print("\n========== PDF EXTRACTION SUCCESSFUL ==========")

    print("Filename:", result["filename"])
    print("Total Pages:", result["total_pages"])
    print("Character Count:", result["character_count"])

    print("\n========== EXTRACTED TEXT ==========\n")

    print(result["extracted_text"][:3000])

    print("\n============================================")

except Exception as error:
    print("\nPDF EXTRACTION FAILED")
    print("Error:", error)
