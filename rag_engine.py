"""
RAG Engine & AI Agent Core for TechMart Online Store
Architecture:
1. ChromaDB: Stores semantic embeddings of STORE POLICIES ONLY (policy.txt).
2. Google Sheets: Real-time live data for products, orders, and bank details (NOT indexed in ChromaDB).
3. Conversational AI Agent: Answers queries with live catalog data & policy retrieval, evaluates refund eligibility, and collects bank details.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

import sheets_service

logger = logging.getLogger(__name__)

# Ensure .env is loaded reliably using absolute path relative to this file
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(_BASE_DIR, ".env")
load_dotenv(_ENV_PATH)

DEFAULT_CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "techmart_policy_store"
DEFAULT_MODEL = "gemini-3.5-flash-lite"


def load_and_chunk_policy(policy_path: str = "policy.txt") -> List[Document]:
    """Loads policy.txt and splits it into semantic section chunks for ChromaDB."""
    abs_path = os.path.join(_BASE_DIR, policy_path) if not os.path.isabs(policy_path) else policy_path
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Policy file not found: {abs_path}")

    loader = TextLoader(abs_path, encoding="utf-8")
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60,
        separators=["\n\n", "\n", ". ", " "]
    )
    chunks = splitter.split_documents(raw_docs)

    for i, chunk in enumerate(chunks):
        first_line = chunk.page_content.strip().split("\n")[0]
        chunk.metadata.update({
            "source": os.path.basename(policy_path),
            "doc_type": "policy",
            "section": first_line[:50],
            "chunk_id": i
        })

    return chunks


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
    policy_path: str = "policy.txt"
) -> Tuple[Chroma, int]:
    """
    Initializes or loads the Chroma vectorstore.
    Indexes STORE POLICIES ONLY (policy.txt).
    Google Sheets products are NOT stored in ChromaDB and are fetched in real-time.
    """
    embeddings = get_embedding_model(api_key)

    if force_rebuild and os.path.exists(persist_directory):
        import shutil
        try:
            shutil.rmtree(persist_directory)
        except Exception:
            pass

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=persist_directory
    )

    current_count = vectorstore._collection.count()

    if current_count == 0 or force_rebuild:
        policy_chunks = load_and_chunk_policy(policy_path)
        vectorstore.add_documents(policy_chunks)
        current_count = vectorstore._collection.count()

    return vectorstore, current_count


def get_llm(
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.2
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


# ----------------------------------------------------------------
# Real-Time Google Sheets Product Search (No ChromaDB Indexing)
# ----------------------------------------------------------------

def get_live_products_context(query: str, top_k: int = 6) -> str:
    """
    Fetches real-time products directly from Google Sheets (NOT indexed in ChromaDB).
    Matches products based on model, brand, category, keywords, price, and suitability.
    """
    try:
        df = sheets_service.fetch_products_dataframe()
        if df is None or df.empty:
            return ""

        q_lower = query.lower()
        scored_products = []

        # Check for budget constraints (e.g. "under $1000", "under 1000", "below 500")
        price_match = re.search(r'(?:under|below|less than|\$)\s*(\d+)', q_lower)
        max_budget = float(price_match.group(1)) if price_match else None

        for _, row in df.iterrows():
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

            score = 0
            searchable_text = f"{brand} {model} {category} {specs} {best_for}".lower()

            # Exact or partial model match
            model_lower = model.lower()
            if model_lower in q_lower:
                score += 60
            elif any(part in q_lower for part in model_lower.split() if len(part) >= 3):
                score += 30

            # Brand match
            if brand.lower() in q_lower:
                score += 25

            # Category match (e.g. laptop, phone, tablet, headphone)
            cat_clean = category.lower().rstrip("s")
            if cat_clean in q_lower:
                score += 35

            # Keyword matching for use cases
            q_words = [w for w in re.findall(r'\b\w{3,}\b', q_lower) if w not in ["what", "price", "stock", "have", "with", "tell", "show", "much", "does", "cost", "your", "under", "for"]]
            for w in q_words:
                if w in searchable_text:
                    score += 15

            # Budget adjustment
            if max_budget is not None and score > 0:
                if price <= max_budget:
                    score += 20
                else:
                    score -= 40

            if score > 0:
                scored_products.append((score, {
                    "brand": brand,
                    "model": model,
                    "category": category,
                    "price": price,
                    "stock": stock,
                    "specs": specs,
                    "best_for": best_for
                }))

        # If general catalog inquiry without specific match
        if not scored_products and any(kw in q_lower for kw in ["product", "catalog", "item", "inventory", "carry", "store", "buy", "sell", "recommend"]):
            for _, row in df.head(5).iterrows():
                scored_products.append((1, {
                    "brand": row.get("Brand"),
                    "model": row.get("Model Name"),
                    "category": row.get("Category"),
                    "price": float(row.get("price", 0)),
                    "stock": int(row.get("stock", 0)) if pd.notna(row.get("stock")) else 0,
                    "specs": row.get("Key Specifications"),
                    "best_for": row.get("Best For")
                }))

        scored_products.sort(key=lambda x: x[0], reverse=True)
        top_matches = [item[1] for item in scored_products[:top_k]]

        if not top_matches:
            return ""

        lines = [
            "---",
            "[REAL-TIME LIVE PRODUCT CATALOG FROM GOOGLE SHEETS (AUTHORITATIVE)]:"
        ]
        for p in top_matches:
            stock_desc = f"In Stock ({p['stock']} available)" if p['stock'] > 0 else "Currently OUT OF STOCK"
            lines.append(
                f"• {p['brand']} {p['model']} ({p['category']})\n"
                f"  - Current Live Price: ${p['price']:.2f}\n"
                f"  - Real-Time Availability: {stock_desc}\n"
                f"  - Key Specifications: {p['specs']}\n"
                f"  - Best Suited For: {p['best_for']}"
            )
        lines.append("---")
        return "\n".join(lines)

    except Exception as ex:
        logger.error(f"Error in real-time product lookup: {ex}")
        return ""


# ----------------------------------------------------------------
# AI Agent System Prompt
# ----------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """You are Charlie, an expert, courteous, and proactive AI Sales, Support, and Refund Agent at TechMart Online Store.

