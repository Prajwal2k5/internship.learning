
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import OLLAMA_LLM_MODEL, TEMPERATURE
from src.vector_store import load_vector_store


def answer_question(question, k=4):
    """Answer a question using relevant content from the FAISS index."""
    if not question.strip():
        raise ValueError("Please enter a question.")

    vector_store = load_vector_store()
    retriever = vector_store.as_retriever(
        search_kwargs={"k": k}
    )

    relevant_documents = retriever.invoke(question)

    if not relevant_documents:
        return "I could not find relevant information in the indexed documents."

    context = "\n\n".join(
        f"Source: {doc.metadata.get('source', 'Unknown')}, "
        f"Page: {doc.metadata.get('page', 'Unknown')}\n"
        f"{doc.page_content}"
        for doc in relevant_documents
    )

    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=TEMPERATURE,
    )

    prompt = PromptTemplate.from_template(
        """
        You are a helpful marketing knowledge assistant.

        Answer the question using only the supplied document context.
        If the context does not contain the answer, clearly say so.
        Do not invent facts.

        Document context:
        {context}

        Question:
        {question}

        Answer:
        """
    )

    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "context": context,
        "question": question,
    })

    sources = [
        {
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "Unknown"),
        }
        for doc in relevant_documents
    ]

    return {
        "answer": answer,
        "sources": sources,
    }
