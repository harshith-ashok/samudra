"""Single choke point for every Ollama call in the app. Model names live here only."""

import ollama

CHAT_MODEL = "gpt-oss:120b-cloud"
EMBED_MODEL = "nomic-embed-text"

_client = ollama.Client()


def chat(messages: list[dict], tools: list | None = None) -> ollama.ChatResponse:
    return _client.chat(model=CHAT_MODEL, messages=messages, tools=tools)


def embed(texts: list[str]) -> list[list[float]]:
    response = _client.embed(model=EMBED_MODEL, input=texts)
    return response.embeddings
