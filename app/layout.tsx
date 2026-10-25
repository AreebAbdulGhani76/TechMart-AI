import type { Metadata } from 'next';
import './globals.css';

export const viewport = {
  width: 'device-width',
  initialScale: 1,
};

export const metadata: Metadata = {
  title: 'TechMart AI — Intelligent E-Commerce Support & Orders Agent',
  description:
    'AI-powered e-commerce support agent assisting customers with product queries, order placement, and policy-governed refund evaluations grounded in live Google Sheets and Word (.docx) policies.',
  keywords: [
    'AI Support Agent',
    'E-Commerce Assistant',
    'Next.js AI',
    'Google Sheets Integration',
    'Word docx Policy RAG',
    'Refund Automation',
  ],
  authors: [{ name: 'TechMart Intelligent AI Team' }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
