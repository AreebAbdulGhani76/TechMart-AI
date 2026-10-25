# 🛍️ TechMart Autonomous AI Support & Store Operations Agent

An enterprise-grade, full-stack AI Support & Store Operations dashboard built with **Next.js 15 (App Router)**, **TypeScript**, **Google Gemini**, and live **Google Sheets API** integration, alongside an optional **Streamlit** Python interface.

The AI assistant (**Charlie**) operates as an autonomous e-commerce support specialist that:
1. **Answers Sales & Policy Inquiries**: Recommends products, checks real-time specifications and live stock, and grounds answers in company policies extracted from the official Word document (`policy.docx`).
2. **Takes Orders Live**: Automatically captures customer order requests, validates inventory, and records new orders in the live Google Sheets database.
3. **Evaluates Refund Eligibility**: Inspects live orders from Google Sheets and enforces return window policies (15 days for electronics, 30 days for general items).
4. **Collects & Records Banking Details**: Securely captures customer Bank Name, Account/IBAN Number, and Mobile Number for eligible refunds and writes them directly to Google Sheets.

---

## ☁️ Live Google Sheets Integration

Data is queried and updated **live in real time** via Google Service Account authentication:
- **Products Catalog**: Live pricing, categories, and inventory stock
- **Orders Database**: Live order lookup and new order booking
- **Bank Details Database**: Secure refund disbursement logging

---

## ⚙️ Environment Configuration (`.env`)

Before running or deploying the application, configure your credentials in `.env`. See `.env.example` for reference:

```env
# 1. Google Gemini API Key
# Get a free key at: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_gemini_api_key_here

# 2. Google Service Account Credentials File Path
# Place your service account JSON file in the project root and reference it here
GOOGLE_APPLICATION_CREDENTIALS=leads-data-serviceaccount.json

# Optional: Directly provide the Service Account JSON string for cloud deployment (Vercel, Railway, etc.)
# GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}

# 3. Google Sheets IDs & GIDs
PRODUCTS_SHEET_ID=1RZ1U4TKfqqjY4kpbvFUQOJd_PwDlYp0I
PRODUCTS_GID=1097220337

ORDERS_SHEET_ID=18G2BQlwSihkgC5JcCFosbMVEbSQBQE_hgvKpFogcWCI
ORDERS_GID=1288216522

BANK_DETAILS_SHEET_ID=1gWgVsSVU4u1V8qTcEIKj7F81XxY02Y-0sJCdc-J6gNg
BANK_DETAILS_GID=0
```

> [!IMPORTANT]
> All credentials, keys, and secret service account files are strictly excluded from git tracking via `.gitignore`. Never commit `.env` or Service Account JSON files to version control.

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- (Optional for Python interface) Python 3.10+

### Next.js Web Application (Recommended)

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment**:
   Copy `.env.example` to `.env` and insert your API keys and credentials:
   ```bash
   cp .env.example .env
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

4. **Build for production**:
   ```bash
   npm run build
   npm run start
   ```

### Python / Streamlit Application (Alternative)

1. Activate virtual environment and install requirements:
   ```bash
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run Streamlit app:
   ```bash
   streamlit run app.py
   ```
   Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📁 Repository Structure

```
├── app/
│   ├── api/
│   │   ├── chat/route.ts       # Streaming AI agent route with function routing
│   │   ├── orders/route.ts     # Live order fetching and order placement
│   │   ├── policy/route.ts     # Word docx policy extraction and metadata
│   │   ├── products/route.ts   # Live Google Sheets catalog endpoint
│   │   └── refund/route.ts     # Refund eligibility check & bank submission
│   ├── globals.css             # Enterprise dark SaaS design system
│   ├── layout.tsx              # Root HTML and metadata layout
│   └── page.tsx                # Interactive multi-tab SaaS dashboard
├── lib/
│   ├── gemini.ts               # Google Gemini client and autonomous agent logic
│   ├── policy.ts               # Mammoth-powered Word (.docx) policy extractor
│   └── sheets.ts               # Google Sheets API connector (JWT authentication)
├── policy.docx                 # Official TechMart company policies document
├── sheets_service.py           # Python Google Sheets connector
├── rag_engine.py               # Python RAG & LangChain agent core
├── app.py                      # Python Streamlit interface
├── .env.example                # Environment configuration template
└── .gitignore                  # Security-first ignore rules
```

---

## 🛡️ Security & Privacy

- All sensitive credentials (`.env`, service account JSON keys, backup files) are excluded via `.gitignore`.
- Next.js API routes run strictly server-side, protecting your Gemini API key and Google Cloud credentials from client exposure.
- Real-time rate limiting, sanitization, and error boundaries prevent credential leakage.
