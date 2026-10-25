import fs from 'fs';
import path from 'path';
import { google } from 'googleapis';
import * as XLSX from 'xlsx';
import { sendRefundConfirmationEmail, sendOrderConfirmationEmail } from './email';

export const PRODUCTS_SHEET_ID = process.env.PRODUCTS_SHEET_ID || '1RZ1U4TKfqqjY4kpbvFUQOJd_PwDlYp0I';
export const ORDERS_SHEET_ID = process.env.ORDERS_SHEET_ID || '18G2BQlwSihkgC5JcCFosbMVEbSQBQE_hgvKpFogcWCI';
export const BANK_DETAILS_SHEET_ID = process.env.BANK_DETAILS_SHEET_ID || '1gWgVsSVU4u1V8qTcEIKj7F81XxY02Y-0sJCdc-J6gNg';

export interface ProductItem {
  Category: string;
  Brand: string;
  'Model Name': string;
  'Key Specifications': string;
  'Best For': string;
  price: number;
  stock: number;
}

export interface OrderItem {
  _row_number?: number;
  order_id: string;
  customer: string;
  'Model Name': string;
  product: string;
  category: string;
  days_ago: string | number;
  Status: string;
  Email?: string;
  email?: string;
}

export interface BankDetailItem {
  order_id: string;
  customer: string;
  product: string;
  Bank_Name: string;
  'Account Number': string;
  'Mobile Number': string;
}

export interface RefundInteractionItem {
  timestamp: string;
  order_id: string;
  customer: string;
  product: string;
  refund_status: string;
  email_sent_to: string;
  interaction_notes: string;
}

let cachedAuth: any = null;
let cachedProducts: ProductItem[] | null = null;
let lastProductsFetchTime = 0;
const CACHE_TTL = 60000; // 1 minute

function getServiceAccountCredentials() {
  // 1. Direct JSON string in environment variable
  if (process.env.GOOGLE_SERVICE_ACCOUNT_JSON) {
    try {
      return JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON);
    } catch (e) {
      console.warn('Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON from environment:', e);
    }
  }

  // 2. File path configured via GOOGLE_APPLICATION_CREDENTIALS
  if (process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    const envPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
    const resolvedPath = path.isAbsolute(envPath) ? envPath : path.join(process.cwd(), envPath);
    if (fs.existsSync(resolvedPath)) {
      const raw = fs.readFileSync(resolvedPath, 'utf-8');
      return JSON.parse(raw);
    }
  }

  // 3. Fallback to scanning for local service account JSON file in workspace
  const root = process.cwd();
  const files = fs.readdirSync(root);
  const credsFile = files.find(
    (f) =>
      (f.startsWith('leads-data-') || f.includes('serviceaccount') || f.includes('credentials')) &&
      f.endsWith('.json')
  );

  if (credsFile) {
    const raw = fs.readFileSync(path.join(root, credsFile), 'utf-8');
    return JSON.parse(raw);
  }

  throw new Error('No Google Service Account credentials JSON file found in project or configured in environment.');
}

export function getAuthorizedClient() {
  if (cachedAuth) return cachedAuth;
  const creds = getServiceAccountCredentials();
  cachedAuth = new google.auth.JWT({
    email: creds.client_email,
    key: creds.private_key,
    scopes: [
      'https://www.googleapis.com/auth/spreadsheets',
      'https://www.googleapis.com/auth/drive.readonly',
    ],
  });
  return cachedAuth;
}

