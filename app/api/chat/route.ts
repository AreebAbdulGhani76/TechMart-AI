import { NextRequest, NextResponse } from 'next/server';
import { processAgentChat } from '@/lib/gemini';

export async function POST(req: NextRequest) {
  try {
    const { message, history, apiKey } = await req.json();

    if (!message || typeof message !== 'string') {
      return NextResponse.json({ error: 'Message is required.' }, { status: 400 });
    }

    const { stream, newOrderCreated } = await processAgentChat(message, history || [], apiKey);

    const encoder = new TextEncoder();
    const readable = new ReadableStream({
      async start(controller) {
        try {
          for await (const chunk of (stream as AsyncIterable<any>)) {
            const text = chunk.text();
            controller.enqueue(encoder.encode(text));
          }
          controller.close();
        } catch (err: any) {
          controller.error(err);
        }
      },
    });

    return new Response(readable, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'X-New-Order': newOrderCreated ? JSON.stringify(newOrderCreated) : '',
      },
    });
  } catch (err: any) {
    console.error('Chat API Error:', err);
    return NextResponse.json(
      { error: err.message || 'Internal server error processing agent query.' },
      { status: 500 }
    );
  }
}
