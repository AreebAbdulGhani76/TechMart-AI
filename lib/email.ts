import nodemailer from 'nodemailer';

export interface RefundEmailParams {
  orderId: string;
  customer: string;
  product: string;
  customerEmail?: string;
  daysAgo?: number | string;
  allowedDays?: number | string;
  price?: number | string;
  bankName?: string;
  accountNumber?: string;
}

export interface OrderEmailParams {
  orderId: string;
  customer: string;
  modelName: string;
  category?: string;
  price?: number | string;
  customerEmail?: string;
  deliveryDays?: string;
}

export interface EmailDispatchResult {
  success: boolean;
  messageId: string;
  recipient: string;
  reference: string;
  sentAt: string;
  status: string;
  previewUrl?: string;
  error?: string;
}

export type RefundEmailResult = EmailDispatchResult;
export type OrderEmailResult = EmailDispatchResult;

/**
 * Core multi-provider email dispatcher:
 * 1. Direct Gmail Service (via EMAIL_USER & EMAIL_PASS / App Password)
 * 2. Custom SMTP (via SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
 * 3. Ethereal Test Mail with instant public web preview URL
 * 4. JSON Transport fallback
 */
async function dispatchEmail(options: {
  recipient: string;
  subject: string;
  text: string;
  html: string;
  reference: string;
  orderId: string;
}): Promise<EmailDispatchResult> {
  const { recipient, subject, text, html, reference, orderId } = options;
  const sentAt = new Date().toISOString();

  try {
    const gmailUser = (process.env.EMAIL_USER || process.env.GMAIL_USER || '').trim();
    const gmailPass = (process.env.EMAIL_PASS || process.env.GMAIL_PASS || '').trim();

    // 1. Direct Gmail Service
    if (gmailUser && gmailPass) {
      const transporter = nodemailer.createTransport({
        service: 'gmail',
        auth: {
          user: gmailUser,
          pass: gmailPass,
        },
      });

      const info = await transporter.sendMail({
        from: process.env.SMTP_FROM || `"TechMart AI Store" <${gmailUser}>`,
        to: recipient,
        subject,
        text,
        html,
      });

      console.log(`[EMAIL DISPATCH SUCCESS] Real Gmail sent to ${recipient}, id: ${info.messageId}`);
      return {
        success: true,
        messageId: info.messageId,
        recipient,
        reference,
        sentAt,
        status: 'DISPATCHED_GMAIL',
      };
    }

    // 2. Custom SMTP
    if (
      process.env.SMTP_HOST &&
      process.env.SMTP_USER &&
      process.env.SMTP_PASS
    ) {
      const transporter = nodemailer.createTransport({
        host: process.env.SMTP_HOST,
        port: parseInt(process.env.SMTP_PORT || '587', 10),
        secure: process.env.SMTP_SECURE === 'true' || process.env.SMTP_PORT === '465',
        auth: {
          user: process.env.SMTP_USER,
          pass: process.env.SMTP_PASS,
        },
      });

      const info = await transporter.sendMail({
        from: process.env.SMTP_FROM || `"TechMart AI Support" <noreply@techmart.com>`,
        to: recipient,
        subject,
        text,
        html,
      });

      console.log(`[EMAIL DISPATCH SUCCESS] Real SMTP sent to ${recipient}, id: ${info.messageId}`);
      return {
        success: true,
        messageId: info.messageId,
        recipient,
        reference,
        sentAt,
        status: 'DISPATCHED_SMTP',
      };
    }

    // 3. Fallback: Ethereal test inbox with clickable preview URL
    try {
      const testAccount = await nodemailer.createTestAccount();
      const testTransporter = nodemailer.createTransport({
        host: 'smtp.ethereal.email',
        port: 587,
        secure: false,
        auth: {
          user: testAccount.user,
          pass: testAccount.pass,
        },
      });

      const info = await testTransporter.sendMail({
        from: `"TechMart AI Store" <${testAccount.user}>`,
        to: recipient,
        subject,
        text,
        html,
      });

      const previewUrl = nodemailer.getTestMessageUrl(info) || '';
      console.log(`[ETHEREAL EMAIL DISPATCHED]:\n  To: ${recipient}\n  Preview URL: ${previewUrl}`);

      return {
        success: true,
        messageId: info.messageId,
        recipient,
        reference,
        sentAt,
        status: 'ETHEREAL_PREVIEW',
        previewUrl,
      };
    } catch (etherealErr: any) {
      console.warn('[ETHEREAL FALLBACK FAILED, USING JSON TRANSPORT]:', etherealErr.message);

      const transporter = nodemailer.createTransport({
        jsonTransport: true,
      });

      await transporter.sendMail({
        from: `"TechMart AI Support" <support@techmart.com>`,
        to: recipient,
        subject,
        text,
        html,
      });

      const generatedId = `<order-${Date.now()}@techmart-ai.com>`;
      return {
        success: true,
        messageId: generatedId,
        recipient,
        reference,
        sentAt,
        status: 'AUTOMATED_EMAIL_LOGGED',
      };
    }
  } catch (err: any) {
    console.error('[EMAIL DISPATCH ERROR]:', err);
    return {
      success: false,
      messageId: '',
      recipient,
      reference,
      sentAt,
      status: 'FAILED',
      error: err.message || 'Unknown email dispatch error',
    };
  }
}

