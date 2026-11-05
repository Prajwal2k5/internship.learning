
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pdf_text(file_path: str) -> dict:
    """
    Extract text from a PDF document.

    Args:
        file_path: Location of the PDF file.

    Returns:
        Dictionary containing extracted text and page count.
    """

    pdf_path = Path(file_path)

    # Check whether file exists
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {pdf_path}"
        )

    if not pdf_path.is_file():
        raise ValueError("Provided path is not a file.")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    try:
        reader = PdfReader(str(pdf_path))

        # Check encrypted PDF
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError(
                    "PDF is password protected."
                )

            if reader.is_encrypted:
                raise ValueError(
                    "PDF is password protected."
                )

        extracted_pages = []

        # Extract text page by page
        for page_number, page in enumerate(reader.pages, start=1):

            page_text = page.extract_text() or ""

            extracted_pages.append(
                f"--- Page {page_number} ---\n{page_text}"
            )

        full_text = "\n\n".join(extracted_pages).strip()

        if not full_text:
            raise ValueError(
                "No readable text found in PDF. "
                "The document may contain scanned images."
            )

        return {
            "filename": pdf_path.name,
            "total_pages": len(reader.pages),
            "extracted_text": full_text,
            "character_count": len(full_text)
        }

    except PdfReadError as error:
        raise ValueError(
            f"Unable to read PDF: {error}"
        ) from error
