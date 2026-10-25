import { NextResponse } from 'next/server';
import { getCompanyPolicyText, getCompanyPolicySections } from '@/lib/policy';
import path from 'path';
import fs from 'fs';

export async function GET() {
  try {
    const docxPath = path.join(process.cwd(), 'policy.docx');
    const docxExists = fs.existsSync(docxPath);
    const docxStats = docxExists ? fs.statSync(docxPath) : null;

    const fullText = await getCompanyPolicyText();
    const sections = await getCompanyPolicySections();

    return NextResponse.json({
      success: true,
      source: docxExists ? 'Word Document (policy.docx)' : 'Text Document (policy.txt)',
      filename: 'policy.docx',
      fileSizeBytes: docxStats ? docxStats.size : null,
      lastModified: docxStats ? docxStats.mtime : null,
      totalSections: sections.length,
      sections,
      fullText,
    });
  } catch (err: any) {
    console.error('Policy API Error:', err);
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
