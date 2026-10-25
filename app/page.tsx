'use client';

import React, { useState, useEffect, useRef } from 'react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  orderInfo?: {
    order_id: string;
    customer: string;
    model_name: string;
    price: number;
    status: string;
  };
}

interface Product {
  Category: string;
  Brand: string;
  'Model Name': string;
  'Key Specifications': string;
  'Best For': string;
  price: number;
  stock: number;
}

interface Order {
  order_id: string;
  customer: string;
  'Model Name': string;
  product: string;
  category: string;
  days_ago: string | number;
  Status: string;
}

interface BankDetail {
  order_id: string;
  customer: string;
  product: string;
  Bank_Name: string;
  'Account Number': string;
  'Mobile Number': string;
}

interface PolicySection {
  title: string;
  content: string;
}

// Markdown Formatter Helpers
function renderFormattedInline(text: string): React.ReactNode[] {
  // Matches code blocks, inline code, bold-italic, bold, italic, or order IDs
  const regex = /(```[\s\S]*?```|`[^`]+`|\*\*\*[^*]+?\*\*\*|\*\*[^*]+?\*\*|\*[^*]+?\*|__[^_]+?__|_[^_]+?_|\bORD-\d+\b)/gi;
  const rawParts = text.split(regex);

  return rawParts.map((part, index) => {
    if (!part) return null;

    // 1. Code blocks
    if (part.startsWith('```') && part.endsWith('```')) {
      return (
        <pre
          key={`cb-${index}`}
          style={{
            background: 'rgba(0, 0, 0, 0.45)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12.5px',
            fontFamily: 'var(--font-mono)',
            color: '#38bdf8',
            overflowX: 'auto',
            margin: '6px 0',
          }}
        >
          {part.slice(3, -3).trim()}
        </pre>
      );
    }

    // 2. Inline code
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={`c-${index}`}
          style={{
            fontFamily: 'var(--font-mono)',
            background: 'rgba(0, 0, 0, 0.45)',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '13px',
            color: '#38bdf8',
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // 3. Bold-Italic (***text***)
    if (part.startsWith('***') && part.endsWith('***') && part.length >= 6) {
      const inner = part.slice(3, -3);
      return (
        <strong key={`bi-${index}`} style={{ color: '#ffffff', fontWeight: 700 }}>
          <em style={{ color: '#e0e7ff', fontStyle: 'italic' }}>{inner}</em>
        </strong>
      );
    }

    // 4. Bold (**text** or __text__)
    if (
      ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) &&
      part.length >= 4
    ) {
      const inner = part.slice(2, -2);
      if (/^ORD-\d+$/i.test(inner)) {
        return (
          <span key={`ord-${index}`} className="order-pill" style={{ display: 'inline-block', margin: '0 2px' }}>
            {inner.toUpperCase()}
          </span>
        );
      }
      return (
        <strong key={`b-${index}`} style={{ color: '#ffffff', fontWeight: 700 }}>
          {inner}
        </strong>
      );
    }

    // 5. Italic / Single-Asterisk (*text* or _text_)
    if (
      ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) &&
      part.length >= 2
    ) {
      const inner = part.slice(1, -1);
      if (/^ORD-\d+$/i.test(inner)) {
        return (
          <span key={`ord-${index}`} className="order-pill" style={{ display: 'inline-block', margin: '0 2px' }}>
            {inner.toUpperCase()}
          </span>
        );
      }
      return (
        <strong key={`em-${index}`} style={{ color: '#ffffff', fontWeight: 600 }}>
          {inner}
        </strong>
      );
    }

    // 6. Direct Order ID matching (ORD-108 without asterisks)
    if (/^ORD-\d+$/i.test(part)) {
      return (
        <span key={`ord-${index}`} className="order-pill" style={{ display: 'inline-block', margin: '0 2px' }}>
          {part.toUpperCase()}
        </span>
      );
    }

    // 7. Plain text: clean up any remaining stray asterisks attached to words
    const cleanText = part
      .replace(/(^|\s)\*([A-Za-z0-9_\-]+)/g, '$1$2')
      .replace(/([A-Za-z0-9_\-]+)\*($|\s)/g, '$1$2')
      .replace(/\*{2,}/g, '');

    return <span key={`t-${index}`}>{cleanText}</span>;
  });
}

function renderMessageContent(content: string) {
  const lines = content.split('\n');
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return <div key={idx} style={{ height: '8px' }} />;
    }

    const isBullet = /^[•\-\*]\s+/.test(trimmed);
    if (isBullet) {
      const cleanLine = trimmed.replace(/^[•\-\*]\s+/, '');
      return (
        <div
          key={idx}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
            margin: '3px 0',
            paddingLeft: '4px',
          }}
        >
          <span style={{ color: 'var(--primary)', fontSize: '13px', lineHeight: '1.6' }}>•</span>
          <div style={{ flex: 1, lineHeight: '1.6' }}>{renderFormattedInline(cleanLine)}</div>
        </div>
      );
    }

    const numMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (numMatch) {
      return (
        <div
          key={idx}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
            margin: '3px 0',
            paddingLeft: '4px',
          }}
        >
          <span style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '13px', lineHeight: '1.6' }}>
            {numMatch[1]}.
          </span>
          <div style={{ flex: 1, lineHeight: '1.6' }}>{renderFormattedInline(numMatch[2])}</div>
        </div>
      );
    }

    return (
      <p key={idx} style={{ margin: '0 0 6px 0', lineHeight: '1.6' }}>
        {renderFormattedInline(line)}
      </p>
    );
  });
}

// Masking helper for privacy & trust (Section 6)
function maskAccountNumber(acc: string): string {
  const clean = (acc || '').trim();
  if (clean.length <= 4) return clean;
  const last4 = clean.slice(-4);
  return `•••• •••• ${last4}`;
}

function maskMobileNumber(mob: string): string {
  const clean = (mob || '').trim();
  if (clean.length <= 4) return clean;
  const last3 = clean.slice(-3);
  return `+92 ••• •••${last3}`;
}

const POLICY_CARD_CONFIG: Record<
  string,
  {
    icon: string;
    category: string;
    shortSummary: string;
    highlights: Array<{ text: string; variant: 'primary' | 'success' | 'info' }>;
    contactInfo?: { email?: string; phone?: string; hours?: string };
  }
> = {
  'RETURN POLICY': {
    icon: '🔄',
    category: 'Returns & Replacements',
    shortSummary:
      'Return general items within 30 days of purchase; electronics (laptops, phones, tablets) within 15 days. Must be unused in original packaging with accessories. Final Sale items excluded.',
    highlights: [
      { text: '30-Day General Return', variant: 'primary' },
      { text: '15-Day Electronics Return', variant: 'primary' },
      { text: 'Original Packaging Required', variant: 'info' },
    ],
  },
  'REFUND POLICY': {
    icon: '💳',
    category: 'Billing & Reimbursements',
    shortSummary:
      'Refunds processed within 5 business days after receipt of returned items. Credited to original payment method. Shipping costs non-refundable unless defective. Credit cards may take +3–5 days.',
    highlights: [
      { text: '5 Business Days Processing', variant: 'success' },
      { text: 'Original Payment Method', variant: 'info' },
      { text: 'Shipping Non-Refundable', variant: 'primary' },
    ],
  },
  'SHIPPING POLICY': {
    icon: '🚚',
    category: 'Logistics & Delivery',
    shortSummary:
      'Free standard shipping on orders above $50. Standard shipping ($4.99) arrives in 3–5 days; Express ($12.99) arrives in 1–2 days. Orders before 2:00 PM EST dispatch same day. All 50 US states.',
    highlights: [
      { text: 'Free Shipping on $50+', variant: 'success' },
      { text: 'Standard: $4.99 (3–5 Days)', variant: 'info' },
      { text: 'Express: $12.99 (1–2 Days)', variant: 'primary' },
    ],
  },
  'WARRANTY POLICY': {
    icon: '🛡️',
    category: 'Hardware Protection',
    shortSummary:
      'All electronics include a 1-year manufacturer warranty covering hardware defects. Physical and liquid damage excluded. Optional 2-year extended warranty available for laptops and desktops.',
    highlights: [
      { text: '1-Year Manufacturer Warranty', variant: 'primary' },
      { text: 'Hardware Defects Covered', variant: 'info' },
      { text: 'Optional 2-Yr Extended Plan', variant: 'success' },
    ],
  },
  'EXCHANGE POLICY': {
    icon: '🔁',
    category: 'Returns & Replacements',
    shortSummary:
      'Exchanges allowed within 30 days of purchase (15 days for electronics) in original condition. If replacement costs more, customer pays difference; if less, refunded within 5 business days.',
    highlights: [
      { text: '30-Day General Exchange', variant: 'primary' },
      { text: '15-Day Electronics Window', variant: 'primary' },
      { text: 'Price Difference Adjusted', variant: 'info' },
    ],
  },
  'CUSTOMER SUPPORT': {
    icon: '🎧',
    category: 'Direct Inquiries & Hours',
    shortSummary:
      'Dedicated support available Monday to Friday, 9:00 AM to 6:00 PM EST. Contact via email, phone, or live chat for return assistance, order tracking, and warranty support.',
    highlights: [
      { text: 'Mon–Fri: 9:00 AM – 6:00 PM EST', variant: 'primary' },
      { text: '1-800-TECHMART', variant: 'info' },
      { text: 'support@techmart.com', variant: 'success' },
    ],
    contactInfo: {
      email: 'support@techmart.com',
      phone: '1-800-TECHMART',
      hours: 'Mon–Fri 9:00 AM – 6:00 PM EST',
    },
  },
  'COMPANY POLICY DOCUMENT': {
    icon: '📄',
    category: 'Authoritative Grounding Document',
    shortSummary:
      'TechMart Online Store Customer Policies source document. Establishes customer terms, return eligibility, warranty specifications, and shipping standards.',
    highlights: [
      { text: 'policy.docx Word Document', variant: 'info' },
      { text: '7 Grounded Sections', variant: 'success' },
      { text: 'Real-Time Verification', variant: 'primary' },
    ],
  },
};

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<'chat' | 'catalog' | 'orders' | 'policies'>('chat');

  // Service health status (verified from real APIs)
  const [dataServiceStatus, setDataServiceStatus] = useState<'connected' | 'checking' | 'error'>('checking');
  const [policyServiceStatus, setPolicyServiceStatus] = useState<'ready' | 'checking' | 'error'>('checking');
  const [lastSyncTime, setLastSyncTime] = useState<string>('Live');

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      content:
        "Hi! I'm Charlie, your TechMart support assistant. I can help you find products, track orders, and check return or refund eligibility.",
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showClearChatModal, setShowClearChatModal] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Products State
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Orders State
  const [orders, setOrders] = useState<Order[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [newCustomerName, setNewCustomerName] = useState('');
  const [newProductModel, setNewProductModel] = useState('');
  const [placingOrder, setPlacingOrder] = useState(false);
  const [orderConfirmationDialog, setOrderConfirmationDialog] = useState<boolean>(false);
  const [orderSuccessBanner, setOrderSuccessBanner] = useState<any>(null);

  // Refund State
  const [refundOrderId, setRefundOrderId] = useState('');
  const [refundEval, setRefundEval] = useState<any>(null);
  const [evaluatingRefund, setEvaluatingRefund] = useState(false);

  // Bank Form State
  const [bankOrderId, setBankOrderId] = useState('');
  const [bankCustomer, setBankCustomer] = useState('');
  const [bankProduct, setBankProduct] = useState('');
  const [bankName, setBankName] = useState('');
  const [bankAccount, setBankAccount] = useState('');
  const [bankMobile, setBankMobile] = useState('');
  const [submittingBank, setSubmittingBank] = useState(false);
  const [bankDetailsList, setBankDetailsList] = useState<BankDetail[]>([]);
  const [loadingBankDetails, setLoadingBankDetails] = useState(false);
  const [bankConfirmationDialog, setBankConfirmationDialog] = useState<boolean>(false);
  const [bankSuccessBanner, setBankSuccessBanner] = useState<string | null>(null);

  // Policy State
  const [policySections, setPolicySections] = useState<PolicySection[]>([]);
  const [fullPolicyText, setFullPolicyText] = useState<string>('');
  const [policyMeta, setPolicyMeta] = useState<any>(null);
  const [loadingPolicy, setLoadingPolicy] = useState(false);
  const [policySearchTerm, setPolicySearchTerm] = useState('');
  const [selectedPolicyDetail, setSelectedPolicyDetail] = useState<PolicySection | null>(null);
  const [showSourceDocModal, setShowSourceDocModal] = useState<boolean>(false);

  // Auto-scroll chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Initial Data Fetch
  useEffect(() => {
    fetchProductsData();
    fetchOrdersData();
    fetchBankDetailsData();
    fetchPolicyData();
  }, []);

  const fetchProductsData = async (force = false) => {
    try {
      setLoadingProducts(true);
      const res = await fetch(`/api/products${force ? '?force=true' : ''}`);
      const data = await res.json();
      if (data.success && data.products) {
        setProducts(data.products);
        setDataServiceStatus('connected');
        if (data.lastUpdated) {
          const d = new Date(data.lastUpdated);
          setLastSyncTime(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        }
      } else {
        setDataServiceStatus('error');
      }
    } catch (err) {
      console.error('Error fetching products:', err);
      setDataServiceStatus('error');
    } finally {
      setLoadingProducts(false);
    }
  };

  const fetchOrdersData = async () => {
    try {
      setLoadingOrders(true);
      const res = await fetch('/api/orders');
      const data = await res.json();
      if (data.success && data.orders) {
        setOrders(data.orders);
        setDataServiceStatus('connected');
      }
    } catch (err) {
      console.error('Error fetching orders:', err);
    } finally {
      setLoadingOrders(false);
    }
  };

  const fetchBankDetailsData = async () => {
    try {
      setLoadingBankDetails(true);
      const res = await fetch('/api/refund?view=bank_details');
      const data = await res.json();
      if (data.success && data.bankDetails) {
        setBankDetailsList(data.bankDetails);
      }
    } catch (err) {
      console.error('Error fetching bank details:', err);
    } finally {
      setLoadingBankDetails(false);
    }
  };

  const fetchPolicyData = async () => {
    try {
      setLoadingPolicy(true);
      const res = await fetch('/api/policy');
      const data = await res.json();
      if (data.success) {
        setPolicySections(data.sections || []);
        setFullPolicyText(data.fullText || '');
        setPolicyMeta({
          source: data.source,
          filename: data.filename,
          sizeBytes: data.fileSizeBytes,
          lastModified: data.lastModified,
          totalSections: data.totalSections || (data.sections ? data.sections.length : 7),
        });
        setPolicyServiceStatus('ready');
      } else {
        setPolicyServiceStatus('error');
      }
    } catch (err) {
      console.error('Error fetching policies:', err);
      setPolicyServiceStatus('error');
    } finally {
      setLoadingPolicy(false);
    }
  };

  // Chat Submission Handler
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isStreaming) return;

    setInputMessage('');
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    const newHistory = [...messages, { id: userMsgId, role: 'user' as const, content: text }];
    setMessages(newHistory);
    setIsStreaming(true);

    try {
      const chatPayloadHistory = newHistory.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: chatPayloadHistory,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat error HTTP ${response.status}`);
      }

      // Check if new order header was returned
      const newOrderHeader = response.headers.get('X-New-Order');
      let orderInfo: any = null;
      if (newOrderHeader) {
        try {
          orderInfo = JSON.parse(newOrderHeader);
          fetchOrdersData();
        } catch (e) {
          console.warn('Failed to parse X-New-Order header');
        }
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');
      let accumulated = '';

      setMessages((prev) => [
        ...prev,
        { id: assistantMsgId, role: 'assistant', content: '', orderInfo },
      ]);

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          accumulated += chunk;

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, content: accumulated } : msg
            )
          );
        }
      }

      if (text.includes('ORD-') || accumulated.includes('ORD-')) {
        fetchOrdersData();
        fetchBankDetailsData();
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: 'assistant',
          content: `⚠️ Charlie encountered a connection issue: ${err.message || 'Please check API connection.'}`,
        },
      ]);
    } finally {
      setIsStreaming(false);
    }
  };

  // Place Order with Confirmation Dialog (Section 3.5 & Section 6)
  const triggerOrderConfirmation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCustomerName.trim() || !newProductModel.trim()) return;
    setOrderConfirmationDialog(true);
  };

  const confirmAndPlaceOrder = async () => {
    setOrderConfirmationDialog(false);
    try {
      setPlacingOrder(true);
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: newCustomerName.trim(),
          model_name: newProductModel.trim(),
        }),
      });
      const data = await res.json();
      if (data.success && data.order) {
        setOrderSuccessBanner(data.order);
        setNewCustomerName('');
        setNewProductModel('');
        await fetchOrdersData();
      } else {
        alert(`Failed to place order: ${data.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      alert(`Error placing order: ${err.message}`);
    } finally {
      setPlacingOrder(false);
    }
  };

  // Check Refund from Orders Tab
  const handleCheckRefund = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refundOrderId.trim() || evaluatingRefund) return;

    try {
      setEvaluatingRefund(true);
      const res = await fetch('/api/refund', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'evaluate',
          order_id: refundOrderId.trim(),
        }),
      });
      const data = await res.json();
      if (data.success && data.result) {
        setRefundEval(data.result);
        if (data.result.eligible) {
          setBankOrderId(data.result.order_id);
          setBankCustomer(data.result.customer);
          setBankProduct(data.result.model_name);
        }
      } else {
        alert(data.error || 'Order not found in database.');
      }
    } catch (err: any) {
      alert(`Error checking refund: ${err.message}`);
    } finally {
      setEvaluatingRefund(false);
    }
  };

  // Submit Bank Details with Confirmation Dialog (Section 3.5 & Section 6)
  const triggerBankConfirmation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bankOrderId.trim() || !bankName.trim() || !bankAccount.trim()) return;
    setBankConfirmationDialog(true);
  };

  const confirmAndSubmitBank = async () => {
    setBankConfirmationDialog(false);
    try {
      setSubmittingBank(true);
      const res = await fetch('/api/refund', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'submit_bank',
          order_id: bankOrderId.trim(),
          customer: bankCustomer.trim(),
          product: bankProduct.trim(),
          bank_name: bankName.trim(),
          account_number: bankAccount.trim(),
          mobile_number: bankMobile.trim(),
        }),
      });
      const data = await res.json();
      if (data.success) {
        setBankSuccessBanner(
          `Refund approved for ${bankOrderId}. Banking details securely synchronized with Google Sheets. Payout scheduled within 5 business days.`
        );
        setBankOrderId('');
        setBankCustomer('');
        setBankProduct('');
        setBankName('');
        setBankAccount('');
        setBankMobile('');
        setRefundEval(null);
        await fetchOrdersData();
        await fetchBankDetailsData();
      } else {
        alert(`Failed to save bank details: ${data.error}`);
      }
    } catch (err: any) {
      alert(`Error submitting bank info: ${err.message}`);
    } finally {
      setSubmittingBank(false);
    }
  };

  // Filtered Products
  const categories = ['All', ...Array.from(new Set(products.map((p) => p.Category))).filter(Boolean)];
  const filteredProducts = products.filter((p) => {
    const matchesSearch =
      !searchTerm ||
      p['Model Name'].toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.Brand.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p['Key Specifications'].toLowerCase().includes(searchTerm.toLowerCase()) ||
      p['Best For'].toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory = selectedCategory === 'All' || p.Category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Filtered Policy Sections (Searches across titles, full content, categories, and keyword tags)
  const filteredPolicies = policySections.filter((sec) => {
    if (!policySearchTerm.trim()) {
      return true; // Renders all 7 policies
    }
    const term = policySearchTerm.toLowerCase().trim();
    const config = POLICY_CARD_CONFIG[sec.title.trim().toUpperCase()];
    const tagMatch = config?.highlights?.some((h) => h.text.toLowerCase().includes(term));
    const titleMatch = sec.title.toLowerCase().includes(term);
    const contentMatch = sec.content.toLowerCase().includes(term);
    const categoryMatch = config?.category?.toLowerCase().includes(term);
    const summaryMatch = config?.shortSummary?.toLowerCase().includes(term);
    return titleMatch || contentMatch || Boolean(tagMatch) || Boolean(categoryMatch) || Boolean(summaryMatch);
  });

  return (
    <div className="app-container">
      {/* 3.1 Compact Header & Verified Status Indicators */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-icon" aria-hidden="true">
            ⚡
          </div>
          <div>
            <h1 className="brand-title">TechMart AI</h1>
            <p className="brand-subtitle">Customer Support & Orders Assistant</p>
          </div>
        </div>

        <div className="header-status-area">
          <div className="service-pill" title="Google Sheets live synchronization">
            <span
              className={`status-dot ${
                dataServiceStatus === 'connected' ? 'active' : dataServiceStatus === 'checking' ? 'pending' : 'error'
              }`}
            />
            <span>{dataServiceStatus === 'connected' ? 'Data connected' : 'Connecting...'}</span>
          </div>

          <div className="service-pill" title="policy.docx Word document grounding">
            <span
              className={`status-dot ${
                policyServiceStatus === 'ready' ? 'active' : policyServiceStatus === 'checking' ? 'pending' : 'error'
              }`}
            />
            <span>{policyServiceStatus === 'ready' ? 'Policy ready' : 'Policy pending'}</span>
          </div>
        </div>
      </header>

      {/* 3.2 Primary Navigation Tabs */}
      <nav className="nav-tabs" aria-label="Main Navigation">
        <button
          id="nav-tab-chat"
          className={`nav-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <span>💬</span>
          <span>Support Chat</span>
        </button>

        <button
          id="nav-tab-catalog"
          className={`nav-tab-btn ${activeTab === 'catalog' ? 'active' : ''}`}
          onClick={() => setActiveTab('catalog')}
        >
          <span>📦</span>
          <span>Product Catalog</span>
          {products.length > 0 && <span className="nav-badge">{products.length}</span>}
        </button>

        <button
          id="nav-tab-orders"
          className={`nav-tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
          onClick={() => setActiveTab('orders')}
        >
          <span>🛒</span>
          <span>Orders & Refunds</span>
          {orders.length > 0 && <span className="nav-badge">{orders.length}</span>}
        </button>

        <button
          id="nav-tab-policies"
          className={`nav-tab-btn ${activeTab === 'policies' ? 'active' : ''}`}
          onClick={() => setActiveTab('policies')}
        >
          <span>📜</span>
          <span>Company Policies</span>
        </button>
      </nav>

      {/* VIEW 1: Main Support Chat Experience (Primary Focus) */}
      {activeTab === 'chat' && (
        <section aria-label="Customer Support Chat Workspace">
          <div className="chat-workspace dashboard-layout">
            {/* Main Chat Panel */}
            <div className="chat-card chat-panel">
              <div className="chat-card-header">
                <div className="agent-profile">
                  <div className="agent-avatar" aria-hidden="true">
                    🤖
                  </div>
                  <div>
                    <h2 className="agent-name">Charlie</h2>
                    <span className="agent-role">TechMart AI Assistant</span>
                  </div>
                </div>

                <div className="chat-header-actions">
                  <button
                    type="button"
                    className="btn-icon-control"
                    onClick={() => {
                      fetchProductsData(true);
                      fetchOrdersData();
                      fetchBankDetailsData();
                    }}
                    title="Refresh data"
                    aria-label="Refresh data"
                    disabled={loadingProducts}
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                      className={loadingProducts ? 'spin-animation' : ''}
                    >
                      <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                    </svg>
                  </button>

                  <button
                    type="button"
                    className="btn-icon-control danger-hover"
                    onClick={() => setShowClearChatModal(true)}
                    title="Clear conversation"
                    aria-label="Clear conversation"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Messages Area */}
              <div className="messages-container" id="chat-messages-scroll" role="log" aria-live="polite">
                {messages.map((m) => (
                  <div key={m.id} className={`message-row ${m.role}`}>
                    <div className="msg-icon">{m.role === 'assistant' ? '⚡' : '👤'}</div>
                    <div style={{ maxWidth: '100%' }}>
                      <div className="message-bubble">{renderMessageContent(m.content)}</div>

                      {/* Real Verified Order Placement Callout */}
                      {m.orderInfo && (
                        <div className="order-success-callout">
                          <span style={{ fontSize: '18px' }}>🎉</span>
                          <div>
                            <h4>Order Confirmed & Saved to Google Sheets</h4>
                            <p>
                              <strong>Order ID:</strong> {m.orderInfo.order_id} •{' '}
                              <strong>Customer:</strong> {m.orderInfo.customer} •{' '}
                              <strong>Model:</strong> {m.orderInfo.model_name} •{' '}
                              <strong>Price:</strong> ${m.orderInfo.price.toFixed(2)}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isStreaming && (
                  <div className="message-row assistant">
                    <div className="msg-icon">⚡</div>
                    <div className="typing-dots">
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* 3.3 Four Useful Quick Actions (Grid / wrapping, no clipping) */}
              <div className="quick-actions-bar" aria-label="Suggested quick actions">
                <button
                  className="quick-action-btn"
                  onClick={() =>
                    handleSendMessage('Can you recommend top laptops or products currently in stock?')
                  }
                >
                  <span>🔍</span>
                  <span>Find a product</span>
                </button>
                <button
                  className="quick-action-btn"
                  onClick={() =>
                    handleSendMessage('I would like to track my order. Can you look up order status?')
                  }
                >
                  <span>📦</span>
                  <span>Track an order</span>
                </button>
                <button
                  className="quick-action-btn"
                  onClick={() =>
                    handleSendMessage('Can you check if order ORD-101 is eligible for a refund under store policy?')
                  }
                >
                  <span>⚖️</span>
                  <span>Check a refund</span>
                </button>
                <button
                  className="quick-action-btn"
                  onClick={() =>
                    handleSendMessage('What is the company return and refund policy for electronics and general merchandise?')
                  }
                >
                  <span>📜</span>
                  <span>Return policy</span>
                </button>
              </div>

              {/* Input Composer */}
              <form
                className="chat-composer"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
              >
                <input
                  type="text"
                  id="chat-composer-input"
                  className="composer-input"
                  placeholder="Ask about products, orders, or return policies…"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  disabled={isStreaming}
                />
                <button
                  type="submit"
                  id="chat-composer-send"
                  className="btn-send"
                  disabled={isStreaming || !inputMessage.trim()}
                >
                  <span>Send</span>
                  <span>↗</span>
                </button>
              </form>
            </div>

            {/* 3.7 Reworked Right Sidebar: Service Status & Policy Summary */}
            <aside className="chat-aside dashboard-sidebar">
              <div className="aside-card service-status">
                <div className="aside-card-header">
                  <span>Service Status</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Updated {lastSyncTime}</span>
                </div>
                <div className="service-status-list">
                  <div className="service-status-row">
                    <span className="service-label">Product Catalog</span>
                    <span className="service-state">
                      <span className="status-dot active" />
                      <span>{products.length} Items Synced</span>
                    </span>
                  </div>
                  <div className="service-status-row">
                    <span className="service-label">Orders Service</span>
                    <span className="service-state">
                      <span className="status-dot active" />
                      <span>{orders.length} Live Orders</span>
                    </span>
                  </div>
                  <div className="service-status-row">
                    <span className="service-label">Store Policy</span>
                    <span className="service-state">
                      <span className="status-dot active" />
                      <span>policy.docx Active</span>
                    </span>
                  </div>
                </div>
              </div>

              <div className="aside-card policy-reference">
                <div className="aside-card-header">
                  <span>Policy Quick Reference</span>
                </div>
                <div className="policy-rules-summary">
                  <p style={{ marginBottom: '8px' }}>
                    <strong>• Electronics:</strong> 15-day return window from purchase date.
                  </p>
                  <p style={{ marginBottom: '8px' }}>
                    <strong>• General Merchandise:</strong> 30-day return window.
                  </p>
                  <p>
                    <strong>• Refund Payout:</strong> 5 business days after bank verification.
                  </p>
                </div>
              </div>
            </aside>
          </div>
        </section>
      )}

      {/* VIEW 2: Live Product Catalog (Section 3.4) */}
      {activeTab === 'catalog' && (
        <section aria-label="Product Catalog">
          <div className="catalog-toolbar">
            <div className="search-input-wrap">
              <span className="search-icon-svg">🔍</span>
              <input
                type="text"
                id="product-search-field"
                className="search-field"
                placeholder="Search products by model, brand, or specifications..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className="category-filter-group">
              {categories.map((cat) => (
                <button
                  key={cat}
                  className={`category-filter-btn ${selectedCategory === cat ? 'active' : ''}`}
                  onClick={() => setSelectedCategory(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="sync-timestamp">Last refreshed: {lastSyncTime}</span>
              <button
                type="button"
                className="btn-icon-control"
                onClick={() => fetchProductsData(true)}
                title="Refresh products"
                aria-label="Refresh products"
                disabled={loadingProducts}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                  className={loadingProducts ? 'spin-animation' : ''}
                >
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
              </button>
            </div>
          </div>

          {loadingProducts ? (
            <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
              <p>Fetching real-time product inventory from Google Sheets...</p>
            </div>
          ) : filteredProducts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
              <p>No products found matching &ldquo;{searchTerm}&rdquo;.</p>
            </div>
          ) : (
            <div className="products-grid-layout">
              {filteredProducts.map((p, idx) => (
                <article key={idx} className="product-item-card">
                  <div>
                    <div className="product-card-top">
                      <span className="badge-category">{p.Category}</span>
                      <span
                        className={`badge-stock ${
                          p.stock > 0 ? 'in-stock' : 'out-of-stock'
                        }`}
                      >
                        {p.stock > 0 ? `${p.stock} in stock` : 'Out of stock'}
                      </span>
                    </div>

                    <h3 className="product-card-title">{p['Model Name']}</h3>
                    <div className="product-card-brand">{p.Brand}</div>

                    <div className="product-card-specs">{p['Key Specifications']}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                      🎯 Ideal for: {p['Best For']}
                    </div>
                  </div>

                  <div className="product-card-footer">
                    <div className="product-card-price">${p.price.toFixed(2)}</div>
                    <button
                      className="btn-card-action"
                      onClick={() => {
                        setActiveTab('chat');
                        handleSendMessage(
                          `Can you provide details on the ${p.Brand} ${p['Model Name']} and assist me with purchasing it?`
                        );
                      }}
                    >
                      Inquire in Chat ↗
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {/* VIEW 3: Orders & Refund Manager (Section 3.5 & Section 6) */}
      {activeTab === 'orders' && (
        <section aria-label="Orders and Refunds Management">
          <div className="orders-split-layout">
            {/* Left Column: Live Orders & Bank Submissions */}
            <div>
              {/* Live Orders Table */}
              <div className="section-panel">
                <div className="panel-header">
                  <h3 className="panel-title">
                    <span>📋 Live Orders</span>
                    <span className="nav-badge">{orders.length} Records</span>
                  </h3>
                  <button
                    type="button"
                    className="btn-icon-control"
                    onClick={fetchOrdersData}
                    disabled={loadingOrders}
                    title="Refresh orders"
                    aria-label="Refresh orders"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                      className={loadingOrders ? 'spin-animation' : ''}
                    >
                      <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                    </svg>
                  </button>
                </div>

                <div className="table-responsive-container">
                  <table className="saas-table">
                    <thead>
                      <tr>
                        <th>Order ID</th>
                        <th>Customer</th>
                        <th>Model Name</th>
                        <th>Category</th>
                        <th>Purchase Age</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.map((o, idx) => (
                        <tr key={idx}>
                          <td>
                            <span className="order-pill">{o.order_id}</span>
                          </td>
                          <td style={{ fontWeight: 600 }}>{o.customer}</td>
                          <td>{o['Model Name'] || '—'}</td>
                          <td style={{ textTransform: 'capitalize' }}>
                            {o.product} ({o.category})
                          </td>
                          <td>{o.days_ago} days ago</td>
                          <td>
                            <span
                              className={`status-badge-table ${
                                (o.Status || '').toLowerCase().includes('approved')
                                  ? 'approved'
                                  : (o.Status || '').toLowerCase().includes('shipped')
                                  ? 'shipped'
                                  : 'placed'
                              }`}
                            >
                              {o.Status || 'Pending'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Recorded Refund Bank Accounts (Masked for Privacy) */}
              <div className="section-panel">
                <div className="panel-header">
                  <h3 className="panel-title">
                    <span>💳 Recorded Refund Accounts</span>
                    <span className="nav-badge">{bankDetailsList.length}</span>
                  </h3>
                  <button
                    type="button"
                    className="btn-icon-control"
                    onClick={fetchBankDetailsData}
                    disabled={loadingBankDetails}
                    title="Refresh refund accounts"
                    aria-label="Refresh refund accounts"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                      className={loadingBankDetails ? 'spin-animation' : ''}
                    >
                      <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                    </svg>
                  </button>
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                  Sensitive account details are masked in UI logs to safeguard customer privacy.
                </p>

                <div className="table-responsive-container">
                  <table className="saas-table">
                    <thead>
                      <tr>
                        <th>Order ID</th>
                        <th>Customer</th>
                        <th>Product</th>
                        <th>Bank Name</th>
                        <th>Account (Masked)</th>
                        <th>Mobile</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bankDetailsList.length === 0 ? (
                        <tr>
                          <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px' }}>
                            No refund accounts submitted yet.
                          </td>
                        </tr>
                      ) : (
                        bankDetailsList.map((b, idx) => (
                          <tr key={idx}>
                            <td>
                              <span className="order-pill">{b.order_id}</span>
                            </td>
                            <td>{b.customer}</td>
                            <td>{b.product}</td>
                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{b.Bank_Name}</td>
                            <td style={{ fontFamily: 'var(--font-mono)' }}>{maskAccountNumber(b['Account Number'])}</td>
                            <td>{maskMobileNumber(b['Mobile Number'])}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Right Column: Actions (Place Order, Evaluate Refund, Submit Bank) */}
            <div>
              {/* Place New Order */}
              <div className="section-panel">
                <h3 className="panel-title" style={{ marginBottom: '8px' }}>
                  <span>➕ Place Customer Order</span>
                </h3>
                <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                  Registers order with sequential Order ID and updates live Google Sheets.
                </p>

                {orderSuccessBanner && (
                  <div className="result-callout eligible" style={{ marginBottom: '14px' }}>
                    <strong>✅ Order Created Successfully!</strong>
                    <div style={{ marginTop: '4px' }}>
                      Order ID: <strong>{orderSuccessBanner.order_id}</strong> • Customer:{' '}
                      {orderSuccessBanner.customer} • Model: {orderSuccessBanner.model_name}
                    </div>
                  </div>
                )}

                <form onSubmit={triggerOrderConfirmation}>
                  <div className="form-field-group">
                    <label className="form-field-label">Customer Full Name</label>
                    <input
                      type="text"
                      className="form-field-input"
                      placeholder="e.g. Sara Ahmed"
                      value={newCustomerName}
                      onChange={(e) => setNewCustomerName(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-field-group">
                    <label className="form-field-label">Select Product Model</label>
                    <input
                      type="text"
                      list="models-datalist"
                      className="form-field-input"
                      placeholder="e.g. MacBook Air M3"
                      value={newProductModel}
                      onChange={(e) => setNewProductModel(e.target.value)}
                      required
                    />
                    <datalist id="models-datalist">
                      {products.map((p, i) => (
                        <option key={i} value={p['Model Name']}>
                          {p.Brand} {p['Model Name']} (${p.price.toFixed(2)})
                        </option>
                      ))}
                    </datalist>
                  </div>

                  <button
                    type="submit"
                    className="btn-primary-action"
                    disabled={placingOrder || !newCustomerName.trim() || !newProductModel.trim()}
                  >
                    {placingOrder ? 'Recording in Sheets...' : 'Review & Place Order ↗'}
                  </button>
                </form>
              </div>

              {/* Check Refund Eligibility */}
              <div className="section-panel">
                <h3 className="panel-title" style={{ marginBottom: '8px' }}>
                  <span>⚖️ Check Refund Eligibility</span>
                </h3>
                <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                  Evaluates purchase date and item category against official store policy.
                </p>

                <form onSubmit={handleCheckRefund}>
                  <div className="form-field-group">
                    <label className="form-field-label">Order ID</label>
                    <input
                      type="text"
                      className="form-field-input"
                      placeholder="e.g. ORD-101"
                      value={refundOrderId}
                      onChange={(e) => setRefundOrderId(e.target.value)}
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    className="btn-primary-action"
                    disabled={evaluatingRefund || !refundOrderId.trim()}
                  >
                    {evaluatingRefund ? 'Evaluating...' : 'Evaluate Eligibility ↗'}
                  </button>
                </form>

                {refundEval && (
                  <div className={`result-callout ${refundEval.eligible ? 'eligible' : 'ineligible'}`}>
                    <div style={{ fontWeight: 700, marginBottom: '4px' }}>
                      {refundEval.eligible ? '✅ ELIGIBLE FOR REFUND' : '❌ NOT ELIGIBLE'}
                    </div>
                    <p>
                      <strong>Order:</strong> {refundEval.order_id} ({refundEval.customer})
                    </p>
                    <p>
                      <strong>Item:</strong> {refundEval.model_name}
                    </p>
                    <p>
                      <strong>Policy Window:</strong> Purchased {refundEval.days_ago} days ago (Allowed limit:{' '}
                      {refundEval.allowed_days} days).
                    </p>
                    <p style={{ marginTop: '6px' }}>{refundEval.message}</p>
                  </div>
                )}
              </div>

              {/* Submit Bank Details */}
              <div className="section-panel">
                <h3 className="panel-title" style={{ marginBottom: '8px' }}>
                  <span>🏦 Submit Refund Bank Details</span>
                </h3>
                <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                  Appends banking information to Google Sheets and updates status to &ldquo;Return Approved&rdquo;.
                </p>

                {bankSuccessBanner && (
                  <div className="result-callout eligible" style={{ marginBottom: '14px' }}>
                    {bankSuccessBanner}
                  </div>
                )}

                <form onSubmit={triggerBankConfirmation}>
                  <div className="form-field-group">
                    <label className="form-field-label">Order ID</label>
                    <input
                      type="text"
                      className="form-field-input"
                      placeholder="e.g. ORD-101"
                      value={bankOrderId}
                      onChange={(e) => setBankOrderId(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-field-group">
                    <label className="form-field-label">Customer Name</label>
                    <input
                      type="text"
                      className="form-field-input"
                      placeholder="Customer name"
                      value={bankCustomer}
                      onChange={(e) => setBankCustomer(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-field-group">
                    <label className="form-field-label">Bank Name</label>
                    <input
                      type="text"
                      className="form-field-input"
                      placeholder="e.g. Meezan Bank / Chase"
                      value={bankName}
                      onChange={(e) => setBankName(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-field-group">
                    <label className="form-field-label">Account Number / IBAN</label>
                    <input
                      type="text"
                      className="form-field-input"
                      placeholder="e.g. 01020304050607"
                      value={bankAccount}
                      onChange={(e) => setBankAccount(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-field-group">
                    <label className="form-field-label">Mobile Number</label>
                    <input
                      type="text"
                      className="form-field-input"
                      placeholder="e.g. +92 300 1234567"
                      value={bankMobile}
                      onChange={(e) => setBankMobile(e.target.value)}
                    />
                  </div>

                  <button
                    type="submit"
                    className="btn-primary-action"
                    disabled={submittingBank || !bankOrderId.trim() || !bankName.trim() || !bankAccount.trim()}
                  >
                    {submittingBank ? 'Appending to Sheets...' : 'Review & Submit to Sheets ↗'}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* VIEW 4: Official Store Policies Centre */}
      {activeTab === 'policies' && (
        <section aria-label="Official Store Policies Centre">
          {/* Compact Page Header with Title, Description, and Responsive Functional Search */}
          <div className="policy-center-header">
            <div className="policy-header-title-group">
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Store Policies
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Official customer policies and service terms grounded in Word document (<code>policy.docx</code>).
              </p>
            </div>

            {/* Functional Search Field with Responsive Expanded Width */}
            <div className="policy-search-container">
              <div className="policy-search-wrapper">
                <span
                  style={{
                    position: 'absolute',
                    left: '12px',
                    color: 'var(--text-muted)',
                    fontSize: '13px',
                    pointerEvents: 'none',
                  }}
                  aria-hidden="true"
                >
                  🔍
                </span>
                <input
                  type="text"
                  className="search-field"
                  placeholder="Search policies (returns, refund, warranty)..."
                  value={policySearchTerm}
                  onChange={(e) => setPolicySearchTerm(e.target.value)}
                  aria-label="Search store policies"
                />
                {policySearchTerm && (
                  <button
                    type="button"
                    onClick={() => setPolicySearchTerm('')}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      fontSize: '13px',
                      padding: 0,
                    }}
                    title="Clear search"
                    aria-label="Clear search"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Refined Responsive Source-Status Indicator */}
          <div className="policy-source-strip">
            <div className="policy-source-left">
              <span className="policy-source-badge">
                <span
                  className={`status-dot ${policyServiceStatus === 'ready' ? 'active' : 'pending'}`}
                  style={{ width: 7, height: 7 }}
                />
                📄 {policyMeta?.filename || 'policy.docx'}
              </span>
              <span>
                <strong style={{ color: 'var(--text-primary)' }}>Source:</strong> Company Policy Document &bull; TechMart Online Store &bull;{' '}
                <span style={{ color: 'var(--success)', fontWeight: 600 }}>Active Grounding</span>
              </span>
              {policyMeta?.sizeBytes && (
                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  ({(policyMeta.sizeBytes / 1024).toFixed(1)} KB)
                </span>
              )}
            </div>

            <div className="policy-source-right">
              <span className="policy-verified-count">
                {loadingPolicy
                  ? 'Verifying Sections...'
                  : `${policySections.length} Verified Section${policySections.length === 1 ? '' : 's'}`}
              </span>
              <button
                type="button"
                className="btn-secondary"
                style={{
                  padding: '5px 12px',
                  fontSize: '12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
                onClick={() => setShowSourceDocModal(true)}
                title="View complete unedited policy document"
                aria-label="View source document"
              >
                <span>📖</span>
                <span>View Source Document ↗</span>
              </button>
            </div>
          </div>

          {/* Active Search Results Indicator */}
          {policySearchTerm.trim() && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 14px',
                background: 'var(--bg-panel-subtle)',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '16px',
                fontSize: '12.5px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <span>
                Showing <strong>{filteredPolicies.length}</strong> matching policy section
                {filteredPolicies.length === 1 ? '' : 's'} for &ldquo;{policySearchTerm}&rdquo;
              </span>
              <button
                className="btn-quiet"
                onClick={() => setPolicySearchTerm('')}
                style={{ fontSize: '12px', color: 'var(--primary)' }}
              >
                Clear filter
              </button>
            </div>
          )}

          {/* Loading State */}
          {loadingPolicy ? (
            <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
              <div className="typing-dot" style={{ display: 'inline-block', margin: '0 4px' }} />
              <div className="typing-dot" style={{ display: 'inline-block', margin: '0 4px' }} />
              <div className="typing-dot" style={{ display: 'inline-block', margin: '0 4px' }} />
              <p style={{ marginTop: '12px', fontSize: '13.5px' }}>
                Extracting authoritative policies from policy.docx...
              </p>
            </div>
          ) : policyServiceStatus === 'error' || policySections.length === 0 ? (
            /* Clear Unavailable / Error State (Never fabricates content) */
            <div
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 'var(--radius-md)',
                padding: '36px',
                textAlign: 'center',
                maxWidth: '560px',
                margin: '40px auto',
              }}
            >
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>⚠️</div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f87171', marginBottom: '8px' }}>
                Store Policies Unavailable
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '18px', lineHeight: 1.6 }}>
                Unable to load policies from the official Word document (<code>policy.docx</code>). Our system does not
                fabricate policy terms when the authoritative source is unreachable.
              </p>
              <button
                className="btn-secondary"
                onClick={fetchPolicyData}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '8px 18px' }}
              >
                <span>🔄</span>
                <span>Retry Loading Policies</span>
              </button>
            </div>
          ) : filteredPolicies.length === 0 ? (
            /* Zero Search Results State */
            <div
              style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '40px 20px',
                textAlign: 'center',
                margin: '20px 0',
              }}
            >
              <div style={{ fontSize: '28px', marginBottom: '8px' }}>🔍</div>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                No policies matched &ldquo;{policySearchTerm}&rdquo;
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Try searching for keywords like returns, 15 days, shipping, warranty, or customer support.
              </p>
              <button className="btn-secondary" onClick={() => setPolicySearchTerm('')}>
                Clear Search Filter
              </button>
            </div>
          ) : (
            /* Scannable Policy Cards Grid */
            <div className="policy-grid-layout">
              {filteredPolicies.map((sec, idx) => {
                const upperTitle = sec.title.trim().toUpperCase();
                const config = POLICY_CARD_CONFIG[upperTitle] || {
                  icon: '📌',
                  category: 'Store Policy',
                  shortSummary: sec.content.slice(0, 160) + '...',
                  highlights: [{ text: 'Grounded in policy.docx', variant: 'primary' as const }],
                };
                const isSupport = upperTitle === 'CUSTOMER SUPPORT';

                return (
                  <article
                    key={idx}
                    className={`policy-item-card ${isSupport ? 'support-highlight' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedPolicyDetail(sec)}
                  >
                    <div>
                      {/* Card Header with Icon, Title, and Category */}
                      <div className="policy-card-header">
                        <div className="policy-card-icon" aria-hidden="true">
                          {config.icon}
                        </div>
                        <div className="policy-card-title-group">
                          <h3>{sec.title}</h3>
                          <span>{config.category}</span>
                        </div>
                      </div>

                      {/* Subtle Visual Highlights (Deadlines, Timelines, Thresholds) */}
                      <div className="policy-highlights-row">
                        {config.highlights.map((h, hIdx) => (
                          <span key={hIdx} className={`policy-highlight-chip ${h.variant}`}>
                            {h.text}
                          </span>
                        ))}
                      </div>

                      {/* Concise Scannable Summary */}
                      <p className="policy-card-summary">{config.shortSummary}</p>

                      {/* Quick Contact Info for Customer Support */}
                      {isSupport && config.contactInfo && (
                        <div
                          style={{
                            background: 'rgba(99, 102, 241, 0.08)',
                            border: '1px solid rgba(99, 102, 241, 0.2)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '10px 12px',
                            marginBottom: '14px',
                            fontSize: '12.5px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '6px',
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: 'var(--text-muted)' }}>🕒 Hours:</span>
                            <strong style={{ color: 'var(--text-primary)' }}>{config.contactInfo.hours}</strong>
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '2px' }}>
                            <a
                              href={`mailto:${config.contactInfo.email}`}
                              style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}
                            >
                              ✉️ {config.contactInfo.email}
                            </a>
                            <a
                              href="tel:18008324627"
                              style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}
                            >
                              📞 {config.contactInfo.phone}
                            </a>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Card Footer with Read Full Policy Trigger */}
                    <div className="policy-card-footer">
                      <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                        authoritative &bull; policy.docx
                      </span>
                      <button
                        type="button"
                        className="btn-quiet"
                        style={{
                          color: 'var(--primary)',
                          fontWeight: 600,
                          fontSize: '12.5px',
                          padding: '4px 8px',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedPolicyDetail(sec);
                        }}
                      >
                        Read full policy ↗
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}

          {/* AI Assistant Banner (Links to Charlie AI) */}
          <div className="policy-ai-banner">
            <div className="policy-ai-banner-content">
              <div className="policy-ai-icon" aria-hidden="true">
                🤖
              </div>
              <div>
                <h4>Have a specific order question or need policy clarification?</h4>
                <p>
                  Charlie AI is grounded in our official Word document and can check your specific order return eligibility in seconds.
                </p>
              </div>
            </div>
            <button
              className="btn-primary-action"
              style={{
                width: 'auto',
                margin: 0,
                padding: '9px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13.5px',
              }}
              onClick={() => {
                setActiveTab('chat');
                setInputMessage('What are the store return and refund policies for electronics?');
              }}
            >
              <span>💬</span>
              <span>Ask Charlie in Chat ↗</span>
            </button>
          </div>
        </section>
      )}

      {/* CONFIRMATION DIALOG FOR ORDER PLACEMENT (Section 3.5 & Section 6) */}
      {orderConfirmationDialog && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="order-confirm-title">
          <div className="modal-content-box">
            <div className="modal-header">
              <h3 id="order-confirm-title" className="modal-title">
                Confirm Order Placement
              </h3>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: '10px' }}>
                You are about to record a new live order in Google Sheets:
              </p>
              <div
                style={{
                  background: 'var(--bg-surface)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '13px',
                }}
              >
                <p>
                  <strong>Customer:</strong> {newCustomerName}
                </p>
                <p>
                  <strong>Product Model:</strong> {newProductModel}
                </p>
                <p>
                  <strong>Destination:</strong> Google Sheets Orders Tab (Live)
                </p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setOrderConfirmationDialog(false)}>
                Cancel
              </button>
              <button className="btn-primary-action" style={{ width: 'auto', marginTop: 0 }} onClick={confirmAndPlaceOrder}>
                Confirm & Place Order
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CONFIRMATION DIALOG FOR BANK DETAILS SUBMISSION (Section 3.5 & Section 6) */}
      {bankConfirmationDialog && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="bank-confirm-title">
          <div className="modal-content-box">
            <div className="modal-header">
              <h3 id="bank-confirm-title" className="modal-title">
                Confirm Refund Bank Submission
              </h3>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: '10px' }}>
                Please confirm the refund banking information to be written to Google Sheets:
              </p>
              <div
                style={{
                  background: 'var(--bg-surface)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '13px',
                }}
              >
                <p>
                  <strong>Order ID:</strong> {bankOrderId}
                </p>
                <p>
                  <strong>Bank Name:</strong> {bankName}
                </p>
                <p>
                  <strong>Account:</strong> {maskAccountNumber(bankAccount)}
                </p>
                <p>
                  <strong>Mobile:</strong> {maskMobileNumber(bankMobile)}
                </p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setBankConfirmationDialog(false)}>
                Cancel
              </button>
              <button className="btn-primary-action" style={{ width: 'auto', marginTop: 0 }} onClick={confirmAndSubmitBank}>
                Confirm & Submit to Sheets
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CONFIRMATION DIALOG FOR CLEARING CHAT */}
      {showClearChatModal && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="clear-chat-title"
          onClick={() => setShowClearChatModal(false)}
        >
          <div
            className="modal-content-box"
            style={{ maxWidth: '440px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="clear-chat-title" className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>🗑️</span>
                <span>Clear Conversation</span>
              </h3>
              <button
                className="btn-quiet"
                onClick={() => setShowClearChatModal(false)}
                aria-label="Close dialog"
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                Are you sure you want to clear your conversation? All previous messages from this session will be removed and this action cannot be undone.
              </p>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowClearChatModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary-action"
                style={{
                  width: 'auto',
                  marginTop: 0,
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  borderColor: '#dc2626',
                }}
                onClick={() => {
                  setMessages([
                    {
                      id: `welcome-${Date.now()}`,
                      role: 'assistant',
                      content:
                        "Hi! I'm Charlie, your TechMart support assistant. I can help you find products, track orders, and check return or refund eligibility.",
                    },
                  ]);
                  setIsStreaming(false);
                  setShowClearChatModal(false);
                }}
              >
                Clear Conversation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* POLICY DETAIL MODAL (Full Section View) */}
      {selectedPolicyDetail && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="policy-detail-title"
          onClick={() => setSelectedPolicyDetail(null)}
        >
          <div
            className="modal-content-box modal-wide"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '24px' }}>
                  {POLICY_CARD_CONFIG[selectedPolicyDetail.title.trim().toUpperCase()]?.icon || '📌'}
                </span>
                <div>
                  <h3 id="policy-detail-title" className="modal-title">
                    {selectedPolicyDetail.title}
                  </h3>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {POLICY_CARD_CONFIG[selectedPolicyDetail.title.trim().toUpperCase()]?.category ||
                      'Official Store Policy'}{' '}
                    &bull; Grounded in policy.docx
                  </span>
                </div>
              </div>
              <button
                className="btn-quiet"
                onClick={() => setSelectedPolicyDetail(null)}
                aria-label="Close policy details"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              {/* Highlight chips in modal */}
              {POLICY_CARD_CONFIG[selectedPolicyDetail.title.trim().toUpperCase()]?.highlights && (
                <div className="policy-highlights-row" style={{ marginBottom: '16px' }}>
                  {POLICY_CARD_CONFIG[selectedPolicyDetail.title.trim().toUpperCase()].highlights.map((h, i) => (
                    <span key={i} className={`policy-highlight-chip ${h.variant}`}>
                      {h.text}
                    </span>
                  ))}
                </div>
              )}

              {/* Unedited authoritative content from Word document */}
              <div
                style={{
                  background: 'var(--bg-surface)',
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '13.5px',
                  lineHeight: '1.7',
                  color: 'var(--text-primary)',
                  whiteSpace: 'pre-line',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                {selectedPolicyDetail.content}
              </div>

              {/* Dedicated Contact info if Customer Support */}
              {selectedPolicyDetail.title.trim().toUpperCase() === 'CUSTOMER SUPPORT' && (
                <div
                  style={{
                    marginTop: '16px',
                    padding: '14px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--primary-subtle)',
                    border: '1px solid rgba(99, 102, 241, 0.25)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    fontSize: '13px',
                  }}
                >
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Direct Support Channels:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px' }}>
                    <a
                      href="mailto:support@techmart.com"
                      style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}
                    >
                      ✉️ support@techmart.com
                    </a>
                    <a
                      href="tel:18008324627"
                      style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}
                    >
                      📞 1-800-TECHMART (1-800-832-4627)
                    </a>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      🕒 Mon–Fri 9:00 AM – 6:00 PM EST
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
              <button
                className="btn-primary-action"
                style={{ width: 'auto', margin: 0, padding: '8px 16px', fontSize: '13px' }}
                onClick={() => {
                  const policyName = selectedPolicyDetail.title;
                  setSelectedPolicyDetail(null);
                  setActiveTab('chat');
                  setInputMessage(`What are the specific rules and deadlines for the ${policyName}?`);
                }}
              >
                <span>💬 Ask Charlie in Chat ↗</span>
              </button>

              <button className="btn-secondary" onClick={() => setSelectedPolicyDetail(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FULL SOURCE POLICY DOCUMENT MODAL */}
      {showSourceDocModal && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="source-doc-title"
          onClick={() => setShowSourceDocModal(false)}
        >
          <div
            className="modal-content-box modal-wide"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '22px' }}>📄</span>
                <div>
                  <h3 id="source-doc-title" className="modal-title">
                    Official Policy Document Source
                  </h3>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {policyMeta?.filename || 'policy.docx'} &bull; {policyMeta?.source || 'Word Document'}
                  </span>
                </div>
              </div>
              <button
                className="btn-quiet"
                onClick={() => setShowSourceDocModal(false)}
                aria-label="Close document viewer"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              {/* Metadata Banner */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '12px',
                  padding: '10px 14px',
                  background: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '14px',
                  fontSize: '12.5px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Format: </span>
                  <strong>Microsoft Word (.docx)</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Status: </span>
                  <strong style={{ color: 'var(--success)' }}>● Verified Grounding Source</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Total Sections: </span>
                  <strong>{policySections.length || 7} Sections</strong>
                </div>
                {policyMeta?.sizeBytes && (
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Size: </span>
                    <strong>{(policyMeta.sizeBytes / 1024).toFixed(1)} KB</strong>
                  </div>
                )}
              </div>

              {/* Complete unedited raw text */}
              <div
                style={{
                  background: 'var(--bg-panel-subtle)',
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '13px',
                  lineHeight: '1.7',
                  color: 'var(--text-secondary)',
                  whiteSpace: 'pre-line',
                  maxHeight: '380px',
                  overflowY: 'auto',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                {fullPolicyText || policySections.map((s) => `${s.title}\n\n${s.content}`).join('\n\n---\n\n')}
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowSourceDocModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
