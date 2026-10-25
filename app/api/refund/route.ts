import { NextRequest, NextResponse } from 'next/server';
import {
  evaluateRefund,
  submitBankDetails,
  fetchBankDetails,
  approveRefund,
  logRefundInteraction,
  fetchRefundInteractions,
} from '@/lib/sheets';

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams;
    const orderId = searchParams.get('order_id');
    const view = searchParams.get('view');

    if (view === 'interactions') {
      const interactions = await fetchRefundInteractions();
      return NextResponse.json({ success: true, interactions, count: interactions.length });
    }

    if (view === 'bank_details') {
      const bankDetails = await fetchBankDetails();
      return NextResponse.json({ success: true, bankDetails, count: bankDetails.length });
    }

    if (orderId) {
      const result = await evaluateRefund(orderId);
      return NextResponse.json({ success: true, result });
    }

    const bankDetails = await fetchBankDetails();
    return NextResponse.json({ success: true, bankDetails, count: bankDetails.length });
  } catch (err: any) {
    console.error('Refund GET API Error:', err);
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      action,
      order_id,
      customer,
      product,
      bank_name,
      account_number,
      mobile_number,
      email,
      customer_email,
    } = body;

    const targetEmail = email || customer_email;

    if (action === 'evaluate' || (!action && order_id && !account_number && !action)) {
      if (!order_id) {
        return NextResponse.json({ error: 'order_id is required' }, { status: 400 });
      }
      const evalResult = await evaluateRefund(order_id);
      return NextResponse.json({ success: true, result: evalResult });
    }

    if (action === 'approve') {
      if (!order_id) {
        return NextResponse.json({ error: 'order_id is required for approval' }, { status: 400 });
      }
      const res = await approveRefund(order_id, targetEmail);
      return NextResponse.json({ success: true, result: res });
    }

    if (action === 'submit_bank' || (order_id && account_number)) {
      if (!order_id || !account_number || !bank_name) {
        return NextResponse.json(
          { error: 'order_id, bank_name, and account_number are required' },
          { status: 400 }
        );
      }
      const res = await submitBankDetails(
        order_id,
        customer || 'Customer',
        product || 'Product',
        bank_name,
        account_number,
        mobile_number || '',
        targetEmail
      );
      return NextResponse.json({ success: true, result: res });
    }

    return NextResponse.json({ error: 'Invalid request action or parameters' }, { status: 400 });
  } catch (err: any) {
    console.error('Refund POST API Error:', err);
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
