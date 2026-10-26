
from src.qa_engine import answer_question

question = "What are the key content marketing strategies?"

result = answer_question(question)

print("\nQUESTION:")
print(question)

print("\nANSWER:")
if isinstance(result, dict):
    print(result["answer"])

    print("\nSOURCES:")
    for source in result["sources"]:
        print(
            f"- {source['source']}, "
            f"page {source['page']}"
        )
else:
    print(result)
