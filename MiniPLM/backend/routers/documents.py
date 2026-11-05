
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.database import get_db
from backend.models import Document, Part, PartDocument
from backend.schemas import DocumentResponse

from backend.services.pdf_service import extract_pdf_text

from backend.services.ai_service import (
    summarize_document,
    extract_technical_information
)

from backend.services.rag_service import (
    index_pdf_document,
    answer_document_question
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

logger = logging.getLogger(__name__)


# Request model for document questions
class DocumentQuestionRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000
    )


# Upload directory
BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# 1. UPLOAD PDF AND LINK TO PART
@router.post(
    "/upload/{part_id}",
    response_model=DocumentResponse,
    status_code=201
)
async def upload_document(
    part_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    part = db.query(Part).filter(
        Part.id == part_id
    ).first()

    if not part:
        raise HTTPException(
            status_code=404,
            detail="Part not found."
        )

    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds 10 MB."
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file."
        )

    stored_filename = f"{uuid4().hex}.pdf"
    file_path = UPLOAD_DIR / stored_filename

    try:
        file_path.write_bytes(content)

        new_document = Document(
            filename=Path(file.filename).name,
            file_path=str(file_path),
            content_type="application/pdf"
        )

        db.add(new_document)
        db.flush()

        document_link = PartDocument(
            part_id=part_id,
            document_id=new_document.id
        )

        db.add(document_link)
        db.commit()
        db.refresh(new_document)

        return new_document

    except IntegrityError:
        db.rollback()
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=409,
            detail="Database conflict while uploading document."
        )

    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()


# 2. GET ALL DOCUMENTS
@router.get("/", response_model=list[DocumentResponse])
def get_all_documents(
    db: Session = Depends(get_db)
):
    return db.query(Document).all()


# 3. AI DOCUMENT SUMMARY
@router.post("/{document_id}/summarize")
def summarize_pdf_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        pdf_result = extract_pdf_text(document.file_path)

        summary = summarize_document(
            pdf_result["extracted_text"]
        )

        return {
            "document_id": document.id,
            "filename": document.filename,
            "total_pages": pdf_result["total_pages"],
            "summary": summary
        }

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception:
        logger.exception("AI document summarization failed.")

        raise HTTPException(
            status_code=502,
            detail="AI summarization failed. Check the server logs."
        )


# 4. AI TECHNICAL INFORMATION EXTRACTION
@router.post("/{document_id}/extract-info")
def extract_pdf_information(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        pdf_result = extract_pdf_text(document.file_path)

        extracted_information = extract_technical_information(
            pdf_result["extracted_text"]
        )

        return {
            "document_id": document.id,
            "filename": document.filename,
            "total_pages": pdf_result["total_pages"],
            "extracted_information": extracted_information
        }

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception:
        logger.exception("AI technical information extraction failed.")

        raise HTTPException(
            status_code=502,
            detail="AI information extraction failed. Check the server logs."
        )


# 5. INDEX PDF FOR RAG QUESTION ANSWERING
@router.post("/{document_id}/index")
def index_document_for_rag(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        result = index_pdf_document(
            document_id=document.id,
            file_path=document.file_path
        )

        return result

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception:
        logger.exception("RAG document indexing failed.")

        raise HTTPException(
            status_code=502,
            detail="Document indexing failed. Check the server logs."
        )


# 6. ASK QUESTIONS ABOUT AN INDEXED PDF
@router.post("/{document_id}/ask")
def ask_document_question(
    document_id: int,
    request: DocumentQuestionRequest,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        result = answer_document_question(
            document_id=document.id,
            question=request.question
        )

        # Replace the internal UUID filename with the original filename
        result["filename"] = document.filename

        return result

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    except (ValueError, OSError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception:
        logger.exception("Document question answering failed.")

        raise HTTPException(
            status_code=502,
            detail="Question answering failed. Check the server logs."
        )


# 7. GET DOCUMENT BY ID
@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return document


# 8. DOWNLOAD PDF
@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    file_path = Path(document.file_path)

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Physical document file not found."
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=Path(document.filename).name
    )


# 9. GET DOCUMENTS LINKED TO A PART
@router.get(
    "/part/{part_id}",
    response_model=list[DocumentResponse]
)
def get_part_documents(
    part_id: int,
    db: Session = Depends(get_db)
):
    part = db.query(Part).filter(
        Part.id == part_id
    ).first()

    if not part:
        raise HTTPException(
            status_code=404,
            detail="Part not found."
        )

    documents = (
        db.query(Document)
        .join(PartDocument)
        .filter(PartDocument.part_id == part_id)
        .all()
    )

    return documents


# 10. DELETE DOCUMENT
@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    file_path = Path(document.file_path)

    try:
        db.delete(document)
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Could not delete document."
        )

    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Document record deleted, but physical file cleanup failed."
        )

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id
    }
