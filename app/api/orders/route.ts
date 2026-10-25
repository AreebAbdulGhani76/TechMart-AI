import { NextRequest, NextResponse } from 'next/server';
import { fetchOrders, createOrder } from '@/lib/sheets';

export async function GET() {
  try {
    const orders = await fetchOrders();
    return NextResponse.json({ success: true, orders, count: orders.length });
  } catch (err: any) {
    console.error('Orders GET API Error:', err);
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const { customer, model_name } = await req.json();
    if (!customer || !model_name) {
      return NextResponse.json({ error: 'Customer name and product model are required.' }, { status: 400 });
    }

    const newOrder = await createOrder(customer, model_name);
    return NextResponse.json({ success: true, order: newOrder });
  } catch (err: any) {
    console.error('Orders POST API Error:', err);
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
