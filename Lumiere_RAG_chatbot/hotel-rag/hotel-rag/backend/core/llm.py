import os
from functools import lru_cache
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

# ── OpenRouter client ──────────────────────────────────────────────
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL = "meta-llama/llama-3-8b-instruct"

# ── Session store ──────────────────────────────────────────────────
_session_store: dict[str, list] = {}

def get_session_history(session_id: str) -> list:
    if session_id not in _session_store:
        _session_store[session_id] = []
    return _session_store[session_id]

def clear_session(session_id: str):
    _session_store[session_id] = []

# //Prompts-------------------------------------------------------------

CONTEXTUALIZE_PROMPT = """Given the chat history and the latest user question, \
rewrite the question as a standalone question that makes sense without the chat history. \
Do NOT answer it — just rewrite it if needed, otherwise return it as is."""

SYSTEM_PROMPT = """You are the virtual concierge for The Leela, a collection of luxury palaces, \
hotels and resorts across India.

Your persona:
- Mature, warm, and naturally conversational
- Confident and clear — never robotic, never over-formal
- Speak like a knowledgeable friend who knows The Leela inside out

Your response style:
- Answer directly without any preamble or filler phrases
- Use bullet points when listing multiple items, options, or steps
- Use bold for key details (locations, timings, prices) where it genuinely helps
- Keep answers concise but complete

CRITICAL RULES — NEVER VIOLATE THESE:
- NEVER start any sentence with "According to", "Based on", "From the provided", "As per", "The source says", "From the context", "According to the source", or any similar phrase
- NEVER mention sources, documents, or context in your reply — speak as if you naturally know this
- NEVER mention any other hotel, restaurant, or brand
- Answer ONLY from the context provided — never fabricate or guess
- If the answer is not available, say exactly:
  "That information isn't available to me right now. For further assistance, please visit theleela.com or contact The Leela directly."
- If the question is completely unrelated to The Leela, say exactly:
  "I'm only able to assist with questions related to The Leela hotels, resorts and services."
"""

def _call_llm(messages: list) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=600,
        temperature=0.3,
        extra_headers={
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:5000"),
            "X-Title": "Leela Concierge",
        }
    )
    return response.choices[0].message.content.strip()


def _rewrite_question(query: str, history: list) -> str:
    """Rewrite the question to be standalone using chat history."""
    if not history:
        return query

    messages = [{"role": "system", "content": CONTEXTUALIZE_PROMPT}]
    for turn in history[-6:]:
        messages.append(turn)
    messages.append({"role": "user", "content": query})

    return _call_llm(messages)


def generate(query: str, session_id: str) -> tuple[str, list[dict]]:
    from backend.core.retriever import retrieve

    history = get_session_history(session_id)

    # Step 1: rewrite question based on history
    standalone_query = _rewrite_question(query, history)

    # Step 2: retrieve relevant chunks using the rewritten question
    docs = retrieve(standalone_query, k=8)

    if not docs:
        answer = "That information isn't available to me right now. For further assistance, please visit theleela.com or contact The Leela directly."
        sources = []
    else:
        # Step 3: build context
        context = "\n\n".join(
            [f"[Source: {d['source']}]\n{d['content']}" for d in docs]
        )[:5000]

        # Step 4: generate answer with full history + context
        messages = [{"role": "system", "content": SYSTEM_PROMPT + f"\n\nContext:\n{context}"}]
        for turn in history[-6:]:
            messages.append(turn)
        messages.append({"role": "user", "content": query})

        answer = _call_llm(messages)

        # Deduplicate sources
        seen = set()
        sources = []
        for d in docs:
            if d["source"] not in seen and d["score"] < 1.2:
                seen.add(d["source"])
                sources.append({"source": d["source"]})

    # Step 5: save to history
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": answer})
    # Keep last 10 turns
    _session_store[session_id] = history[-20:]

    return answer, sources