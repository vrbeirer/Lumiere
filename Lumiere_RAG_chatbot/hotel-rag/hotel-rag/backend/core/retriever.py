import os
from functools import lru_cache
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

VECTOR_PATH = os.path.join(os.path.dirname(__file__), "../../vectorstore")


@lru_cache(maxsize=1)
def _load_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def _load_db():
    embeddings = _load_embeddings()
    return FAISS.load_local(
        VECTOR_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )


def get_vectorstore():
    return _load_db()


def retrieve(query: str, k: int = 8) -> list[dict]:
    db = _load_db()
    results = db.similarity_search_with_score(query, k=k)

    docs = []
    seen = set()
    for doc, score in results:
        content = doc.page_content.strip()
        if content in seen:
            continue
        seen.add(content)
        source = doc.metadata.get("source", "")
        source_name = os.path.basename(source) if source else "The Leela"
        docs.append({
            "content": content,
            "source": source_name,
            "score": float(score),
        })
    return docs