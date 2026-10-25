"""
TechMart AI Agent — Enterprise Streamlit RAG Platform
Powered by Google Gemini 3.8 Flash & ChromaDB.
Integrates live Google Sheets for:
- Products catalog: 1RZ1U4TKfqqjY4kpbvFUQOJd_PwDlYp0I
- Orders database: 18G2BQlwSihkgC5JcCFosbMVEbSQBQE_hgvKpFogcWCI
- Bank details collection: 1gWgVsSVU4u1V8qTcEIKj7F81XxY02Y-0sJCdc-J6gNg
"""

import os
import json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Load environment variables reliably using absolute path
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_FILE = os.path.join(_BASE_DIR, ".env")
load_dotenv(_ENV_FILE)

# Import RAG engine and Google Sheets service
import sheets_service
from rag_engine import (
    load_and_chunk_policy,
    get_vectorstore,
    get_llm,
    answer_query,
    stream_answer_query,
    DEFAULT_CHROMA_DIR,
    COLLECTION_NAME
)

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="TechMart AI Agent | Sales, Support & Refunds",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Modern UI Theme & CSS
# ---------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"], [data-testid="stAppViewContainer"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Main Container Padding */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1250px;
}

/* Header Banner */
.hero-banner {
    background: linear-gradient(135deg, #09090b 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1px solid #312e81;
    border-radius: 16px;
    padding: 24px 30px;
    margin-bottom: 20px;
    color: #ffffff;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
}

.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: #f4f4f5;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.hero-title {
    font-size: 2.0rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0 0 6px 0;
    color: #ffffff;
}

.hero-subtitle {
    font-size: 0.95rem;
    color: #cbd5e1;
    margin: 0;
    max-width: 780px;
    line-height: 1.5;
}

/* Stat Cards */
.stat-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    text-align: center;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px -2px rgba(0, 0, 0, 0.08);
}
.stat-val {
    font-size: 1.6rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.02em;
}
.stat-label {
    font-size: 0.76rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #64748b;
    margin-top: 4px;
}

/* Product Cards */
.product-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 14px;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.product-card:hover {
    border-color: #6366f1;
    box-shadow: 0 8px 20px -4px rgba(99, 102, 241, 0.12);
}

.product-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f172a;
    margin: 6px 0 4px 0;
}

.badge-category {
    background: #eef2ff;
    color: #4338ca;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    display: inline-block;
}

.stock-badge-in {
    background: #ecfdf5;
    color: #047857;
    font-weight: 700;
    font-size: 0.76rem;
    padding: 3px 8px;
    border-radius: 6px;
    display: inline-block;
}
.stock-badge-out {
    background: #fef2f2;
    color: #b91c1c;
    font-weight: 700;
    font-size: 0.76rem;
    padding: 3px 8px;
    border-radius: 6px;
    display: inline-block;
}

.price-tag {
    font-size: 1.25rem;
    font-weight: 800;
    color: #0f172a;
}

/* Decision Badges */
.eligible-box {
    background: #ecfdf5;
    border: 1.5px solid #10b981;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0;
    color: #064e3b;
}

.ineligible-box {
    background: #fef2f2;
    border: 1.5px solid #ef4444;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0;
    color: #7f1d1d;
}

