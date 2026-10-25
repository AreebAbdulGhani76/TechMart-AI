import { NextRequest, NextResponse } from 'next/server';
import { fetchProducts } from '@/lib/sheets';

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams;
    const force = searchParams.get('force') === 'true';
    const products = await fetchProducts(force);
    return NextResponse.json({
      success: true,
      products,
      count: products.length,
      lastUpdated: new Date().toISOString(),
    });
  } catch (err: any) {
    console.error('Products API Error:', err);
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