You have four primary duties:
1. **Answer Customer Inquiries in Real Time**:
   - Provide accurate product recommendations, real-time pricing, and stock status using the Live Product Catalog from Google Sheets below.
   - Clarify store policies on returns, refunds, shipping, warranties, and support channels using the Policy Knowledge Base.
   - Always prioritize real-time Google Sheets information for live prices and inventory.

2. **Take Customer Orders & Update Live Google Sheets**:
   - When a customer wants to buy, purchase, or order a product:
     * Check the live catalog below to see if the model exists and its real-time availability.
     * If the customer's name is not yet provided, politely ask for their full name to complete and finalize their order.
     * When both the product model and customer name are provided, the system registers the order directly into the live Google Sheet with status 'Order Placed'.
     * Warmly congratulate the customer, provide their new Order ID (e.g. ORD-110), confirm the Model Name, total price, and expected delivery timeframe (standard 3-5 business days).

3. **Decide Refund Eligibility**:
   - When a customer asks about a return or refund for an order:
     * If they haven't provided their Order ID (e.g., ORD-101), politely ask for it.
     * When an order is referenced, check the Verified Order & Refund Assessment provided below.
     * **Policy Rules**:
       - Electronics (laptops, phones, tablets, headphones, keyboards, etc.): Must be returned within **15 days** of purchase.
       - General merchandise: Must be returned within **30 days**.
       - Items marked as "Final Sale" cannot be returned.
     * If the order is **ELIGIBLE** (within return window):
       - Congratulate/reassure the customer that their order is eligible for a full refund.
       - State the order details clearly (Order ID, Model, Purchase age).
       - Explicitly instruct them to provide their **Banking Details**:
         1. **Bank Name** (e.g. Meezan Bank, Chase, HBL)
         2. **Account / IBAN Number**
         3. **Mobile Number**
     * If the order is **NOT ELIGIBLE** (exceeded return window):
       - Politely explain why (e.g., "This electronic item was purchased more than 15 days ago, exceeding our return window").
       - Empathize and offer assistance with warranty service or tech support if applicable.

4. **Handle Banking Information**:
   - If the customer provides their banking information for an eligible order:
     * Check the "Live Bank Submission Status" below. If the system has recorded the details, confirm to the user that their banking information has been successfully received and submitted for processing.
     * Reassure them that refunds are disbursed within 5 business days according to TechMart policy.

Policy Knowledge Base (ChromaDB):
{policy_context}

{live_products_context}

{order_context}

{order_placement_context}

{bank_submission_context}
"""


def extract_order_id(text: str) -> Optional[str]:
    """Finds order IDs like ORD-101, ORD-102, etc."""
    match = re.search(r'\b(ORD-\d+)\b', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def extract_order_intent_with_llm(
    query: str,
    chat_history: Optional[List[Dict[str, str]]],
    llm: ChatGoogleGenerativeAI
) -> Dict[str, Any]:
    """Uses Gemini to identify if a customer wants to place an order, the product model, and customer name."""
    history_context = ""
    if chat_history:
        recent = chat_history[-4:]
        history_context = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent])

    prompt = f"""Determine if the customer wants to buy, purchase, or place an order for a product.