/* Quick Reference Chips */
.quick-chip {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    text-align: center;
}
.quick-chip-val {
    font-size: 1.15rem;
    font-weight: 800;
    color: #09090b;
}
.quick-chip-lbl {
    font-size: 0.74rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    margin-top: 2px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------
# Cached Resource Loaders
@st.cache_data(show_spinner=False, ttl=60)
def load_all_cached_data():
    """Loads policy chunks and live Google Sheets products DataFrame."""
    policy_chunks = load_and_chunk_policy("policy.txt")
    df_products = sheets_service.fetch_products_dataframe()
    return policy_chunks, df_products


@st.cache_resource(show_spinner=False)
def get_cached_vs(api_key: str):
    """Initializes and caches Chroma vectorstore in RAM for instant queries."""
    return get_vectorstore(
        api_key=api_key,
        persist_directory=DEFAULT_CHROMA_DIR,
        force_rebuild=False
    )


@st.cache_resource(show_spinner=False)
def get_cached_llm(api_key: str, model_name: str, temperature: float):
    """Caches LLM instance to avoid re-instantiation."""
    return get_llm(api_key=api_key, model_name=model_name, temperature=temperature)


# ---------------------------------------------------------
# Sidebar Configuration & Controls
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")

    # API Key Configuration
    env_api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if "api_key" not in st.session_state or not st.session_state["api_key"]:
        st.session_state["api_key"] = env_api_key

    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.get("api_key", env_api_key),
        type="password",
        help="Loaded automatically from .env. You can also override it here if needed."
    )

    if api_key_input:
        st.session_state["api_key"] = api_key_input.strip()

    active_api_key = st.session_state.get("api_key", "").strip() or env_api_key

    if not active_api_key:
        st.warning("⚠️ Enter your Gemini API key above to activate intelligent chat & embeddings.", icon="🔑")
        st.markdown("[👉 Get a Free Gemini API Key](https://aistudio.google.com/app/apikey)")
    else:
        st.success("API Key active (from .env)", icon="✅")

    st.markdown("---")
    st.markdown("### 🧠 Model & Retrieval")

    model_options = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash"
    ]
    model_choice = st.selectbox(
        "Gemini Model",
        options=model_options,
        index=0,
        help="Gemini 3.5 Flash Lite is selected by default for ultra-fast, 1-2 second responses."
    )

    use_streaming = st.toggle("⚡ Real-time Token Streaming", value=True, help="Stream answers word-by-word.")
    show_sources = st.toggle("🔍 Show Grounded Sources", value=False, help="Display retrieved knowledge chunks below responses (disabled by default).")

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.05,
        help="Lower values produce more deterministic, fact-grounded responses."
    )

    top_k = st.slider(
        "Retrieved Sources (Top-K)",
        min_value=2,
        max_value=8,
        value=4,
        step=1,
        help="Number of relevant knowledge chunks retrieved from ChromaDB."
    )

    st.markdown("---")
    st.markdown("### ☁️ Google Sheets Telemetry")

    try:
        policy_chunks, df_products = load_all_cached_data()
        in_stock_count = int((df_products["stock"] > 0).sum()) if df_products is not None else 0
        orders_data = sheets_service.fetch_orders()
        bank_data = sheets_service.fetch_bank_details()

        st.markdown(f"""
        - 📦 **Products in Live Sheet**: `{len(df_products)} SKUs` *(Real-Time)*
        - 🟢 **In-Stock Units**: `{in_stock_count}`
        - 📋 **Live Orders**: `{len(orders_data)} orders`
        - 💳 **Bank Records**: `{len(bank_data)} entries`
        - 📜 **Policy Clauses in ChromaDB**: `{len(policy_chunks)} chunks`
        - 🏷️ **Policy Collection**: `{COLLECTION_NAME}`
        """)
    except Exception as e:
        st.error(f"Error loading telemetry: {e}")

    # Reindex Vector Database Action
    if active_api_key:
        if st.button("🔄 Sync Live Sheets to ChromaDB", use_container_width=True, help="Force re-fetch Google Sheets and re-embed all documents"):
            with st.spinner("Re-fetching Google Sheets and rebuilding ChromaDB index..."):
                try:
                    load_all_cached_data.clear()
                    get_cached_vs.clear()
                    sheets_service.clear_cache()
                    vs, count = get_vectorstore(api_key=active_api_key, force_rebuild=True)
                    st.success(f"Indexed {count} documents into ChromaDB!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Failed to rebuild index: {ex}")

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["active_refund_order"] = None
        st.rerun()


# ---------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <div class="hero-pill">🤖 Autonomous AI Sales & Refund Agent</div>
    <h1 class="hero-title">TechMart AI Assistant</h1>
    <p class="hero-subtitle">
        Intelligent customer assistant grounded in Google Sheets catalog & orders.
        Answers sales inquiries, evaluates refund eligibility based on store policy, and securely collects banking information.
    </p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Key Performance Metrics Row
