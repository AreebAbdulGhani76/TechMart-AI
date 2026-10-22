"""
TechMart AI Assistant — Enterprise Streamlit RAG Application
Grounds Google Gemini LLM in real-time product catalogs and store policies via ChromaDB.
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


# Import RAG engine functions
from rag_engine import (
    prepare_all_documents,
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
    page_title="TechMart AI Assistant | RAG Platform",
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
    padding-top: 1.8rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* Header Banner */
.hero-banner {
    background: linear-gradient(135deg, #09090b 0%, #18181b 100%);
    border: 1px solid #27272a;
    border-radius: 16px;
    padding: 26px 32px;
    margin-bottom: 24px;
    color: #ffffff;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
}

.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.18);
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
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0 0 6px 0;
    color: #ffffff;
}

.hero-subtitle {
    font-size: 0.95rem;
    color: #a1a1aa;
    margin: 0;
    max-width: 720px;
    line-height: 1.5;
}

/* Stat Cards */
.stat-card {
    background: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px -2px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.08);
    border-color: #09090b;
}

.stat-val {
    font-size: 1.85rem;
    font-weight: 800;
    color: #09090b;
    line-height: 1.2;
}

.stat-label {
    font-size: 0.76rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #71717a;
    margin-top: 4px;
}

/* Product Cards */
.product-card {
    background: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 14px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 290px;
    box-shadow: 0 2px 8px -2px rgba(0, 0, 0, 0.04);
    transition: all 0.2s ease-in-out;
}

.product-card:hover {
    border-color: #09090b;
    box-shadow: 0 10px 24px -6px rgba(0, 0, 0, 0.1);
    transform: translateY(-3px);
}

.badge-category {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: #f4f4f5;
    color: #18181b;
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid #e4e4e7;
}

.product-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #09090b;
    margin: 8px 0 6px 0;
}

.product-specs {
    font-size: 0.83rem;
    color: #52525b;
    line-height: 1.45;
    margin-bottom: 8px;
}

.product-bestfor {
    font-size: 0.8rem;
    color: #71717a;
    margin-bottom: 12px;
}

.price-tag {
    font-size: 1.25rem;
    font-weight: 800;
    color: #09090b;
}

.stock-badge-in {
    font-size: 0.78rem;
    font-weight: 700;
    color: #059669;
    background: #ecfdf5;
    padding: 3px 8px;
    border-radius: 9999px;
    border: 1px solid #a7f3d0;
}

.stock-badge-out {
    font-size: 0.78rem;
    font-weight: 700;
    color: #dc2626;
    background: #fef2f2;
    padding: 3px 8px;
    border-radius: 9999px;
    border: 1px solid #fecaca;
}

/* Source Reference Card */
.source-card {
    background: #fafafa;
    border: 1px solid #e4e4e7;
    border-left: 3px solid #09090b;
    border-radius: 8px;
    padding: 12px 14px;
    margin-top: 6px;
    margin-bottom: 6px;
    font-size: 0.84rem;
}

.source-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 700;
    font-size: 0.78rem;
    text-transform: uppercase;
    color: #09090b;
    margin-bottom: 4px;
}

/* Policy Card */
.policy-card {
    background: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 14px;
}

.policy-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #09090b;
    margin-bottom: 8px;
}

.policy-body {
    font-size: 0.9rem;
    color: #3f3f46;
    line-height: 1.6;
}

/* Quick Reference Chips */
.quick-chip {
    background: #ffffff;
    border: 1px solid #e4e4e7;
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
    color: #71717a;
    font-weight: 600;
    text-transform: uppercase;
    margin-top: 2px;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: #d4d4d8;
    border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
    background: #a1a1aa;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------
# Cached Resource Loaders
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_all_cached_data():
    """Caches document and DataFrame loading to make app instant."""
    policy_chunks, product_docs, all_docs, df_products = prepare_all_documents()
    return policy_chunks, product_docs, all_docs, df_products


def get_cached_vs(api_key: str, force_rebuild: bool = False):
    """Initializes or loads Chroma vectorstore with caching."""
    return get_vectorstore(
        api_key=api_key,
        persist_directory=DEFAULT_CHROMA_DIR,
        force_rebuild=force_rebuild
    )


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
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]
    model_choice = st.selectbox(
        "Gemini Model",
        options=model_options,
        index=0,
        help="Gemini 3.5 Flash is selected by default for fast, grounded RAG responses."
    )

    use_streaming = st.toggle("⚡ Real-time Token Streaming", value=True, help="Stream answers word-by-word.")

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
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
    st.markdown("### 🗄️ Knowledge Base Telemetry")

    try:
        policy_chunks, product_docs, all_docs, df_products = load_all_cached_data()
        in_stock_count = int((df_products["stock"] > 0).sum()) if df_products is not None else 0

        st.markdown(f"""
        - 📦 **Products in Catalog**: `{len(df_products)}`
        - 🟢 **In-Stock SKUs**: `{in_stock_count}`
        - 📜 **Policy Clauses**: `{len(policy_chunks)} chunks`
        - 📚 **Total Embeddings**: `{len(all_docs)} items`
        - 🏷️ **Collection**: `{COLLECTION_NAME}`
        """)
    except Exception as e:
        st.error(f"Error loading telemetry: {e}")

    # Reindex Vector Database Action
    if active_api_key:
        if st.button("🔄 Sync / Rebuild ChromaDB", use_container_width=True, help="Force re-embed and index all documents"):
            with st.spinner("Re-indexing documents into ChromaDB..."):
                try:
                    vs, count = get_cached_vs(active_api_key, force_rebuild=True)
                    st.success(f"Indexed {count} documents into ChromaDB!")
                except Exception as ex:
                    st.error(f"Failed to rebuild index: {ex}")

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()


# ---------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <div class="hero-pill">⚡ TechMart Enterprise RAG Platform</div>
    <h1 class="hero-title">AI Sales & Policy Assistant</h1>
    <p class="hero-subtitle">
        Grounding intelligent customer interactions in live catalog specifications, real-time stock levels,
        and official company policies using ChromaDB dense vector retrieval and Google Gemini.
    </p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Key Performance Metrics Row
# ---------------------------------------------------------
try:
    policy_chunks, product_docs, all_docs, df_products = load_all_cached_data()
    m1, m2, m3, m4 = st.columns(4)

    total_prods = len(df_products)
    in_stock_total = int((df_products["stock"] > 0).sum())
    total_clauses = len(policy_chunks)

    with m1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val">{total_prods}</div>
            <div class="stat-label">Total Products</div>
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
            <div class="stat-val" style="color: #2563eb;">{total_clauses}</div>
            <div class="stat-label">Policy Clauses</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color: #7c3aed;">Chroma</div>
            <div class="stat-label">Vector Store</div>
        </div>
        """, unsafe_allow_html=True)