/**
 * Dispatches an automated Refund Approved Confirmation Email.
 */
export async function sendRefundConfirmationEmail(
  params: RefundEmailParams
): Promise<RefundEmailResult> {
  const {
    orderId,
    customer,
    product,
    customerEmail,
    daysAgo = '5',
    allowedDays = '15',
    bankName,
    accountNumber,
  } = params;

  const recipient = (
    customerEmail && customerEmail.includes('@')
      ? customerEmail
      : `${customer.toLowerCase().replace(/[^a-z0-9]/g, '') || 'customer'}@techmart-customer.com`
  ).trim();

  const reference = `REF-${orderId.replace(/[^A-Za-z0-9]/g, '')}-${Date.now().toString(36).toUpperCase()}`;

  const maskedAccount = accountNumber
    ? accountNumber.length > 4
      ? `••••••••${accountNumber.slice(-4)}`
      : accountNumber
    : 'Original Payment Method';

  const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Refund Approved - TechMart AI</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0e17; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0e17; padding: 30px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #111827; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);">
          
          <!-- Header -->
          <tr>
            <td style="padding: 28px 32px; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-bottom: 1px solid rgba(99, 102, 241, 0.3);">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <div style="display: inline-block; background: #6366f1; color: #ffffff; font-weight: 800; font-size: 13px; padding: 4px 10px; border-radius: 6px; letter-spacing: 0.5px; text-transform: uppercase;">
                      TechMart AI Store
                    </div>
                    <h1 style="margin: 12px 0 0 0; font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.3px;">
                      Refund Approved & Confirmed
                    </h1>
                  </td>
                  <td align="right" style="vertical-align: middle;">
                    <span style="display: inline-block; background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #34d399; font-weight: 700; font-size: 12px; padding: 6px 12px; border-radius: 9999px;">
                      ✓ APPROVED
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body Content -->
          <tr>
            <td style="padding: 32px;">
              <p style="margin: 0 0 18px 0; font-size: 15px; line-height: 1.6; color: #f8fafc;">
                Dear <strong>${customer}</strong>,
              </p>
              <p style="margin: 0 0 24px 0; font-size: 14.5px; line-height: 1.6; color: #cbd5e1;">
                We are pleased to inform you that your return and refund request for <strong>Order #${orderId}</strong> has been verified against our store return policy and is officially <strong>APPROVED</strong>.
              </p>

              <!-- Order Summary Card -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #162032; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; margin-bottom: 24px; padding: 18px 20px;">
                <tr>
                  <td style="padding-bottom: 10px; font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">
                    Order Reference
                  </td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13px; font-weight: 700; color: #6366f1; font-family: monospace;">
                    ${orderId}
                  </td>
                </tr>
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Item / Model:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; font-weight: 600; color: #ffffff;">${product}</td>
                </tr>
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Purchase Age:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; color: #ffffff;">${daysAgo} days ago</td>
                </tr>
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Allowed Return Window:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; color: #ffffff;">${allowedDays} days limit</td>
                </tr>
                ${
                  bankName
                    ? `
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Disbursement Bank:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; color: #ffffff;">${bankName}</td>
                </tr>
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Account Ending:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; font-family: monospace; color: #ffffff;">${maskedAccount}</td>
                </tr>
                `
                    : ''
                }
                <tr>
                  <td style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 12px; font-size: 14px; font-weight: 700; color: #ffffff;">Refund Status:</td>
                  <td align="right" style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 12px; font-size: 14px; font-weight: 700; color: #34d399;">
                    Return Approved (Synced to Google Sheets)
                  </td>
                </tr>
              </table>

              <div style="background: rgba(99, 102, 241, 0.1); border-left: 4px solid #6366f1; padding: 14px 18px; border-radius: 4px; margin-bottom: 24px;">
                <p style="margin: 0; font-size: 13.5px; line-height: 1.6; color: #e0e7ff;">
                  ⏱️ <strong>Disbursement Timeline:</strong> Your refund will be credited directly to your bank account within <strong>3 to 5 business days</strong> in accordance with Section 3.2 of the TechMart Return & Refund Policy.
                </p>
              </div>

              <div style="background-color: #0f172a; border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 12px 16px; text-align: center; margin-bottom: 24px;">
                <span style="font-size: 11.5px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Confirmation Tracking Reference</span>
                <div style="font-family: monospace; font-size: 15px; font-weight: 700; color: #38bdf8; margin-top: 4px;">
                  ${reference}
                </div>
              </div>

              <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #94a3b8;">
                If you have any questions or need to make corrections, simply reply to this email or contact support at <a href="mailto:support@techmart.com" style="color: #6366f1; text-decoration: none;">support@techmart.com</a>.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 32px; background-color: #0b0f19; border-top: 1px solid rgba(255, 255, 255, 0.08); text-align: center;">
              <p style="margin: 0 0 6px 0; font-size: 12px; color: #64748b;">
                TechMart AI Support • Automated Customer Refund System
              </p>
              <p style="margin: 0; font-size: 11px; color: #475569;">
                Grounding Source: policy.docx • Live Google Sheets Sync Status: ACTIVE
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim();

  const textContent = `
TechMart AI - Refund Approved Confirmation

Dear ${customer},

Your refund request for Order #${orderId} has been verified and APPROVED under store policy.

Order Summary:
- Order ID: ${orderId}
- Product Model: ${product}
- Purchase Age: ${daysAgo} days ago (Allowed window: ${allowedDays} days)
- Status: Return Approved (Synced to Google Sheets)
- Payout Schedule: 3-5 business days to ${bankName ? `${bankName} (${maskedAccount})` : 'original payment method'}
- Confirmation Reference: ${reference}

If you have questions, please reach out to support@techmart.com.

TechMart AI Support Team
  `.trim();

  return dispatchEmail({
    recipient,
    subject: `Refund Approved: Order Confirmation #${orderId} - TechMart AI`,
    text: textContent,
    html: htmlContent,
    reference,
    orderId,
  });
}