# ---------------------------------------------------------
try:
    policy_chunks, df_products = load_all_cached_data()
    m1, m2, m3, m4 = st.columns(4)

    total_prods = len(df_products)
    in_stock_total = int((df_products["stock"] > 0).sum())
    total_clauses = len(policy_chunks)
    orders_count = len(sheets_service.fetch_orders())

    with m1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val">{total_prods}</div>
            <div class="stat-label">Google Sheets SKUs</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #059669;">{in_stock_total}</div>
            <div class="stat-label">In-Stock Items</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #4f46e5;">{orders_count}</div>
            <div class="stat-label">Live Orders</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #7c3aed;">Chroma + Sheets</div>
            <div class="stat-label">RAG Architecture</div>
        </div>
        """, unsafe_allow_html=True)

except Exception:
    pass

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Tabbed Navigation
# ---------------------------------------------------------
tab_chat, tab_refund, tab_catalog, tab_policies = st.tabs([
    "💬 Chat with Charlie (AI Agent)",
    "🛒 Orders & Refunds Agent (Google Sheets)",
    "📦 Live Product Catalog (Google Sheets)",
    "📜 Store Policies & FAQ"
])

# Initialize session state for messages and active refund order
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I'm **Charlie**, your TechMart AI Sales, Order, and Refund Agent.\n\n"
                "I can help you:\n"
                "1. 🛍️ **Explore Products & Place Orders**: Check specs, real-time prices, and place an order directly for any model (e.g. *'I want to buy the MacBook Air M3, my name is Ali'*).\n"
                "2. 🔄 **Check Refund Eligibility**: Just give me your **Order ID** (e.g. `ORD-101`, `ORD-104`), and I'll verify if your order is eligible under our return policy.\n"
                "3. 💳 **Process Your Refund**: If eligible, I'll securely collect your banking details to disburse your refund.\n\n"
                "What can I assist you with today?"
            ),
            "sources": []
        }
    ]

if "active_refund_order" not in st.session_state:
    st.session_state["active_refund_order"] = None


# ---------------------------------------------------------
# TAB 1: Chat Interface
# ---------------------------------------------------------
with tab_chat:
    # Quick Suggestion Chips
    st.markdown("**💡 Quick Inquiries:**")
    q1, q2, q3, q4 = st.columns(4)

    preset_query = None
    with q1:
        if st.button("🛒 Order: MacBook Air M3", key="chip_q1", use_container_width=True):
            preset_query = "I would like to order the MacBook Air M3. My name is Hamza."
    with q2:
        if st.button("🔄 Check Refund: ORD-101", key="chip_q2", use_container_width=True):
            preset_query = "Can I get a refund for order ORD-101? Is it eligible?"
    with q3:
        if st.button("❌ Check Refund: ORD-104", key="chip_q3", use_container_width=True):
            preset_query = "I would like to request a refund for order ORD-104."
    with q4:
        if st.button("🚚 Shipping & Return Policy", key="chip_q4", use_container_width=True):
            preset_query = "What is the return window for electronics, and how much is shipping?"

    # Check if a product inquiry was triggered from the Catalog tab
    if "pending_query" in st.session_state and st.session_state["pending_query"]:
        preset_query = st.session_state["pending_query"]
        st.session_state["pending_query"] = None

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Render Chat History
    for idx, msg in enumerate(st.session_state["messages"]):
        is_user = msg["role"] == "user"
        with st.chat_message(msg["role"], avatar="🧑‍💻" if is_user else "🛍️"):
            st.markdown(msg["content"])

            # Render Grounded Sources if enabled in settings
            sources = msg.get("sources", [])
            if show_sources and sources and not is_user:
                with st.expander(f"🔍 Grounded Knowledge Sources ({len(sources)} chunks retrieved)", expanded=False):
                    for s_idx, doc in enumerate(sources):
                        meta = doc.get("metadata", {}) if isinstance(doc, dict) else getattr(doc, "metadata", {})
                        content = doc.get("page_content", "") if isinstance(doc, dict) else getattr(doc, "page_content", "")
                        doc_type = meta.get("doc_type", "document").upper()
                        source_file = meta.get("source", "knowledge_base")
                        badge_color = "#059669" if doc_type == "PRODUCT" else "#2563eb"

                        st.markdown(f"""
                        <div class="source-card">
                            <div class="source-header">
                                <span style="background: {badge_color}; color: #ffffff; padding: 2px 6px; border-radius: 4px;">{doc_type}</span>
                                <span>Source: {source_file}</span>
                                {f"<span>· Brand: {meta.get('brand')}</span>" if 'brand' in meta else ""}
                                {f"<span>· Model: {meta.get('model')}</span>" if 'model' in meta else ""}
                            </div>
                            <div style="color: #3f3f46; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; white-space: pre-wrap; line-height: 1.4;">
{content.strip()}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # Interactive Banking Details Widget (if an eligible refund order is active)
    active_ord = st.session_state.get("active_refund_order")
    if active_ord and active_ord.get("eligible"):
        with st.expander("💳 **Quick Bank Details Form for " + str(active_ord.get('order_id')) + "** (Click to submit)", expanded=True):
            st.info(f"Order **{active_ord.get('order_id')}** ({active_ord.get('model_name')}) is eligible for refund. Fill details below or simply type them in chat!")
            bf_c1, bf_c2, bf_c3 = st.columns(3)
            with bf_c1:
                in_bank = st.text_input("Bank Name", placeholder="e.g. Meezan Bank, Chase, HBL", key="chat_bank_name")
            with bf_c2:
                in_acc = st.text_input("Account Number / IBAN", placeholder="e.g. 9876543210", key="chat_acc_num")
            with bf_c3:
                in_mob = st.text_input("Mobile Number", placeholder="e.g. 03001234567", key="chat_mob_num")

            if st.button("🚀 Submit Banking Information", key="btn_submit_chat_bank", use_container_width=True):
                if in_bank and in_acc and in_mob:
                    res = sheets_service.submit_bank_details(
                        order_id=active_ord.get("order_id"),
                        customer=active_ord.get("customer", "Customer"),
                        product=active_ord.get("model_name", "Item"),
                        bank_name=in_bank,
                        account_number=in_acc,
                        mobile_number=in_mob
                    )
                    sa_email = sheets_service.get_service_account_email()
                    if res.get("sheet_synced"):
                        confirm_text = (
                            f"🎉 **Banking Information Recorded & Synced to Google Sheets!**\n"
                            f"- **Order ID:** {active_ord.get('order_id')}\n"
                            f"- **Bank:** {in_bank}\n"
                            f"- **Account:** {in_acc}\n"
                            f"- **Mobile:** {in_mob}\n\n"
                            f"Your refund has been approved and will be processed within 5 business days."
                        )
                        st.success(f"✅ Banking details for Order {active_ord.get('order_id')} synced to Google Sheets!")
                    else:
                        confirm_text = (
                            f"🎉 **Banking Information Recorded!**\n"
                            f"- **Order ID:** {active_ord.get('order_id')}\n"
                            f"- **Bank:** {in_bank}\n"
                            f"- **Account:** {in_acc}\n"
                            f"- **Mobile:** {in_mob}\n\n"
                            f"⚠️ **Note for Google Sheets Sync:** Your details are saved securely, but could not be written to the Google Sheet because `{sa_email}` has 'Viewer' access. "
                            f"Please grant **Editor** access to `{sa_email}` in Google Sheets Share settings."
                        )
                        st.warning(f"⚠️ Saved locally. Grant 'Editor' access to `{sa_email}` in Google Sheets to sync to cloud.")

                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": confirm_text,
                        "sources": []
                    })
                    st.session_state["active_refund_order"] = None
                    st.rerun()
                else:
                    st.warning("Please fill in all three fields: Bank Name, Account Number, and Mobile Number.")

    # Chat Input Box
    user_prompt = st.chat_input("Ask Charlie about products, refund eligibility (e.g. ORD-101), or enter bank details...")
    active_prompt = preset_query or user_prompt

    if active_prompt:
        if not active_api_key:
            st.error("🔑 Please provide a Google Gemini API Key in the left sidebar to activate Charlie.", icon="🚨")
        else:
            # 1. Add user message
            st.session_state["messages"].append({
                "role": "user",
                "content": active_prompt
            })
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(active_prompt)

            # 2. Assistant response
            with st.chat_message("assistant", avatar="🛍️"):
                history_payload = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["messages"][:-1]
                ]

                try:
                    vectorstore, _ = get_cached_vs(active_api_key)
                    llm = get_cached_llm(
                        api_key=active_api_key,
                        model_name=model_choice,
                        temperature=temperature
                    )

                    if use_streaming:
                        stream_res = stream_answer_query(
                            query=active_prompt,
                            vectorstore=vectorstore,
                            llm=llm,
                            chat_history=history_payload,
                            k=top_k,
                            active_order=st.session_state.get("active_refund_order")
                        )
                        retrieved_docs = stream_res[0]
                        token_gen = stream_res[1]
                        matched_order = stream_res[2] if len(stream_res) > 2 else None
                        refund_eval = stream_res[3] if len(stream_res) > 3 else None
                        new_order = stream_res[4] if len(stream_res) > 4 else None

                        # Stream response
                        response_text = st.write_stream(token_gen)
                        sources_to_save = [
                            {"page_content": d.page_content, "metadata": d.metadata}
                            for d in retrieved_docs
                        ]
                    else:
                        with st.spinner("Charlie is consulting ChromaDB and Google Sheets..."):
                            rag_result = answer_query(
                                query=active_prompt,
                                vectorstore=vectorstore,
                                llm=llm,
                                chat_history=history_payload,
                                k=top_k,
                                active_order=st.session_state.get("active_refund_order")
                            )
                            response_text = rag_result["answer"]
                            matched_order = rag_result.get("matched_order")
                            refund_eval = rag_result.get("refund_eval")
                            new_order = rag_result.get("new_order")
                            st.markdown(response_text)
                            sources_to_save = [
                                {"page_content": d.page_content, "metadata": d.metadata}
                                for d in rag_result["source_documents"]
                            ]

                    if new_order:
                        st.toast(f"🎉 New Order {new_order.get('order_id')} placed for {new_order.get('customer')} ({new_order.get('model_name')}) in Google Sheets!", icon="🛍️")

                    # Track active refund order in session state
                    if refund_eval and refund_eval.get("eligible"):
                        st.session_state["active_refund_order"] = refund_eval

                    # Show sources accordion immediately if enabled in settings
                    if show_sources and sources_to_save:
                        with st.expander(f"🔍 Grounded Knowledge Sources ({len(sources_to_save)} chunks retrieved)", expanded=False):
                            for s_idx, doc in enumerate(sources_to_save):
                                meta = doc["metadata"]
                                content = doc["page_content"]
                                doc_type = meta.get("doc_type", "document").upper()
                                source_file = meta.get("source", "knowledge_base")
                                badge_color = "#059669" if doc_type == "PRODUCT" else "#2563eb"

                                st.markdown(f"""
                                <div class="source-card">
                                    <div class="source-header">
                                        <span style="background: {badge_color}; color: #ffffff; padding: 2px 6px; border-radius: 4px;">{doc_type}</span>
                                        <span>Source: {source_file}</span>
                                        {f"<span>· Brand: {meta.get('brand')}</span>" if 'brand' in meta else ""}
                                        {f"<span>· Model: {meta.get('model')}</span>" if 'model' in meta else ""}
                                    </div>
                                    <div style="color: #3f3f46; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; white-space: pre-wrap; line-height: 1.4;">
{content.strip()}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                    # Append assistant message with sources to state
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": response_text,
                        "sources": sources_to_save
                    })

                except Exception as ex:
                    err_msg = f"❌ Error querying agent pipeline: {ex}"
                    st.error(err_msg)
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": err_msg,
                        "sources": []
                    })


# ---------------------------------------------------------
# TAB 2: Orders & Refunds Agent (Google Sheets)
# ---------------------------------------------------------
with tab_refund:
    st.markdown("### 🛒 Orders & Refunds Management Agent")
    st.caption("Directly connected to Google Sheets: Takes new customer orders, evaluates refund eligibility, and records banking information.")

    # Refresh Button
    r_col1, r_col2 = st.columns([4, 1])
    with r_col2:
        if st.button("🔄 Refresh Sheets Data", use_container_width=True):
            st.rerun()

    orders_list = sheets_service.fetch_orders()
    df_orders = pd.DataFrame(orders_list)
    if "_row_number" in df_orders.columns:
        df_orders = df_orders.drop(columns=["_row_number"])

    st.markdown("#### 📋 Live Orders Database (`Sheet1`)")
    st.dataframe(df_orders, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### 🛍️ Step 1: Place a New Customer Order (Add to Google Sheet)")
    with st.expander("➕ **Click to Create and Register a New Customer Order**", expanded=False):
        st.write("Fill in customer name and choose a product from the live catalog to immediately append an order into Google Sheets:")

        prod_df = sheets_service.fetch_products_dataframe()
        prod_options = []
        if prod_df is not None and not prod_df.empty:
            for _, r in prod_df.iterrows():
                brand = str(r.get("Brand", ""))
                model = str(r.get("Model Name", ""))
                price = float(r.get("price", 0.0))
                stock = int(r.get("stock", 0)) if pd.notna(r.get("stock")) else 0
                prod_options.append(f"{brand} {model} — ${price:.2f} ({stock} available)")

        with st.form("form_create_new_order_tab2"):
            fo_c1, fo_c2 = st.columns(2)
            with fo_c1:
                in_cust_name = st.text_input("Customer Name", placeholder="e.g. Hamza, Bilal, Sarah", key="tab2_cust_name")
            with fo_c2:
                in_sel_prod = st.selectbox("Select Product Model", prod_options, key="tab2_sel_prod")

            btn_create_order = st.form_submit_button("🚀 Submit Order to Google Sheet", use_container_width=True)
            if btn_create_order:
                if not in_cust_name or not in_cust_name.strip():
                    st.error("Please enter a customer name.")
                elif not in_sel_prod:
                    st.error("Please select a product.")
                else:
                    raw_model = in_sel_prod.split(" — ")[0].strip()
                    with st.spinner("Submitting order to Google Sheets..."):
                        c_res = sheets_service.create_new_order(
                            customer=in_cust_name.strip(),
                            model_name=raw_model
                        )
                        st.success(f"🎉 New Order **{c_res['order_id']}** created for **{c_res['customer']}** ({c_res['model_name']})!")
                        if c_res.get("sheet_synced"):
                            st.info("☁️ Appended directly to live Google Sheet (`orders` Sheet1).")
                        st.rerun()

    st.markdown("---")
    st.markdown("#### ⚖️ Step 2: Evaluate Refund Eligibility")

    order_choices = [f"{o.get('order_id')} — {o.get('customer')} ({o.get('Model Name')})" for o in orders_list]
    selected_order_str = st.selectbox("Select an Order to Inspect:", order_choices)

    if selected_order_str:
        sel_oid = selected_order_str.split(" — ")[0].strip()
        selected_order = sheets_service.find_order(sel_oid)

        if selected_order:
            eval_res = sheets_service.evaluate_refund_eligibility(selected_order)

            # Render Eligibility Card
            if eval_res["eligible"]:
                st.markdown(f"""
                <div class="eligible-box">
                    <h3 style="margin: 0 0 8px 0; color: #047857;">✅ ELIGIBLE FOR REFUND</h3>
                    <p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">
                        <strong>Order ID:</strong> {eval_res['order_id']} &nbsp;|&nbsp;
                        <strong>Customer:</strong> {eval_res['customer']} &nbsp;|&nbsp;
                        <strong>Product:</strong> {eval_res['model_name']} &nbsp;|&nbsp;
                        <strong>Current Status:</strong> {eval_res['status'] or 'Pending'}
                    </p>
                    <p style="margin: 8px 0 0 0; font-size: 0.88rem;">
                        <strong>Policy Assessment:</strong> Purchased <strong>{eval_res['days_ago']} days ago</strong>,
                        which is within the allowed <strong>{eval_res['allowed_days']}-day return window</strong> for {eval_res['item_type']}.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### 💳 Step 2: Take Banking Information")
                st.write("Since this order is eligible, please enter customer banking details below to disburse the refund:")

                with st.form("tab_bank_details_form"):
                    f_c1, f_c2 = st.columns(2)
                    with f_c1:
                        f_bank = st.text_input("Bank Name", placeholder="e.g. Meezan Bank, Chase, HBL, Bank of America")
                        f_acc = st.text_input("Account Number / IBAN", placeholder="e.g. 9876543210")
                    with f_c2:
                        f_mob = st.text_input("Mobile / Contact Number", placeholder="e.g. 03001234567")
                        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
                        submit_btn = st.form_submit_button("🚀 Submit to Bank Details Sheet", use_container_width=True)

                    if submit_btn:
                        if not f_bank or not f_acc or not f_mob:
                            st.error("Please fill in all banking fields before submitting.")
                        else:
                            with st.spinner("Submitting to Google Sheets..."):
                                sub_result = sheets_service.submit_bank_details(
                                    order_id=eval_res["order_id"],
                                    customer=eval_res["customer"],
                                    product=eval_res["model_name"],
                                    bank_name=f_bank,
                                    account_number=f_acc,
                                    mobile_number=f_mob
                                )
                                st.success(f"🎉 Banking information recorded for Order {eval_res['order_id']}!")
                                if sub_result.get("sheet_synced"):
                                    st.info("☁️ Successfully synced to live Google Sheet (`Bank_details` Sheet1).")
                                else:
                                    st.warning("⚠️ " + str(sub_result.get("notice", "Recorded locally.")))
                                st.rerun()

            else:
                st.markdown(f"""
                <div class="ineligible-box">
                    <h3 style="margin: 0 0 8px 0; color: #b91c1c;">❌ NOT ELIGIBLE FOR REFUND</h3>
                    <p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">
                        <strong>Order ID:</strong> {eval_res['order_id']} &nbsp;|&nbsp;
                        <strong>Customer:</strong> {eval_res['customer']} &nbsp;|&nbsp;
                        <strong>Product:</strong> {eval_res['model_name']} &nbsp;|&nbsp;
                        <strong>Current Status:</strong> {eval_res['status'] or 'Pending'}
                    </p>
                    <p style="margin: 8px 0 0 0; font-size: 0.88rem;">
                        <strong>Policy Assessment:</strong> Purchased <strong>{eval_res['days_ago']} days ago</strong>,
                        which exceeds the allowed <strong>{eval_res['allowed_days']}-day return window</strong> for {eval_res['item_type']}.
                        Returns cannot be processed.
                    </p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🏦 Live Bank Details Database (`Bank_details` Sheet)")

    pending_banks = sheets_service.get_pending_bank_details()
    sa_email = sheets_service.get_service_account_email()

    if pending_banks:
        st.warning(
            f"⚠️ **Google Sheets Write Permission Notice ({len(pending_banks)} pending submission(s))**:\n\n"
            f"The Google Service Account (`{sa_email}`) currently only has **Viewer** permission on your Google Sheet. "
            f"Google Sheets API returns `HTTP 403: PERMISSION_DENIED` until you grant **Editor** access.\n\n"
            f"**To sync rows automatically to Google Sheets:**\n"
            f"1. Open your [Bank Details Sheet](https://docs.google.com/spreadsheets/d/1gWgVsSVU4u1V8qTcEIKj7F81XxY02Y-0sJCdc-J6gNg/edit?gid=0#gid=0) and [Orders Sheet](https://docs.google.com/spreadsheets/d/18G2BQlwSihkgC5JcCFosbMVEbSQBQE_hgvKpFogcWCI/edit?gid=1288216522#gid=1288216522)\n"
            f"2. Click the green **Share** button (top-right)\n"
            f"3. Change `{sa_email}` from **Viewer** to **Editor** and click **Save**\n"
            f"4. Click the button below to immediately push all pending records into your Google Sheet!"
        )
        if st.button("🚀 Push All Pending Submissions to Google Sheets Now", key="btn_push_pending_sheets", use_container_width=True):
            with st.spinner("Pushing records to Google Sheets..."):
                sync_result = sheets_service.sync_pending_bank_details()
                if sync_result.get("synced", 0) > 0:
                    st.success(f"🎉 Successfully synced {sync_result['synced']} record(s) directly to your Google Sheet!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to sync: {sync_result.get('error')}")

    bank_records = sheets_service.fetch_bank_details()
    if bank_records:
        df_bank = pd.DataFrame(bank_records)
        if "_cloud_synced" in df_bank.columns:
            df_bank["Cloud Synced"] = df_bank["_cloud_synced"].apply(lambda x: "✅ Synced to Sheet" if x else "⏳ Local (Awaiting Editor Role)")
            df_bank = df_bank.drop(columns=["_cloud_synced"])
        st.dataframe(df_bank, use_container_width=True, hide_index=True)
    else:
        st.info("No bank details submitted yet.")


# ---------------------------------------------------------
# TAB 3: Product Catalog Explorer (Live Google Sheets)
# ---------------------------------------------------------
with tab_catalog:
    st.markdown("### 📦 TechMart Product Catalog (Live Google Sheets)")
    st.caption("Real-time inventory and pricing loaded directly from Google Sheets (`1RZ1U4TKfqqjY4kpbvFUQOJd_PwDlYp0I`).")

    try:
        _, df_prod = load_all_cached_data()

        # Search & Filter Controls
        f_row1, f_row2 = st.columns([3, 2])
        with f_row1:
            search_term = st.text_input("🔍 Search Catalog (Name, Specs, or Best For)", placeholder="e.g. OLED, Noise Cancelling, MacBook, 32GB...")
        with f_row2:
            sort_option = st.selectbox(
                "Sort Products By",
                ["Featured", "Price: Low to High", "Price: High to Low", "Stock: Highest First", "Name (A-Z)"]
            )

        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 1.5])
        with f_col1:
            categories = ["All Categories"] + sorted(list(df_prod["Category"].dropna().unique()))
            selected_cat = st.selectbox("Category", categories)
        with f_col2:
            brands = ["All Brands"] + sorted(list(df_prod["Brand"].dropna().unique()))
            selected_brand = st.selectbox("Brand", brands)
        with f_col3:
            max_catalog_price = float(df_prod["price"].max())
            price_limit = st.slider("Max Price ($)", min_value=10.0, max_value=max_catalog_price, value=max_catalog_price, step=50.0)
        with f_col4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            in_stock_filter = st.checkbox("In Stock Only", value=False)

        # Filtering Logic
        filtered_df = df_prod.copy()
        if selected_cat != "All Categories":
            filtered_df = filtered_df[filtered_df["Category"] == selected_cat]
        if selected_brand != "All Brands":
            filtered_df = filtered_df[filtered_df["Brand"] == selected_brand]
        if in_stock_filter:
            filtered_df = filtered_df[filtered_df["stock"] > 0]
        filtered_df = filtered_df[filtered_df["price"] <= price_limit]

        if search_term:
            term = search_term.lower()
            filtered_df = filtered_df[
                filtered_df["Model Name"].astype(str).str.lower().str.contains(term) |
                filtered_df["Key Specifications"].astype(str).str.lower().str.contains(term) |
                filtered_df["Best For"].astype(str).str.lower().str.contains(term) |
                filtered_df["Brand"].astype(str).str.lower().str.contains(term)
            ]

        # Sorting Logic
        if sort_option == "Price: Low to High":
            filtered_df = filtered_df.sort_values(by="price", ascending=True)
        elif sort_option == "Price: High to Low":
            filtered_df = filtered_df.sort_values(by="price", ascending=False)
        elif sort_option == "Stock: Highest First":
            filtered_df = filtered_df.sort_values(by="stock", ascending=False)
        elif sort_option == "Name (A-Z)":
            filtered_df = filtered_df.sort_values(by="Model Name", ascending=True)

        st.caption(f"Showing **{len(filtered_df)}** of **{len(df_prod)}** live products from Google Sheets")

        # Render Product Grid
        if len(filtered_df) == 0:
            st.info("No products match your selected filters. Try broadening your criteria.")
        else:
            cols = st.columns(3)
            for idx, (_, row) in enumerate(filtered_df.iterrows()):
                col_target = cols[idx % 3]
                stock_count = int(row["stock"]) if pd.notna(row["stock"]) else 0
                is_in_stock = stock_count > 0

                with col_target:
                    stock_html = f"<span class='stock-badge-in'>● {stock_count} In Stock</span>" if is_in_stock else "<span class='stock-badge-out'>● Out of Stock</span>"

                    st.markdown(f"""
                    <div class="product-card">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span class="badge-category">{row['Category']}</span>
                                <span style="font-size: 0.75rem; font-weight: 700; color: #71717a;">{row['Brand']}</span>
                            </div>
                            <div class="product-title">{row['Model Name']}</div>
                            <div class="product-specs">
                                <strong>Specs:</strong> {row['Key Specifications']}
                            </div>
                            <div class="product-bestfor">
                                🎯 <strong>Best For:</strong> {row['Best For']}
                            </div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e4e4e7; padding-top: 12px; margin-top: 8px;">
                                <span class="price-tag">${row['price']:.2f}</span>
                                {stock_html}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Quick Inquire Button
                    if st.button(f"💬 Ask Charlie about this", key=f"ask_prod_{idx}", use_container_width=True):
                        st.session_state["pending_query"] = f"Tell me more about the {row['Brand']} {row['Model Name']}. What are its specs, price, and current stock status?"
                        st.rerun()

                    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading product catalog from Google Sheets: {e}")


# ---------------------------------------------------------
# TAB 4: Store Policies & FAQ
# ---------------------------------------------------------
with tab_policies:
    st.markdown("### 📜 TechMart Store Policies & Direct Support")
    st.caption("Official store policy clauses referenced by Charlie to evaluate refund eligibility and answer questions.")

    # Quick Policy Highlights Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="quick-chip">
            <div class="quick-chip-val">30 Days</div>
            <div class="quick-chip-lbl">General Returns</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="quick-chip">
            <div class="quick-chip-val" style="color: #2563eb;">15 Days</div>
            <div class="quick-chip-lbl">Electronics Return</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="quick-chip">
            <div class="quick-chip-val" style="color: #059669;">Free @ $50+</div>
            <div class="quick-chip-lbl">Standard Shipping</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="quick-chip">
            <div class="quick-chip-val" style="color: #7c3aed;">1 Year</div>
            <div class="quick-chip-lbl">Hardware Warranty</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    policy_search = st.text_input("🔍 Search Policies", placeholder="e.g. refund, restocking fee, express shipping, warranty...")

    try:
        policy_chunks, _ = load_all_cached_data()

        matching_chunks = []
        for i, chunk in enumerate(policy_chunks):
            text = chunk.page_content
            if not policy_search or policy_search.lower() in text.lower():
                matching_chunks.append((i, text))

        if not matching_chunks:
            st.info("No policy clauses match your search.")
        else:
            for i, text in matching_chunks:
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                title = lines[0] if lines else f"Policy Section {i+1}"
                body = "\n\n".join(lines[1:]) if len(lines) > 1 else lines[0]

                with st.expander(f"📌 {title}", expanded=(i == 0 or bool(policy_search))):
                    st.markdown(body)

        st.markdown("---")
        st.markdown("""
        ### 📞 Customer Support Channels
        - 📧 **Email**: `support@techmart.com` (Replies within 24 hours)
        - ☎️ **Toll-Free Phone**: `1-800-TECHMART` (Mon–Fri, 9:00 AM – 6:00 PM EST)
        - 💬 **Live Chat**: Available 24/7 via Charlie right here in the web app.
        """)

    except Exception as e:
        st.error(f"Error loading policies: {e}")
