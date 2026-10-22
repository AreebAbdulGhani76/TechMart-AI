# 🛍️ TechMart AI Sales & Policy RAG Chatbot

An end-to-end Retrieval-Augmented Generation (RAG) system and interactive **Streamlit** web application powered by **Google Gemini** (`gemini-2.5-flash`, `models/gemini-embedding-2`) and **ChromaDB**.

The assistant (**Charlie**) helps customers explore products, compare specifications, verify real-time pricing and stock status, and clarify company policies on returns, refunds, shipping, warranties, and support.

---

## 📁 Project Architecture

- **`policy.txt`**: Unstructured store policy document (Return, Refund, Shipping, Warranty, Exchange, Customer Support).
- **`products.xlsx`**: E-commerce catalog containing Category, Brand, Model Name, Key Specifications, Best For, Price, and Stock.
- **`rag_engine.py`**: Modular RAG core handling document ingestion, chunking, ChromaDB vector indexing, and Gemini conversational chain with streaming.
- **`app.py`**: Premium Streamlit web application with multi-tab layout, real-time token streaming, source inspection, and product catalog explorer.
- **`run_app.bat`**: One-click startup script launching the Streamlit application.
- **`RAG_Chatbot.ipynb`**: Complete, self-contained Jupyter Notebook detailing each RAG step from chunking to generation.
- **`.env.example`**: Environment variable template for the Google Gemini API key.
- **`requirements.txt`**: Pinned dependency list.

---

## 🚀 Quickstart

### 1. Configure Your Gemini API Key
Obtain a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```
*(You can also enter your API key directly in the Streamlit sidebar settings.)*

### 2. Launch the Application
Double-click `run_app.bat` or run:
```bash
.\run_app.bat
```
Alternatively, run with python virtual environment:
```bash
.\.venv\Scripts\streamlit run app.py
```
Open your browser at **`http://localhost:8501`**.

---

## 💡 RAG Design Highlights

1. **Hybrid Data Chunking Strategy**:
   - **`policy.txt`**: Chunked with `RecursiveCharacterTextSplitter` (`chunk_size=400`, `chunk_overlap=60`) using paragraph and sentence separators to keep policy provisions coherent.
   - **`products.xlsx`**: Tabular rows are transformed into individual semantic text documents with labeled attributes and rich metadata (`brand`, `category`, `price`, `stock`, `in_stock`) for hybrid filtering.
2. **Embeddings & Vector Database**:
   - Uses Google's `models/gemini-embedding-2` to generate dense vector embeddings.
   - Persists vectors locally in `./chroma_db` using **ChromaDB**.
3. **Conversational Assistant (Charlie)**:
   - Grounded in retrieved store context to eliminate hallucinations.
   - Real-time token streaming for instantaneous response rendering.
   - Displays expandable source citations showing exact chunks from ChromaDB.
4. **Interactive Explorer Tabs**:
   - Full-text search and multi-filtering across categories, brands, price, and stock.
   - Searchable policy knowledge base with quick reference highlights.