except Exception:
    pass

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Tabbed Navigation
# ---------------------------------------------------------
tab_chat, tab_catalog, tab_policies = st.tabs([
    "💬 Chat with Charlie (AI Assistant)",
    "📦 Product Catalog Explorer",
    "📜 Store Policies & FAQ"
])

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I'm **Charlie**, your TechMart sales and customer support specialist.\n\n"
                "I can help you check real-time product availability, compare specifications, find recommendations, "
                "or answer questions regarding our **return policy**, **shipping options**, and **warranties**.\n\n"
                "What can I help you find today?"
            ),
            "sources": []
        }
    ]


# ---------------------------------------------------------
# TAB 1: Chat Interface
# ---------------------------------------------------------
with tab_chat:
    # Quick Suggestion Chips
    st.markdown("**💡 Quick Inquiries:**")
    q1, q2, q3, q4 = st.columns(4)

    preset_query = None
    with q1:
        if st.button("💻 Student laptops under $1,000", key="chip_q1", use_container_width=True):
            preset_query = "What laptops do you recommend for students under $1000 and are they currently in stock?"
    with q2:
        if st.button("🔄 Return policy for laptops", key="chip_q2", use_container_width=True):
            preset_query = "What is the return policy for electronics like laptops and tablets? How many days do I have?"
    with q3:
        if st.button("🎧 Noise cancelling headphones", key="chip_q3", use_container_width=True):
            preset_query = "What noise-cancelling headphones do you carry, what are their prices, and are they in stock?"
    with q4:
        if st.button("🚚 Free shipping requirements", key="chip_q4", use_container_width=True):
            preset_query = "How much do I need to spend for free shipping, and how long does standard delivery take?"

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

            # Render Grounded Sources if available
            sources = msg.get("sources", [])
            if sources and not is_user:
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
                                {f"<span>· Section: {meta.get('section')}</span>" if 'section' in meta else ""}
                            </div>
                            <div style="color: #3f3f46; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; white-space: pre-wrap; line-height: 1.4;">
{content.strip()}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # Chat Input Box
    user_prompt = st.chat_input("Ask Charlie about products, specs, stock availability, or policies...")
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
                    llm = get_llm(
                        api_key=active_api_key,
                        model_name=model_choice,
                        temperature=temperature
                    )

                    if use_streaming:
                        retrieved_docs, token_gen = stream_answer_query(
                            query=active_prompt,
                            vectorstore=vectorstore,
                            llm=llm,
                            chat_history=history_payload,
                            k=top_k
                        )
                        # Stream response
                        response_text = st.write_stream(token_gen)
                        sources_to_save = [
                            {"page_content": d.page_content, "metadata": d.metadata}
                            for d in retrieved_docs
                        ]
                    else:
                        with st.spinner("Charlie is consulting ChromaDB and Gemini..."):
                            rag_result = answer_query(
                                query=active_prompt,
                                vectorstore=vectorstore,
                                llm=llm,
                                chat_history=history_payload,
                                k=top_k
                            )
                            response_text = rag_result["answer"]
                            st.markdown(response_text)
                            sources_to_save = [
                                {"page_content": d.page_content, "metadata": d.metadata}
                                for d in rag_result["source_documents"]
                            ]

                    # Show sources accordion immediately
                    if sources_to_save:
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
                    err_msg = f"❌ Error querying RAG pipeline: {ex}"
                    st.error(err_msg)
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": err_msg,
                        "sources": []
                    })


# ---------------------------------------------------------
# TAB 2: Product Catalog Explorer
# ---------------------------------------------------------
with tab_catalog:
    st.markdown("### 📦 TechMart Product Catalog Explorer")
    st.caption("Live catalog data loaded directly from `products.xlsx` and indexed as semantic vectors.")

    try:
        _, _, _, df_prod = load_all_cached_data()

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

        st.caption(f"Showing **{len(filtered_df)}** of **{len(df_prod)}** products")

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
        st.error(f"Error loading product catalog: {e}")


# ---------------------------------------------------------
# TAB 3: Store Policies & FAQ
# ---------------------------------------------------------
with tab_policies:
    st.markdown("### 📜 TechMart Store Policies & Direct Support")
    st.caption("Indexed clauses extracted from `policy.txt` and referenced by Charlie during customer inquiries.")

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
        policy_chunks, _, _, _ = load_all_cached_data()

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