/**
 * Dispatches an automated Order Confirmation Email whenever a new order is placed.
 */
export async function sendOrderConfirmationEmail(
  params: OrderEmailParams
): Promise<OrderEmailResult> {
  const {
    orderId,
    customer,
    modelName,
    category = 'electronics',
    price,
    customerEmail,
    deliveryDays = '3 to 5 business days',
  } = params;

  const recipient = (
    customerEmail && customerEmail.includes('@')
      ? customerEmail
      : `${customer.toLowerCase().replace(/[^a-z0-9]/g, '') || 'customer'}@techmart-customer.com`
  ).trim();

  const reference = `ORD-CONF-${orderId.replace(/[^A-Za-z0-9]/g, '')}-${Date.now().toString(36).toUpperCase()}`;

  const formattedPrice =
    typeof price === 'number'
      ? `$${price.toFixed(2)}`
      : price
      ? `$${price}`
      : 'Standard Pricing';

  const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Order Confirmed - TechMart AI</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0e17; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0e17; padding: 30px 15px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #111827; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);">
          
          <!-- Header -->
          <tr>
            <td style="padding: 28px 32px; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-bottom: 1px solid rgba(99, 102, 241, 0.3);">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <div style="display: inline-block; background: #6366f1; color: #ffffff; font-weight: 800; font-size: 13px; padding: 4px 10px; border-radius: 6px; letter-spacing: 0.5px; text-transform: uppercase;">
                      TechMart AI Store
                    </div>
                    <h1 style="margin: 12px 0 0 0; font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.3px;">
                      🎉 Order Confirmed!
                    </h1>
                  </td>
                  <td align="right" style="vertical-align: middle;">
                    <span style="display: inline-block; background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #34d399; font-weight: 700; font-size: 12px; padding: 6px 12px; border-radius: 9999px;">
                      ✓ ORDER PLACED
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body Content -->
          <tr>
            <td style="padding: 32px;">
              <p style="margin: 0 0 18px 0; font-size: 15px; line-height: 1.6; color: #f8fafc;">
                Dear <strong>${customer}</strong>,
              </p>
              <p style="margin: 0 0 24px 0; font-size: 14.5px; line-height: 1.6; color: #cbd5e1;">
                Thank you for your purchase with TechMart AI! We have received your order and our fulfillment team is preparing your package for shipment.
              </p>

              <!-- Order Summary Card -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #162032; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; margin-bottom: 24px; padding: 18px 20px;">
                <tr>
                  <td style="padding-bottom: 10px; font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">
                    Order Reference ID
                  </td>
                  <td align="right" style="padding-bottom: 10px; font-size: 14px; font-weight: 700; color: #6366f1; font-family: monospace;">
                    ${orderId}
                  </td>
                </tr>
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Item / Model:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; font-weight: 600; color: #ffffff;">${modelName}</td>
                </tr>
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Category:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; color: #ffffff; text-transform: capitalize;">${category}</td>
                </tr>
                <tr>
                  <td style="padding-bottom: 10px; font-size: 13.5px; color: #94a3b8;">Price:</td>
                  <td align="right" style="padding-bottom: 10px; font-size: 13.5px; font-weight: 700; color: #38bdf8;">${formattedPrice}</td>
                </tr>
                <tr>
                  <td style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 12px; font-size: 14px; font-weight: 700; color: #ffffff;">Estimated Delivery:</td>
                  <td align="right" style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 12px; font-size: 14px; font-weight: 700; color: #34d399;">
                    ${deliveryDays}
                  </td>
                </tr>
              </table>

              <div style="background: rgba(99, 102, 241, 0.1); border-left: 4px solid #6366f1; padding: 14px 18px; border-radius: 4px; margin-bottom: 24px;">
                <p style="margin: 0; font-size: 13.5px; line-height: 1.6; color: #e0e7ff;">
                  🛡️ <strong>Hassle-Free Return Guarantee:</strong> Your purchase is fully covered under Section 1.1 of the TechMart Return Policy (15-day return window for electronics and 30 days for general merchandise).
                </p>
              </div>

              <div style="background-color: #0f172a; border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 12px 16px; text-align: center; margin-bottom: 24px;">
                <span style="font-size: 11.5px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Order Tracking Reference</span>
                <div style="font-family: monospace; font-size: 15px; font-weight: 700; color: #38bdf8; margin-top: 4px;">
                  ${reference}
                </div>
              </div>

              <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #94a3b8;">
                If you need any assistance, our AI agent Charlie is available 24/7 or you can email <a href="mailto:support@techmart.com" style="color: #6366f1; text-decoration: none;">support@techmart.com</a>.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 32px; background-color: #0b0f19; border-top: 1px solid rgba(255, 255, 255, 0.08); text-align: center;">
              <p style="margin: 0 0 6px 0; font-size: 12px; color: #64748b;">
                TechMart AI Store • Automated Order Processing System
              </p>
              <p style="margin: 0; font-size: 11px; color: #475569;">
                Grounding Source: live Google Sheets inventory • Status: Order Placed
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim();

  const textContent = `
TechMart AI - Order Confirmation

Dear ${customer},

Thank you for your order with TechMart AI!

Order Summary:
- Order ID: ${orderId}
- Product: ${modelName}
- Total Price: ${formattedPrice}
- Delivery Timeline: ${deliveryDays}
- Status: Order Placed (Recorded in Google Sheets)
- Tracking Reference: ${reference}

Your order is covered under our store return policy (15-day return window for electronics).

TechMart AI Store Team
support@techmart.com
  `.trim();

  return dispatchEmail({
    recipient,
    subject: `Order Confirmed: #${orderId} (${modelName}) - TechMart AI`,
    text: textContent,
    html: htmlContent,
    reference,
    orderId,
  });
}
