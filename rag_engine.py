"""
RAG Engine for TechMart Online Store
Handles document loading, chunking, ChromaDB vector indexing, and Gemini model interactions.
"""

import os
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# Ensure .env is loaded reliably using absolute path relative to this file
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(_BASE_DIR, ".env")
load_dotenv(_ENV_PATH)


DEFAULT_CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "techmart_knowledge_base"


def load_and_chunk_policy(policy_path: str = "policy.txt") -> List[Document]:
    """Loads policy.txt and splits it into semantic section chunks."""
    if not os.path.exists(policy_path):
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    loader = TextLoader(policy_path, encoding="utf-8")
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60,
        separators=["\n\n", "\n", ". ", " "]
    )
    chunks = splitter.split_documents(raw_docs)

    for i, chunk in enumerate(chunks):
        # Extract section header if present
        first_line = chunk.page_content.strip().split("\n")[0]
        chunk.metadata.update({
            "source": os.path.basename(policy_path),
            "doc_type": "policy",
            "section": first_line[:50],
            "chunk_id": i
        })

    return chunks


def load_and_transform_products(products_path: str = "products.xlsx") -> Tuple[List[Document], pd.DataFrame]:
    """
    Loads products.xlsx and converts each row into a structured,
    self-contained semantic Document with rich metadata.
    """
    if not os.path.exists(products_path):
        raise FileNotFoundError(f"Products file not found: {products_path}")

    df = pd.read_excel(products_path)
    docs = []

    for index, row in df.iterrows():
        brand = str(row.get("Brand", "")).strip()
        model = str(row.get("Model Name", "")).strip()
        category = str(row.get("Category", "")).strip()
        specs = str(row.get("Key Specifications", "")).strip()
        best_for = str(row.get("Best For", "")).strip()
        
        try:
            price = float(row.get("price", 0.0))
        except (ValueError, TypeError):
            price = 0.0

        try:
            stock = int(row.get("stock", 0)) if pd.notna(row.get("stock")) else 0
        except (ValueError, TypeError):
            stock = 0

        stock_status = f"{stock} units in stock" if stock > 0 else "Currently out of stock"

        content = (
            f"Product: {brand} {model}\n"
            f"Category: {category}\n"
            f"Price: ${price:.2f}\n"
            f"Availability: {stock_status}\n"
            f"Key Specifications: {specs}\n"
            f"Best For: {best_for}"
        )

        doc = Document(
            page_content=content,
            metadata={
                "source": os.path.basename(products_path),
                "doc_type": "product",
                "category": category,
                "brand": brand,
                "model": model,
                "price": price,
                "stock": stock,
                "in_stock": stock > 0,
                "best_for": best_for
            }
        )
        docs.append(doc)

    return docs, df


def prepare_all_documents(
    policy_path: str = "policy.txt",
    products_path: str = "products.xlsx"
) -> Tuple[List[Document], List[Document], List[Document], pd.DataFrame]:
    """Loads and prepares both policy chunks and product documents."""
    policy_chunks = load_and_chunk_policy(policy_path)
    product_docs, df_products = load_and_transform_products(products_path)
    all_docs = policy_chunks + product_docs
    return policy_chunks, product_docs, all_docs, df_products


def get_embedding_model(api_key: Optional[str] = None):
    """Initializes Google Gemini text embedding model."""
    key = (api_key or "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise ValueError("Google Gemini API Key is required for embeddings.")
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=key
    )


def get_vectorstore(
    api_key: Optional[str] = None,
    persist_directory: str = DEFAULT_CHROMA_DIR,
    force_rebuild: bool = False,
    policy_path: str = "policy.txt",
    products_path: str = "products.xlsx"
) -> Tuple[Chroma, int]:
    """
    Initializes or loads the Chroma vectorstore.
    If the collection is empty or force_rebuild=True, ingests all documents.
    Returns (vectorstore, document_count).
    """
    embeddings = get_embedding_model(api_key)

    if force_rebuild and os.path.exists(persist_directory):
        import shutil
        try:
            shutil.rmtree(persist_directory)
        except Exception:
            pass

    # Initialize Chroma client
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=persist_directory
    )

    current_count = vectorstore._collection.count()

    if current_count == 0 or force_rebuild:
        _, _, all_docs, _ = prepare_all_documents(policy_path, products_path)
        vectorstore.add_documents(all_docs)
        current_count = vectorstore._collection.count()

    return vectorstore, current_count


def get_llm(
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.5-flash",
    temperature: float = 0.3
) -> ChatGoogleGenerativeAI:
    """Initializes Google Gemini chat model."""
    key = (api_key or "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise ValueError("Google Gemini API Key is required for LLM.")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=key
    )


