
from langchain_ollama import ChatOllama

try:
    llm = ChatOllama(
        model="llama3",
        temperature=0.2
    )

    response = llm.invoke("Reply with only the word OK")

    print("Ollama connection successful!")
    print("Model response:", response.content)

except Exception as e:
    print("Ollama connection failed!")
    print("Error:", e)
