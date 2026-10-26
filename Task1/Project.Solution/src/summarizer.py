
from pathlib import Path
from datetime import datetime, timezone

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import OLLAMA_LLM_MODEL, TEMPERATURE


def get_llm():
    """Initialize the local Llama model."""
    return ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=TEMPERATURE,
    )


def summarize_documents(documents):
    """Summarize document chunks in groups and combine the results."""

    if not documents:
        raise ValueError("No documents provided for summarization.")

    llm = get_llm()

    prompt = PromptTemplate.from_template(
        """
        You are an expert marketing analyst.

        Summarize the following webinar transcript content.
        Focus on:
        1. Main topics and key takeaways
        2. Important marketing frameworks and strategies
        3. Actionable recommendations
        4. Relevant metrics, examples, and conclusions

        Use clear headings and concise bullet points.
        Do not invent information absent from the source.

        Source content:
        {content}
        """
    )

    chain = prompt | llm | StrOutputParser()

    # Process 8 chunks per request to reduce the number of LLM calls.
    group_size = 8
    partial_summaries = []

    total_chunks = len(documents)
    total_groups = (total_chunks + group_size - 1) // group_size

    for start in range(0, total_chunks, group_size):
        group = documents[start:start + group_size]

        content = "\n\n".join(
            document.page_content for document in group
        )

        group_number = start // group_size + 1
        end = min(start + group_size, total_chunks)

        print(
            f"Summarizing chunks {start + 1}-{end} "
            f"of {total_chunks} "
            f"(group {group_number}/{total_groups})..."
        )

        result = chain.invoke({"content": content})
        partial_summaries.append(result)

        print(f"Completed summary group {group_number}/{total_groups}")

    # Combine the partial summaries into one final summary.
    print("Combining partial summaries into the final summary...")

    final_prompt = PromptTemplate.from_template(
        """
        Combine the following partial summaries into one coherent,
        concise marketing summary.

        Organize the result under:
        - Overview
        - Key Takeaways
        - Marketing Strategies and Frameworks
        - Actionable Recommendations
        - Important Metrics and Conclusions

        Remove repetition. Preserve important facts.
        Do not introduce claims unsupported by the summaries.

        Partial summaries:
        {summaries}
        """
    )

    final_chain = final_prompt | llm | StrOutputParser()

    final_summary = final_chain.invoke({
        "summaries": "\n\n".join(partial_summaries)
    })

    print("Final summary generated successfully.")

    return final_summary


def save_summary(summary, title, output_file="summary.txt"):
    """Save the summary with title and UTC timestamp."""

    metadata = {
        "title": title,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        f"Title: {metadata['title']}\n"
        f"Generated at (UTC): {metadata['timestamp']}\n\n"
        f"{summary}\n",
        encoding="utf-8",
    )

    print(f"Summary saved to: {output_path}")

    return metadata
