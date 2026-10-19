import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

DATA_PATH   = "data/pdfs"
VECTOR_PATH = "vectorstore"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_pdfs():
    docs = []
    if not os.path.exists(DATA_PATH):
        return docs
    for file in os.listdir(DATA_PATH):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(DATA_PATH, file))
            docs.extend(loader.load())
    print(f"Loaded {len(docs)} pages from PDFs")
    return docs


def crawl_website(base_url: str, max_pages: int = 60) -> list[Document]:
    visited = set()
    to_visit = [base_url]
    docs = []
    base_netloc = urlparse(base_url).netloc

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            response = requests.get(url, headers=HEADERS, timeout=12)
            if response.status_code != 200:
                print(f"  SKIP {url} ({response.status_code})")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove noise
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                tag.decompose()

            text = " ".join(soup.get_text(separator=" ").split())

            if len(text) > 200:
                docs.append(Document(
                    page_content=text,
                    metadata={"source": url}
                ))
                print(f"  OK [{len(visited)}/{max_pages}] {url} ({len(text)} chars)")

            # Collect internal links
            for a in soup.find_all("a", href=True):
                href = urljoin(base_url, a["href"])
                parsed = urlparse(href)
                # Only follow same domain, ignore anchors/query heavy URLs
                if (parsed.netloc == base_netloc
                        and href not in visited
                        and "#" not in href
                        and href not in to_visit):
                    to_visit.append(href)

            time.sleep(0.3)  # polite delay

        except Exception as e:
            print(f"  ERROR {url}: {e}")

    print(f"Crawled {len(docs)} pages from {base_url}")
    return docs


def create_vector_store(website_url: str = "https://www.theleela.com"):
    print("Loading PDFs...")
    pdf_docs = load_pdfs()

    print(f"Crawling website: {website_url}")
    web_docs = crawl_website(website_url, max_pages=60)

    all_docs = pdf_docs + web_docs
    print(f"Total documents: {len(all_docs)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=120,
        length_function=len,
    )
    chunks = splitter.split_documents(all_docs)
    print(f"Total chunks: {len(chunks)}")

    print("Loading embedding model...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    print("Building FAISS index...")
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(VECTOR_PATH)
    print(f"Vectorstore saved to '{VECTOR_PATH}' with {db.index.ntotal} vectors")


if __name__ == "__main__":
    create_vector_store()