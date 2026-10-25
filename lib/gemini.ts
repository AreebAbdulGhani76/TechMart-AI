import { GoogleGenerativeAI } from '@google/generative-ai';
import { getCompanyPolicyText } from './policy';
import { fetchProducts, evaluateRefund, createOrder, submitBankDetails } from './sheets';

export function getGeminiClient(customKey?: string) {
  const apiKey = customKey || process.env.GOOGLE_API_KEY || '';
  if (!apiKey) throw new Error('Google Gemini API Key is missing.');
  return new GoogleGenerativeAI(apiKey);
}

export async function processAgentChat(
  userMessage: string,
  history: Array<{ role: 'user' | 'assistant'; content: string }>,
  customKey?: string
) {
  const genAI = getGeminiClient(customKey);

  // 1. Fetch Company Policies from Word (.docx) Document
  const policyText = await getCompanyPolicyText();

  // 2. Fetch Live Products from Google Sheets
  const products = await fetchProducts();
  const qLower = userMessage.toLowerCase();
  const matchedProducts = products
    .filter((p) => {
      const full = `${p.Brand} ${p['Model Name']} ${p.Category} ${p['Best For']} ${p['Key Specifications']}`.toLowerCase();
      return qLower.split(' ').some((w) => w.length > 2 && full.includes(w));
    })
    .slice(0, 6);

  const productList = matchedProducts.length > 0 ? matchedProducts : products.slice(0, 5);
  const liveProductsContext = productList
    .map(
      (p) =>
        `• ${p.Brand} ${p['Model Name']} (${p.Category}): $${p.price.toFixed(2)} — Stock: ${p.stock > 0 ? `${p.stock} available` : 'OUT OF STOCK'}\n  Specs: ${p['Key Specifications']}\n  Best For: ${p['Best For']}`
    )
    .join('\n\n');

  // 3. Inspect Order & Refund Status
  let orderRefundContext = '';
  const orderIdMatch = userMessage.match(/\b(ORD-\d+)\b/i) || 
    history.slice(-4).map(h => h.content.match(/\b(ORD-\d+)\b/i)).find(Boolean);

  if (orderIdMatch) {
    const oid = orderIdMatch[1].toUpperCase();
    const evalRes = await evaluateRefund(oid);
    if (evalRes.found) {
      orderRefundContext = `[VERIFIED ORDER & REFUND ASSESSMENT from Google Sheets]:
Order ID: ${evalRes.order_id}
Customer: ${evalRes.customer}
Product: ${evalRes.model_name}
Purchase Age: ${evalRes.days_ago} days ago
Allowed Return Window: ${evalRes.allowed_days} days (${evalRes.item_type})
Current Status: ${evalRes.status}
Eligible for Refund: ${evalRes.eligible ? 'YES' : 'NO'}
Summary: ${evalRes.message}`;
    }
  }

  // 4. Check for Bank Details Submission
  let bankContext = '';
  const hasDigits = /\d{4,}/.test(userMessage);
  const hasBankWord = /\b(bank|account|acc|iban|meezan|chase|hbl|habib|ubl|mcb|nayapay|sadapay)\b/i.test(userMessage);

  if (hasDigits && hasBankWord && orderIdMatch) {
    // Extract bank details via quick LLM pass
    const bankExtractModel = genAI.getGenerativeModel({ model: 'gemini-3.5-flash-lite' });
    const extractPrompt = `Extract customer bank info from: "${userMessage}". Return strict JSON: {"bank_name": string, "account_number": string, "mobile_number": string}`;
    try {
      const extRes = await bankExtractModel.generateContent(extractPrompt);
      const cleanJson = extRes.response.text().replace(/```json|```/g, '').trim();
      const bData = JSON.parse(cleanJson);
      if (bData.account_number) {
        const oid = orderIdMatch[1].toUpperCase();
        const evalRes = await evaluateRefund(oid);
        const subRes = await submitBankDetails(
          oid,
          evalRes.customer || 'Customer',
          evalRes.model_name || 'Item',
          bData.bank_name || 'Bank',
          bData.account_number,
          bData.mobile_number || ''
        );
        bankContext = `[LIVE BANK DETAILS RECORDED IN GOOGLE SHEETS]:
Order ID: ${oid}
Customer: ${evalRes.customer}
Bank: ${bData.bank_name}
Account: ${bData.account_number}
Mobile: ${bData.mobile_number}
Google Sheets Write Status: SUCCESS
Acknowledge receipt warmly, confirm these exact details, and let the customer know their refund is now approved and will disburse within 5 business days!`;
      }
    } catch (err) {
      console.warn('Bank extraction error:', err);
    }
  }

  // 5. Check for Customer Order Placement (Buy / Order intent)
  let orderPlacementContext = '';
  let newOrderCreated = null;
  const isOrderIntent = /\b(buy|order|purchase|checkout|book|get this|place an order|want to buy|want to order)\b/i.test(userMessage) ||
    history.slice(-2).some(h => /name|place your order/i.test(h.content));

  if (isOrderIntent) {
    const orderExtractModel = genAI.getGenerativeModel({ model: 'gemini-3.5-flash-lite' });
    const extractPrompt = `Analyze if customer is placing an order:
History: ${history.slice(-3).map(h => `${h.role}: ${h.content}`).join('\n')}
Message: "${userMessage}"
Return JSON:
{"is_ordering": boolean, "product_model": string or null, "customer_name": string or null, "ready_to_place": boolean}`;

    try {
      const extRes = await orderExtractModel.generateContent(extractPrompt);
      const cleanJson = extRes.response.text().replace(/```json|```/g, '').trim();
      const oData = JSON.parse(cleanJson);

      if (oData.is_ordering && oData.ready_to_place && oData.customer_name && oData.product_model) {
        newOrderCreated = await createOrder(oData.customer_name, oData.product_model);
        orderPlacementContext = `[LIVE NEW ORDER CREATED & ADDED TO GOOGLE SHEETS]:
- New Order ID: ${newOrderCreated.order_id}
- Customer Name: ${newOrderCreated.customer}
- Model Name: ${newOrderCreated.model_name}
- Product Category: ${newOrderCreated.category} (${newOrderCreated.product})
- Price: $${newOrderCreated.price.toFixed(2)}
- Current Status: ${newOrderCreated.status}
- Google Sheets Sync: SUCCESS (Appended to live sheet)

REQUIRED RESPONSE:
1. Warmly congratulate ${newOrderCreated.customer} on placing their new order!
2. Confirm their new Order ID (${newOrderCreated.order_id}), exact Model Name (${newOrderCreated.model_name}), and price ($${newOrderCreated.price.toFixed(2)}).
3. Confirm that standard delivery takes 3-5 business days.`;
      } else if (oData.is_ordering && oData.product_model && !oData.customer_name) {
        orderPlacementContext = `[CUSTOMER ORDER IN PROGRESS - NAME NEEDED]:
The customer wants to purchase: ${oData.product_model}.
REQUIRED RESPONSE:
Confirm that this model is in our live catalog with its price. Politely ask for their full name to complete and record the order in our system right now!`;
      }
    } catch (err) {
      console.warn('Order intent extraction error:', err);
    }
  }

  // 6. Assemble Full Context-Aware System Instruction
  const systemInstruction = `You are Charlie, an expert, courteous, and proactive AI Sales, Order, and Refund Agent at TechMart Online Store.

You have four core duties:
1. **Answer Customer Inquiries in Real Time**:
   - Provide accurate product recommendations, real-time pricing, and stock status using the Live Product Catalog from Google Sheets below.
   - Clarify store policies on returns, refunds, shipping, warranties, and support using the Company Policy from our Word (.docx) document.

2. **Take Customer Orders & Update Live Google Sheets**:
   - When a customer wants to buy/order a product:
     * Check if the product model is in our live catalog and in stock.
     * If the customer has not provided their name yet, politely ask for their full name to complete the order.
     * When both product and name are given, the system registers the order into the live Google Sheet with status 'Order Placed'.
     * Confirm their Order ID (e.g. ORD-113), product model, total price, and shipping window (3-5 business days).

3. **Decide Refund Eligibility**:
   - When a customer asks about a return/refund:
     * Check the verified order assessment below.
     * **Policy Rules**: Electronics (15 days), General items (30 days), Final Sale (No returns).
     * If ELIGIBLE: Congratulate the customer, state order details, and ask for Bank Name, Account/IBAN, and Mobile Number.
     * If NOT ELIGIBLE: Politely explain why using policy rules.

4. **Handle Banking Information**:
   - When bank details are submitted, confirm receipt and reassure them that refunds are disbursed within 5 business days.

Company Policies Document (Word .docx):
${policyText}

Live Product Catalog (Google Sheets):
${liveProductsContext}

${orderRefundContext ? `Live Order Assessment:\n${orderRefundContext}\n` : ''}
${orderPlacementContext ? `Live Order Placement Status:\n${orderPlacementContext}\n` : ''}
${bankContext ? `Live Bank Status:\n${bankContext}\n` : ''}`;

  const contents = [
    { role: 'user', parts: [{ text: `[SYSTEM INSTRUCTION]\n${systemInstruction}` }] },
    { role: 'model', parts: [{ text: "Understood! I am Charlie, TechMart's AI Support Agent. How can I help you today?" }] },
    ...history.slice(-6).map((h) => ({
      role: h.role === 'user' ? 'user' : 'model',
      parts: [{ text: h.content }],
    })),
    { role: 'user', parts: [{ text: userMessage }] },
  ];

  const candidateModels = ['gemini-3.5-flash-lite', 'gemini-flash-latest', 'gemini-3.5-flash'];
  let streamResult = null;
  let lastErr = null;

  for (const mName of candidateModels) {
    try {
      const activeModel = genAI.getGenerativeModel({ model: mName });
      streamResult = await activeModel.generateContentStream({ contents });
      if (streamResult) break;
    } catch (err: any) {
      console.warn(`Model ${mName} attempt encountered an issue, trying next model:`, err.message);
      lastErr = err;
    }
  }

  if (!streamResult) {
    throw lastErr || new Error('All candidate Gemini models are currently unavailable.');
  }

  return { stream: streamResult.stream, newOrderCreated };
}