Conversation History:
{history_context}

Latest Customer Message: "{query}"

Analyze carefully:
1. Is the customer expressing an intent to buy/purchase/order a product? (is_ordering: boolean)
2. What specific product model or device do they want to purchase? (product_model: string or null)
3. What is the customer's full or first name if they provided it in this message or previous history? (customer_name: string or null)
4. Are BOTH a product model and customer name provided so the order can be placed right now? (ready_to_place: boolean)

Return ONLY a valid JSON object matching:
{{
  "is_ordering": boolean,
  "product_model": string or null,
  "customer_name": string or null,
  "ready_to_place": boolean
}}
JSON:"""

    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        raw = res.content
        if isinstance(raw, list):
            content = "".join([
                p if isinstance(p, str) else p.get("text", "") if isinstance(p, dict) else getattr(p, "text", "")
                for p in raw
            ]).strip()
        else:
            content = str(raw).strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except Exception as ex:
        logger.warning(f"Error in LLM order intent extraction: {ex}")
        return {"is_ordering": False, "product_model": None, "customer_name": None, "ready_to_place": False}


def extract_bank_details_with_llm(
    text: str,
    llm: ChatGoogleGenerativeAI
) -> Dict[str, Any]:
    """Uses Gemini to reliably extract banking details from user messages."""
    prompt = f"""Extract bank details from this text if present.
Return ONLY valid JSON matching this schema:
{{
  "has_bank_info": boolean,
  "bank_name": string or null,
  "account_number": string or null,
  "mobile_number": string or null
}}

Text: "{text}"
JSON:"""

    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        raw = res.content
        if isinstance(raw, list):
            content = "".join([
                p if isinstance(p, str) else p.get("text", "") if isinstance(p, dict) else getattr(p, "text", "")
                for p in raw
            ]).strip()
        else:
            content = str(raw).strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except Exception as ex:
        logger.warning(f"Error in LLM bank extraction: {ex}")
        return {"has_bank_info": False, "bank_name": None, "account_number": None, "mobile_number": None}


def inspect_order_and_refund_flow(
    query: str,
    chat_history: Optional[List[Dict[str, str]]],
    llm: ChatGoogleGenerativeAI,
    active_order: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str, str, str, Optional[Dict[str, Any]]]:
    """
    Examines the active query and recent conversation for:
    1. Order ID mentions and refund eligibility.
    2. Bank detail submissions.
    3. New order placement requests (e.g. buying a MacBook Air M3).
    """
    order_id = extract_order_id(query)
    if not order_id and active_order and active_order.get("order_id"):
        order_id = active_order.get("order_id")
    if not order_id and chat_history:
        for msg in reversed(chat_history[-6:]):
            found = extract_order_id(msg.get("content", ""))
            if found:
                order_id = found
                break

    matched_order = None
    refund_eval = None
    order_context_str = ""
    bank_submission_str = ""
    order_placement_str = ""
    new_placed_order = None

    if order_id:
        matched_order = sheets_service.find_order(order_id)
        if not matched_order and active_order and str(active_order.get("order_id", "")).upper() == str(order_id).upper():
            matched_order = active_order

        if matched_order:
            refund_eval = sheets_service.evaluate_refund_eligibility(matched_order)
            order_context_str = f"""---
