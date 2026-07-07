"""Retrieval-Augmented Generation (RAG) utilities and tool.

Builds an in-memory RAG pipeline that:
- Loads PDF documents from `RAG_DATA_DIR` (default: "data").
- Splits documents into token-aware chunks.
- Embeds chunks and stores vectors in an in-memory Qdrant store.
- Exposes a LangChain Tool `retrieve_information` that retrieves relevant
  context and generates a response constrained to that context.

The graph builder is provider-parameterized so evaluation harnesses can run the
SAME pipeline against different chat/embedding models (e.g. Fireworks vs OpenAI).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated, TypedDict

import tiktoken
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

# Prompt kept identical to the original app so evaluation stays representative.
_HUMAN_TEMPLATE = (
    "\n#CONTEXT:\n{context}\n\nQUERY:\n{query}\n\n"
    "Use the provide context to answer the provided user query. "
    "Only use the provided context to answer the query. If you do not know the answer, "
    'or it\'s not contained in the provided context respond with "I don\'t know"'
)
_CHAT_PROMPT = ChatPromptTemplate.from_messages([("human", _HUMAN_TEMPLATE)])


def _tiktoken_len(text: str) -> int:
    """Return token length using tiktoken; used for chunk length measurement."""
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))


class _RAGState(TypedDict):
    """State schema for the two-step RAG graph: retrieve then generate."""

    question: str
    context: list[Document]
    response: str
    response_message: AIMessage | None  # raw message so token usage survives


def default_fireworks_chat_model() -> ChatOpenAI:
    """The app's default generation model (Fireworks gpt-oss-20b)."""
    return ChatOpenAI(
        model=os.environ.get("FIREWORKS_CHAT_MODEL", "accounts/fireworks/models/gpt-oss-20b"),
        openai_api_key=os.environ["FIREWORKS_API_KEY"],
        openai_api_base=FIREWORKS_BASE_URL,
    )


def default_fireworks_embeddings() -> OpenAIEmbeddings:
    """The app's default embedding model (Fireworks qwen3-embedding-4b)."""
    return OpenAIEmbeddings(
        model=os.environ.get("FIREWORKS_EMBEDDING_MODEL", "accounts/fireworks/models/qwen3-embedding-8b"),
        openai_api_key=os.environ["FIREWORKS_API_KEY"],
        openai_api_base=FIREWORKS_BASE_URL,
        check_embedding_ctx_length=False,
        dimensions=4096,
    )


def load_and_split(data_dir: str) -> list[Document]:
    """Load PDFs from `data_dir` (recursive) and split into token-aware chunks."""
    try:
        documents = DirectoryLoader(
            data_dir, glob="**/*.pdf", loader_cls=PyMuPDFLoader
        ).load()
    except Exception:
        documents = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=750, chunk_overlap=0, length_function=_tiktoken_len
    )
    return splitter.split_documents(documents) if documents else []


def build_rag_graph(
    *,
    chat_model: ChatOpenAI | None = None,
    embedding_model: OpenAIEmbeddings | None = None,
    data_dir: str = "data",
    collection_name: str = "rag_collection",
    chunks: list[Document] | None = None,
):
    """Construct and compile the retrieve -> generate RAG graph.

    Provider-agnostic: pass any `chat_model` / `embedding_model`. Defaults reproduce
    the original Fireworks behavior. Pass pre-split `chunks` to reuse a corpus split.
    """
    chat_model = chat_model or default_fireworks_chat_model()
    embedding_model = embedding_model or default_fireworks_embeddings()
    if chunks is None:
        chunks = load_and_split(data_dir)

    vectorstore = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embedding_model,
        location=":memory:",
        collection_name=collection_name,
    )
    retriever = vectorstore.as_retriever()

    def retrieve(state: _RAGState) -> _RAGState:
        retrieved_docs = retriever.invoke(state["question"]) if retriever else []
        return {"context": retrieved_docs}  # type: ignore

    def generate(state: _RAGState) -> _RAGState:
        # Invoke the model directly (no StrOutputParser) so usage_metadata survives.
        messages = _CHAT_PROMPT.format_messages(
            query=state["question"], context=state.get("context", [])
        )
        message = chat_model.invoke(messages)
        return {  # type: ignore
            "response": str(message.content),
            "response_message": message,
        }

    graph_builder = StateGraph(_RAGState)
    graph_builder.add_sequence([retrieve, generate])
    graph_builder.add_edge(START, "retrieve")
    return graph_builder.compile()


@lru_cache(maxsize=1)
def _get_rag_graph():
    """Return a cached compiled RAG graph built from RAG_DATA_DIR (default Fireworks)."""
    data_dir = os.environ.get("RAG_DATA_DIR", "data")
    return build_rag_graph(data_dir=data_dir)


@tool
def retrieve_information(
    query: Annotated[str, "query to ask the retrieve information tool"],
):
    """Use Retrieval Augmented Generation to retrieve information about feline health, including life stage care, nutrition, vaccinations, parasite control, behavior, diagnostics, and veterinary guidelines for cats."""
    graph = _get_rag_graph()
    result = graph.invoke({"question": query})
    if isinstance(result, dict) and "response" in result:
        return result["response"]  # still a plain string — agent unaffected
    return result
