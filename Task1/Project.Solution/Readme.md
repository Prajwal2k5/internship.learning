# Automated Webinar Transcript Summarization & QA System

## Overview

The Automated Webinar Transcript Summarization & QA System is a Python-based application that processes webinar transcript PDFs, generates concise summaries using a local Large Language Model (LLM), and answers user questions using Retrieval-Augmented Generation (RAG).

The application uses LangChain for LLM orchestration, Ollama for local model inference, FAISS for vector storage and similarity search, and Streamlit for the user interface.

## Features

- Load and process multiple webinar transcript PDFs.
- Extract text and split documents into manageable chunks.
- Generate concise summaries highlighting key takeaways, marketing strategies, frameworks, and actionable recommendations.
- Store transcript chunks and generated summaries in a FAISS vector store.
- Attach metadata to generated summaries, including document type, webinar title, timestamp, and source.
- Answer questions using relevant retrieved document context.
- Display source document names and page numbers for retrieved content.
- Inspect stored FAISS documents and their metadata through the Streamlit interface.
- Save the generated summary to a text file.

## Technology Stack

- **Language:** Python
- **LLM Framework:** LangChain
- **Local LLM Runtime:** Ollama
- **Language Model:** Llama 3
- **Embedding Model:** `nomic-embed-text`
- **Vector Database:** FAISS
- **PDF Processing:** PyPDFLoader
- **Text Splitting:** RecursiveCharacterTextSplitter
- **User Interface:** Streamlit

## Project Structure

```text
Project.Solution/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── data/
│   └── webinar transcript PDFs
├── faiss_index/
│   ├── index.faiss
│   └── index.pkl
├── summary.txt
├── src/
│   ├── __init__.py
│   ├── loader.py
│   ├── vector_store.py
│   ├── summarizer.py
│   └── qa_engine.py
└── test_faiss_summary.py
```

The FAISS index and generated summary are created locally when the application processes the documents.

## Prerequisites

- Python 3.10 or a compatible Python version supported by the installed dependencies.
- Ollama installed and running.
- The required Ollama models downloaded locally.
- Git installed.
- VS Code or another Python development environment.

## Installation and Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd Task1/Project.Solution
```

Replace `<repository-url>` with the GitHub repository URL.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Download the required Ollama models

```powershell
ollama pull llama3
ollama pull nomic-embed-text
```

Ensure the Ollama service is running before starting the application.

### 5. Add input PDFs

Create a `data` directory in the project root if it does not already exist. Place your webinar transcript PDFs inside it.

### 6. Run the application

```powershell
streamlit run app.py
```

Open the local URL displayed in the terminal, usually `http://localhost:8501`.

## How to Use

1. Start the Streamlit application.
2. Confirm that the webinar PDF files appear in the sidebar.
3. Click **Process PDFs**.
4. Wait for document loading, chunking, embedding, and summary generation to finish.
5. Read or download the generated summary.
6. Use the question-answering interface to ask questions about the indexed transcripts.
7. Review the retrieved source documents and page numbers.
8. Open the FAISS Metadata Inspector and click **Inspect FAISS Index** to review stored records and metadata.

## Processing Workflow

1. **Document Loading:** PyPDFLoader extracts text and page metadata from PDF files.
2. **Text Splitting:** RecursiveCharacterTextSplitter creates chunks using configurable chunk size and overlap.
3. **Embedding Generation:** Ollama converts text chunks into numerical vector representations.
4. **Vector Storage:** FAISS indexes transcript chunks for similarity-based retrieval.
5. **Summarization:** LangChain prompts and the local Llama 3 model generate and combine partial summaries.
6. **Summary Persistence:** The summary is saved to `summary.txt` and added to FAISS with metadata.
7. **Question Answering:** Relevant documents are retrieved from FAISS and passed as context to the LLM.
8. **Metadata Inspection:** Streamlit displays document counts, metadata, and stored text previews.

## Configuration

Application settings are maintained in `config.py`, including:

- LLM model name
- Embedding model name
- Chunk size
- Chunk overlap
- FAISS index directory
- Summary output file
- LLM temperature

Update these values as needed for your local environment.

## Testing

Run the summary storage and retrieval test:

```powershell
python test_faiss_summary.py
```

The test checks whether generated summary records exist in FAISS, prints their metadata, and performs a similarity search.

## Notes and Limitations

- The first model execution may take additional time while models initialize.
- Processing time depends on document length, hardware, and model performance.
- Answers depend on the quality of extracted text and retrieved context.
- The local FAISS index must be created before retrieval can be performed.
- The FAISS index and generated summary are local artifacts and can be regenerated by processing the PDFs.
- Only load trusted FAISS index files because the local loader uses pickle deserialization.

## Future Enhancements

- Support additional document formats.
- Improve summary generation with configurable summarization strategies.
- Add document-specific filters and metadata search.
- Improve error handling and processing progress reporting.
- Add automated tests and deployment support.

## License

Add the applicable license and attribution information before publicly redistributing this project.
