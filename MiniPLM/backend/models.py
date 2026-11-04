
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class Part(Base):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    manufacturer = Column(String(150), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    lifecycle_status = Column(String(30), default="Draft", nullable=False)

    documents = relationship(
        "PartDocument",
        back_populates="part",
        cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(100), default="application/pdf")
    parts = relationship(
        "PartDocument",
        back_populates="document",
        cascade="all, delete-orphan"
    )


class PartDocument(Base):
    __tablename__ = "part_documents"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    part = relationship("Part", back_populates="documents")
    document = relationship("Document", back_populates="parts")