SYSTEM_PROMPT = """You are Charlie, an expert, courteous, and highly knowledgeable AI sales and customer support assistant at TechMart Online Store.

Your mission is to assist customers with:
1. Product recommendations, specifications, pricing, stock availability, and suitability.
2. Company policies including returns, refunds, shipping times/costs, warranties, exchanges, and contact methods.

Guidelines:
- Ground your answers strictly in the provided Context below.
- Always be accurate, polite, and direct.
- When recommending or discussing products:
  - Mention the product brand and model name clearly.
  - Mention the price (e.g., $799.99) and current stock status (In Stock with quantity, or Out of Stock).
  - Highlight relevant key specifications and why it matches the customer's needs.
  - If a requested item is out of stock, explicitly inform the customer and suggest an alternative if available in context.
- When answering policy questions:
  - Cite specific timeframes (e.g., 30-day general return window, 15-day window for electronics, 5 business days for refunds).
  - Clarify shipping costs, exceptions (e.g. final sale), and support channels (support@techmart.com, 1-800-TECHMART).
- If the required information is NOT present in the context, do NOT invent or hallucinate details. Politely explain that TechMart does not currently have that product in stock or that the policy detail is unavailable, and offer to connect them with human support.
- Format responses cleanly with markdown bullet points, bold product names, and concise summaries.

Context:
{context}
"""


def answer_query(
    query: str,
    vectorstore: Chroma,
    llm: ChatGoogleGenerativeAI,
    chat_history: Optional[List[Dict[str, str]]] = None,
    k: int = 4
) -> Dict[str, Any]:
    """
    Executes a RAG query:
    1. Retrieves top-k documents from ChromaDB
    2. Builds formatted context
    3. Invokes Gemini with history
    4. Returns answer and source references
    """
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    retrieved_docs = retriever.invoke(query)

    context_parts = []
    for i, doc in enumerate(retrieved_docs):
        doc_type = doc.metadata.get("doc_type", "document")
        source = doc.metadata.get("source", "knowledge_base")
        context_parts.append(f"[{doc_type.upper()} | Source: {source}]\n{doc.page_content}")

    context_str = "\n\n---\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context_str)}
    ]

    # Include recent chat history (up to last 6 messages)
    if chat_history:
        for msg in chat_history[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})

    messages.append({"role": "user", "content": query})

    # Format into LangChain message objects
    lc_messages = []
    for m in messages:
        if m["role"] == "system":
            lc_messages.append(HumanMessage(content=f"[SYSTEM INSTRUCTION]:\n{m['content']}"))
        elif m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        else:
            lc_messages.append(AIMessage(content=m["content"]))

    response = llm.invoke(lc_messages)

    raw_content = response.content
    if isinstance(raw_content, list):
        text_parts = []
        for part in raw_content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
            elif hasattr(part, "text"):
                text_parts.append(part.text)
        answer_text = "\n".join(text_parts)
    else:
        answer_text = str(raw_content)

    return {
        "answer": answer_text,
        "source_documents": retrieved_docs
    }


def stream_answer_query(
    query: str,
    vectorstore: Chroma,
    llm: ChatGoogleGenerativeAI,
    chat_history: Optional[List[Dict[str, str]]] = None,
    k: int = 4
):
    """
    Executes a streaming RAG query.
    Retrieves top-k documents from ChromaDB, constructs grounded context,
    and returns (retrieved_docs, token_generator) for real-time streaming in Streamlit.
    """
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    retrieved_docs = retriever.invoke(query)

    context_parts = []
    for doc in retrieved_docs:
        doc_type = doc.metadata.get("doc_type", "document")
        source = doc.metadata.get("source", "knowledge_base")
        context_parts.append(f"[{doc_type.upper()} | Source: {source}]\n{doc.page_content}")

    context_str = "\n\n---\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context_str)}
    ]

    if chat_history:
        for msg in chat_history[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})

    messages.append({"role": "user", "content": query})

    lc_messages = []
    for m in messages:
        if m["role"] == "system":
            lc_messages.append(HumanMessage(content=f"[SYSTEM INSTRUCTION]:\n{m['content']}"))
        elif m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        else:
            lc_messages.append(AIMessage(content=m["content"]))

    def token_generator():
        for chunk in llm.stream(lc_messages):
            if hasattr(chunk, "content") and chunk.content:
                if isinstance(chunk.content, str):
                    yield chunk.content
                elif isinstance(chunk.content, list):
                    for part in chunk.content:
                        if isinstance(part, str):
                            yield part
                        elif isinstance(part, dict) and "text" in part:
                            yield part["text"]

    return retrieved_docs, token_generator()