[VERIFIED LIVE ORDER & REFUND ASSESSMENT from Google Sheets]:
Order ID: {refund_eval['order_id']}
Customer: {refund_eval['customer']}
Product: {refund_eval['model_name']}
Category: {refund_eval['category']}
Purchase Age: {refund_eval['days_ago']} days ago
Allowed Return Window: {refund_eval['allowed_days']} days ({refund_eval['item_type']})
Current Status: {refund_eval['status']}
Eligible for Refund: {'YES' if refund_eval['eligible'] else 'NO'}
Assessment Summary: {refund_eval['message']}
---"""

    # Check for bank details submission
    has_digits = bool(re.search(r'\d{3,}', query))
    has_bank_word = bool(re.search(r'\b(bank|account|acc|acct|iban|routing|meezan|chase|hbl|habib|ubl|mcb|nayapay|sadapay|easypaisa|jazzcash)\b', query, re.I))
    if has_digits and has_bank_word:
        bank_data = extract_bank_details_with_llm(query, llm)
        if bank_data.get("has_bank_info") and bank_data.get("account_number"):
            oid = order_id or (active_order.get("order_id") if active_order else "ORD-UNKNOWN")
            cust = matched_order.get("customer", "Customer") if matched_order else (active_order.get("customer", "Customer") if active_order else "Customer")
            prod = matched_order.get("Model Name", matched_order.get("product", "Item")) if matched_order else (active_order.get("model_name", "Item") if active_order else "Item")
            bank_name = bank_data.get("bank_name") or "Bank"
            account_num = bank_data.get("account_number") or ""
            mobile_num = bank_data.get("mobile_number") or ""

            sub_res = sheets_service.submit_bank_details(
                order_id=oid,
                customer=cust,
                product=prod,
                bank_name=bank_name,
                account_number=account_num,
                mobile_number=mobile_num
            )

            client_email = sheets_service.get_service_account_email()
            is_synced = sub_res.get("sheet_synced", False)

            if is_synced:
                sync_desc = "SUCCESS (Directly updated in live Google Sheet: Bank_details)."
                perm_instruction = "Confirm that these details have been submitted and updated in Google Sheets."
            else:
                sync_desc = f"SAVED LOCALLY (Google Sheets rejected write because service account {client_email} only has 'Viewer' permission)."
                perm_instruction = (
                    f"Inform the customer/user that their banking details have been securely captured. "
                    f"Crucially, add a short note that to update the live Google Sheet directly, the store owner should change "
                    f"`{client_email}` from 'Viewer' to 'Editor' in Google Sheets Share settings."
                )

            bank_submission_str = f"""---
[LIVE BANK SUBMISSION STATUS]:
The customer has provided banking information, and the system has processed it:
- Order ID: {oid}
- Customer: {cust}
- Product: {prod}
- Bank Name: {bank_name}
- Account Number: {account_num}
- Mobile Number: {mobile_num}
- Cloud Sync Status: {sync_desc}

REQUIRED ACTION:
1. Acknowledge receipt warmly and confirm the details (Bank, Account, Mobile, Order ID {oid}).
2. Reassure the customer that their refund will be processed within 5 business days.
3. {perm_instruction}
---"""

    # Check for customer order placement (Buy / Order intent)
    order_keywords = bool(re.search(r'\b(buy|order|purchase|checkout|book|get this|place an order|want to buy|want to order|want this|i will take|i\'ll take)\b', query, re.I))
    history_asking_name = False
    if chat_history:
        last_asst = next((m.get("content", "") for m in reversed(chat_history) if m.get("role") == "assistant"), "")
        if any(w in last_asst.lower() for w in ["name", "order", "place your order", "finalize your order"]):
            history_asking_name = True

    if order_keywords or history_asking_name:
        order_intent = extract_order_intent_with_llm(query, chat_history, llm)
        if order_intent.get("is_ordering"):
            cust_name = order_intent.get("customer_name")
            prod_model = order_intent.get("product_model")
            ready = order_intent.get("ready_to_place")

            if ready and cust_name and prod_model:
                new_placed_order = sheets_service.create_new_order(
                    customer=cust_name.strip(),
                    model_name=prod_model.strip()
                )
                order_placement_str = f"""---
[LIVE NEW ORDER CREATED & UPDATED IN GOOGLE SHEETS]:
A new customer order has been successfully recorded and added to the Orders Google Sheet!
- Order ID: {new_placed_order['order_id']}
- Customer: {new_placed_order['customer']}
- Model Name: {new_placed_order['model_name']}
- Product Type: {new_placed_order['product']}
- Category: {new_placed_order['category']}
- Price: ${new_placed_order.get('price', 0.0):.2f}
- Current Status: {new_placed_order['status']}
- Google Sheets Sync: {'Success (Appended to live sheet)' if new_placed_order.get('sheet_synced') else 'Recorded Locally'}

REQUIRED AGENT RESPONSE:
1. Congratulate {cust_name} warmly on placing their new order!
2. Confirm their new Order ID ({new_placed_order['order_id']}), the exact Model Name ({new_placed_order['model_name']}), and price (${new_placed_order.get('price', 0.0):.2f}).
3. Inform them that their order is registered with status 'Order Placed' and standard delivery will arrive within 3-5 business days.
---"""
            elif prod_model and not cust_name:
                order_placement_str = f"""---
[CUSTOMER ORDER IN PROGRESS - CUSTOMER NAME NEEDED]:
The customer wants to buy/order: {prod_model}.
REQUIRED AGENT RESPONSE:
1. Verify that this item is in our live catalog and state its live price and availability.
2. Politely ask the customer for their full name so you can finalize and record their order in our store database right now!
---"""
            elif not prod_model:
                order_placement_str = """---