export async function fetchProducts(forceRefresh = false): Promise<ProductItem[]> {
  const now = Date.now();
  if (!forceRefresh && cachedProducts && now - lastProductsFetchTime < CACHE_TTL) {
    return cachedProducts;
  }

  const auth = getAuthorizedClient();
  const token = await auth.authorize();
  const url = `https://docs.google.com/spreadsheets/d/${PRODUCTS_SHEET_ID}/export?format=xlsx`;

  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token.access_token}` },
  });

  if (!resp.ok) {
    throw new Error(`Failed to fetch products sheet: HTTP ${resp.status}`);
  }

  const arrayBuffer = await resp.arrayBuffer();
  const workbook = XLSX.read(Buffer.from(arrayBuffer), { type: 'buffer' });
  const firstSheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[firstSheetName];
  const jsonData = XLSX.utils.sheet_to_json<any>(worksheet);

  const cleanProducts: ProductItem[] = jsonData.map((row) => ({
    Category: String(row.Category || '').trim(),
    Brand: String(row.Brand || '').trim(),
    'Model Name': String(row['Model Name'] || '').trim(),
    'Key Specifications': String(row['Key Specifications'] || '').trim(),
    'Best For': String(row['Best For'] || '').trim(),
    price: parseFloat(row.price || 0) || 0,
    stock: parseInt(row.stock || 0, 10) || 0,
  }));

  cachedProducts = cleanProducts;
  lastProductsFetchTime = now;
  return cleanProducts;
}

export async function fetchOrders(): Promise<OrderItem[]> {
  const auth = getAuthorizedClient();
  const sheets = google.sheets({ version: 'v4', auth });

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: ORDERS_SHEET_ID,
    range: 'Sheet1!A:Z',
  });

  const rows = res.data.values || [];
  if (rows.length < 2) return [];

  const headers = rows[0].map((h: any) => String(h).trim());
  const orders: OrderItem[] = [];

  for (let idx = 1; idx < rows.length; idx++) {
    const r = rows[idx];
    const item: any = { _row_number: idx + 1 };
    headers.forEach((h: string, colIdx: number) => {
      item[h] = r[colIdx] ? String(r[colIdx]).trim() : '';
    });
    // Ensure both 'email' and 'Email' are set from column H or header
    const emailVal = item.Email || item.email || (r[7] ? String(r[7]).trim() : '');
    item.Email = emailVal;
    item.email = emailVal;
    orders.push(item as OrderItem);
  }

  return orders;
}

export async function createOrder(customer: string, modelName: string, email?: string): Promise<any> {
  const auth = getAuthorizedClient();
  const sheets = google.sheets({ version: 'v4', auth });

  const existingOrders = await fetchOrders();
  let maxNum = 100;
  for (const o of existingOrders) {
    const match = (o.order_id || '').match(/ORD-(\d+)/i);
    if (match) {
      const n = parseInt(match[1], 10);
      if (n > maxNum) maxNum = n;
    }
  }
  const nextOrderId = `ORD-${maxNum + 1}`;

  // Find product details
  const products = await fetchProducts();
  const matchedProd = products.find(
    (p) =>
      p['Model Name'].toLowerCase() === modelName.toLowerCase() ||
      `${p.Brand} ${p['Model Name']}`.toLowerCase().includes(modelName.toLowerCase()) ||
      modelName.toLowerCase().includes(p['Model Name'].toLowerCase())
  );

  const resolvedModel = matchedProd ? matchedProd['Model Name'] : modelName;
  const resolvedProduct = matchedProd ? matchedProd.Category.toLowerCase() : 'laptop';
  const resolvedCategory = 'electronics';
  const price = matchedProd ? matchedProd.price : 0.0;
  const stock = matchedProd ? matchedProd.stock : 0;
  const customerEmail = (email || '').trim();

  // Columns: order_id, customer, Model Name, product, category, days_ago, Status, Email
  const row = [
    nextOrderId,
    customer.trim(),
    resolvedModel,
    resolvedProduct,
    resolvedCategory,
    '0',
    'Order Placed',
    customerEmail,
  ];

  const appendRes = await sheets.spreadsheets.values.append({
    spreadsheetId: ORDERS_SHEET_ID,
    range: 'Sheet1!A:H',
    valueInputOption: 'USER_ENTERED',
    requestBody: { values: [row] },
  });

  // Automated order confirmation email dispatch
  let emailResult = null;
  if (customerEmail && customerEmail.includes('@')) {
    try {
      emailResult = await sendOrderConfirmationEmail({
        orderId: nextOrderId,
        customer: customer.trim(),
        modelName: resolvedModel,
        category: resolvedCategory,
        price,
        customerEmail,
      });
    } catch (err) {
      console.warn('[ORDER EMAIL DISPATCH ERROR]:', err);
    }
  }

  return {
    success: appendRes.status === 200,
    order_id: nextOrderId,
    customer: customer.trim(),
    model_name: resolvedModel,
    product: resolvedProduct,
    category: resolvedCategory,
    price,
    stock,
    status: 'Order Placed',
    email: customerEmail,
    email_status: emailResult?.status,
    email_reference: emailResult?.reference,
    preview_url: emailResult?.previewUrl || '',
  };
}

export async function evaluateRefund(orderId: string): Promise<any> {
  const orders = await fetchOrders();
  const target = orders.find((o) => o.order_id.toLowerCase() === orderId.toLowerCase());
  if (!target) {
    return { found: false, message: `Order ${orderId} was not found in the live orders database.` };
  }

  const daysAgo = parseInt(String(target.days_ago || '0'), 10) || 0;
  const isElectronics =
    target.category.toLowerCase().includes('electronic') ||
    ['laptop', 'phone', 'tablet', 'headphone', 'keyboard'].some((k) =>
      (target.product + ' ' + target['Model Name']).toLowerCase().includes(k)
    );

  const allowedDays = isElectronics ? 15 : 30;
  const eligible = daysAgo <= allowedDays;

  return {
    found: true,
    order_id: target.order_id,
    customer: target.customer,
    model_name: target['Model Name'],
    days_ago: daysAgo,
    allowed_days: allowedDays,
    eligible,
    status: target.Status || 'Pending',
    email: target.email || target.Email || '',
    item_type: isElectronics ? 'Electronics (15-day limit)' : 'General Merchandise (30-day limit)',
    message: eligible
      ? `Order ${target.order_id} is within the ${allowedDays}-day return window and is ELIGIBLE for a refund.`
      : `Order ${target.order_id} was purchased ${daysAgo} days ago, which exceeds the ${allowedDays}-day return window.`,
  };
}

export async function logRefundInteraction(params: {
  orderId: string;
  customer: string;
  product: string;
  refundStatus: string;
  emailSentTo?: string;
  notes?: string;
}): Promise<any> {
  const auth = getAuthorizedClient();
  const sheets = google.sheets({ version: 'v4', auth });

  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  const row = [
    timestamp,
    params.orderId,
    params.customer,
    params.product,
    params.refundStatus,
    params.emailSentTo || 'N/A',
    params.notes || '',
  ];

  try {
    const appendRes = await sheets.spreadsheets.values.append({
      spreadsheetId: ORDERS_SHEET_ID,
      range: 'Refund_Interactions!A:G',
      valueInputOption: 'USER_ENTERED',
      requestBody: { values: [row] },
    });
    return { success: appendRes.status === 200, row };
  } catch (err: any) {
    console.warn('Failed to append to Refund_Interactions sheet:', err.message);
    return { success: false, error: err.message };
  }
}

export async function submitBankDetails(
  orderId: string,
  customer: string,
  product: string,
  bankName: string,
  accountNumber: string,
  mobileNumber: string,
  email?: string
): Promise<any> {
  const auth = getAuthorizedClient();
  const sheets = google.sheets({ version: 'v4', auth });

  const row = [orderId, customer, product, bankName, accountNumber, mobileNumber];

  const appendRes = await sheets.spreadsheets.values.append({
    spreadsheetId: BANK_DETAILS_SHEET_ID,
    range: 'Sheet1!A:F',
    valueInputOption: 'USER_ENTERED',
    requestBody: { values: [row] },
  });

  // Also update order status in orders sheet
  const orders = await fetchOrders();
  const target = orders.find((o) => o.order_id.toLowerCase() === orderId.toLowerCase());
  const effectiveEmail = (email && email.includes('@'))
    ? email.trim()
    : (target?.email || target?.Email || '');

  if (target && target._row_number) {
    await sheets.spreadsheets.values.update({
      spreadsheetId: ORDERS_SHEET_ID,
      range: `Sheet1!G${target._row_number}`,
      valueInputOption: 'USER_ENTERED',
      requestBody: { values: [['Return Approved']] },
    });

    if (effectiveEmail && effectiveEmail.includes('@')) {
      await sheets.spreadsheets.values.update({
        spreadsheetId: ORDERS_SHEET_ID,
        range: `Sheet1!H${target._row_number}`,
        valueInputOption: 'USER_ENTERED',
        requestBody: { values: [[effectiveEmail]] },
      });
    }
  }

  // 1. Send automated refund confirmation email
  const emailRes = await sendRefundConfirmationEmail({
    orderId,
    customer,
    product,
    customerEmail: effectiveEmail || undefined,
    daysAgo: target?.days_ago || '5',
    bankName,
    accountNumber,
  });

  // 2. Store interaction and refund status in Google Sheets (Refund_Interactions tab)
  await logRefundInteraction({
    orderId,
    customer,
    product,
    refundStatus: 'Return Approved',
    emailSentTo: emailRes.recipient,
    notes: `Refund approved with banking details. Automated confirmation email sent (Ref: ${emailRes.reference}).`,
  });

  return {
    success: appendRes.status === 200,
    order_id: orderId,
    customer,
    product,
    bank_name: bankName,
    account_number: accountNumber,
    mobile_number: mobileNumber,
    email: emailRes.recipient,
    email_status: emailRes.status,
    email_reference: emailRes.reference,
    preview_url: emailRes.previewUrl || '',
  };
}

export async function approveRefund(orderId: string, customerEmail?: string): Promise<any> {
  const evalRes = await evaluateRefund(orderId);
  if (!evalRes.found) {
    return { success: false, message: 'Order not found' };
  }

  const auth = getAuthorizedClient();
  const sheets = google.sheets({ version: 'v4', auth });

  const orders = await fetchOrders();
  const target = orders.find((o) => o.order_id.toLowerCase() === orderId.toLowerCase());
  const effectiveEmail = (customerEmail && customerEmail.includes('@'))
    ? customerEmail.trim()
    : (target?.email || target?.Email || '');

  if (target && target._row_number) {
    await sheets.spreadsheets.values.update({
      spreadsheetId: ORDERS_SHEET_ID,
      range: `Sheet1!G${target._row_number}`,
      valueInputOption: 'USER_ENTERED',
      requestBody: { values: [['Return Approved']] },
    });

    if (effectiveEmail && effectiveEmail.includes('@')) {
      await sheets.spreadsheets.values.update({
        spreadsheetId: ORDERS_SHEET_ID,
        range: `Sheet1!H${target._row_number}`,
        valueInputOption: 'USER_ENTERED',
        requestBody: { values: [[effectiveEmail]] },
      });
    }
  }

  // Send automated confirmation email
  const emailRes = await sendRefundConfirmationEmail({
    orderId: evalRes.order_id,
    customer: evalRes.customer,
    product: evalRes.model_name,
    customerEmail: effectiveEmail || undefined,
    daysAgo: evalRes.days_ago,
    allowedDays: evalRes.allowed_days,
  });

  // Store interaction and refund status in Google Sheets
  await logRefundInteraction({
    orderId: evalRes.order_id,
    customer: evalRes.customer,
    product: evalRes.model_name,
    refundStatus: 'Return Approved',
    emailSentTo: emailRes.recipient,
    notes: `Refund approved under ${evalRes.item_type}. Automated confirmation email sent (Ref: ${emailRes.reference}).`,
  });

  return {
    success: true,
    order_id: evalRes.order_id,
    customer: evalRes.customer,
    product: evalRes.model_name,
    status: 'Return Approved',
    email: emailRes.recipient,
    email_status: emailRes.status,
    email_reference: emailRes.reference,
    preview_url: emailRes.previewUrl || '',
  };
}

export async function updateOrderEmail(orderId: string, email: string): Promise<any> {
  const auth = getAuthorizedClient();
  const sheets = google.sheets({ version: 'v4', auth });
  const orders = await fetchOrders();
  const target = orders.find((o) => o.order_id.toLowerCase() === orderId.toLowerCase());
  if (!target || !target._row_number) {
    return { success: false, message: `Order ${orderId} not found.` };
  }
  const cleanEmail = email.trim();
  const res = await sheets.spreadsheets.values.update({
    spreadsheetId: ORDERS_SHEET_ID,
    range: `Sheet1!H${target._row_number}`,
    valueInputOption: 'USER_ENTERED',
    requestBody: { values: [[cleanEmail]] },
  });
  return { success: res.status === 200, order_id: orderId, email: cleanEmail };
}

export async function fetchRefundInteractions(): Promise<RefundInteractionItem[]> {
  try {
    const auth = getAuthorizedClient();
    const sheets = google.sheets({ version: 'v4', auth });

    const res = await sheets.spreadsheets.values.get({
      spreadsheetId: ORDERS_SHEET_ID,
      range: 'Refund_Interactions!A:G',
    });

    const rows = res.data.values || [];
    if (rows.length < 2) return [];

    const interactions: RefundInteractionItem[] = [];
    for (let idx = 1; idx < rows.length; idx++) {
      const r = rows[idx];
      interactions.push({
        timestamp: r[0] ? String(r[0]).trim() : '',
        order_id: r[1] ? String(r[1]).trim() : '',
        customer: r[2] ? String(r[2]).trim() : '',
        product: r[3] ? String(r[3]).trim() : '',
        refund_status: r[4] ? String(r[4]).trim() : '',
        email_sent_to: r[5] ? String(r[5]).trim() : '',
        interaction_notes: r[6] ? String(r[6]).trim() : '',
      });
    }

    return interactions;
  } catch (err) {
    console.warn('Error fetching refund interactions:', err);
    return [];
  }
}

export async function fetchBankDetails(): Promise<BankDetailItem[]> {
  const auth = getAuthorizedClient();
  const sheets = google.sheets({ version: 'v4', auth });

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: BANK_DETAILS_SHEET_ID,
    range: 'Sheet1!A:F',
  });

  const rows = res.data.values || [];
  if (rows.length < 2) return [];

  const headers = rows[0].map((h: any) => String(h).trim());
  const details: BankDetailItem[] = [];

  for (let idx = 1; idx < rows.length; idx++) {
    const r = rows[idx];
    const item: any = {};
    headers.forEach((h: string, colIdx: number) => {
      item[h] = r[colIdx] ? String(r[colIdx]).trim() : '';
    });
    details.push(item as BankDetailItem);
  }

  return details;
}