[CUSTOMER ORDER IN PROGRESS - MODEL NEEDED]:
The customer expressed an intent to purchase/order, but hasn't specified which product or model.
REQUIRED AGENT RESPONSE:
Ask the customer which device or product model they would like to order from our live catalog.
---"""

    return matched_order, refund_eval, order_context_str, bank_submission_str, order_placement_str, new_placed_order


def answer_query(
    query: str,
    vectorstore: Chroma,
    llm: ChatGoogleGenerativeAI,
    chat_history: Optional[List[Dict[str, str]]] = None,
    k: int = 4,
    active_order: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes an intelligent agent query:
    1. Retrieves policy documents from ChromaDB (Store policies only).
    2. Fetches matching products in real-time from Google Sheets.
    3. Checks order & refund status in real-time from Google Sheets.
    4. Handles order placements directly into Google Sheets.
    """
    # 1. ChromaDB retrieves store policy chunks ONLY
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    policy_docs = retriever.invoke(query)
    policy_parts = [f"[{d.metadata.get('section', 'POLICY')}]\n{d.page_content}" for d in policy_docs]
    policy_context_str = "\n\n---\n\n".join(policy_parts)

    # 2. Real-time live Google Sheets product search
    live_products_str = get_live_products_context(query)

    # 3. Real-time Google Sheets order, refund, and order placement inspection
    matched_order, refund_eval, order_ctx, bank_ctx, order_place_ctx, new_order = inspect_order_and_refund_flow(
        query, chat_history, llm, active_order=active_order
    )

    system_instruction = AGENT_SYSTEM_PROMPT.format(
        policy_context=policy_context_str,
        live_products_context=live_products_str,
        order_context=order_ctx,
        order_placement_context=order_place_ctx,
        bank_submission_context=bank_ctx
    )

    messages = [
        HumanMessage(content=f"[SYSTEM INSTRUCTION]:\n{system_instruction}")
    ]

    if chat_history:
        for msg in chat_history[-6:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=query))

    response = llm.invoke(messages)

    raw_content = response.content
    if isinstance(raw_content, list):
        text_parts = []
        for part in raw_content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif hasattr(part, "text"):
                text_parts.append(part.text)
        answer_text = "\n".join(text_parts)
    else:
        answer_text = str(raw_content)

    return {
        "answer": answer_text,
        "source_documents": policy_docs,
        "matched_order": matched_order,
        "refund_eval": refund_eval,
        "new_order": new_order
    }


def stream_answer_query(
    query: str,
    vectorstore: Chroma,
    llm: ChatGoogleGenerativeAI,
    chat_history: Optional[List[Dict[str, str]]] = None,
    k: int = 4,
    active_order: Optional[Dict[str, Any]] = None
):
    """
    Executes a streaming agent query with:
    - Policy chunks retrieved from ChromaDB
    - Live product information fetched in real-time from Google Sheets
    - Live orders & bank details from Google Sheets
    - Real-time customer order placement into Google Sheets
    """
    # 1. ChromaDB retrieves store policy chunks ONLY
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    policy_docs = retriever.invoke(query)
    policy_parts = [f"[{d.metadata.get('section', 'POLICY')}]\n{d.page_content}" for d in policy_docs]
    policy_context_str = "\n\n---\n\n".join(policy_parts)

    # 2. Real-time live Google Sheets product search
    live_products_str = get_live_products_context(query)

    # 3. Real-time Google Sheets order, refund, and order placement inspection
    matched_order, refund_eval, order_ctx, bank_ctx, order_place_ctx, new_order = inspect_order_and_refund_flow(
        query, chat_history, llm, active_order=active_order
    )

    system_instruction = AGENT_SYSTEM_PROMPT.format(
        policy_context=policy_context_str,
        live_products_context=live_products_str,
        order_context=order_ctx,
        order_placement_context=order_place_ctx,
        bank_submission_context=bank_ctx
    )

    messages = [
        HumanMessage(content=f"[SYSTEM INSTRUCTION]:\n{system_instruction}")
    ]

    if chat_history:
        for msg in chat_history[-6:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=query))

    def token_generator():
        for chunk in llm.stream(messages):
            if hasattr(chunk, "content") and chunk.content:
                if isinstance(chunk.content, str):
                    yield chunk.content
                elif isinstance(chunk.content, list):
                    for part in chunk.content:
                        if isinstance(part, str):
                            yield part
                        elif isinstance(part, dict) and "text" in part:
                            yield part["text"]

    return policy_docs, token_generator(), matched_order, refund_eval, new_order
