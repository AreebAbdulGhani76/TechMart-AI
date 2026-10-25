import fs from 'fs';
import path from 'path';
import mammoth from 'mammoth';

export interface PolicySection {
  title: string;
  content: string;
}

let cachedPolicyText: string | null = null;
let cachedPolicySections: PolicySection[] | null = null;

export async function getCompanyPolicyText(): Promise<string> {
  if (cachedPolicyText) return cachedPolicyText;

  const docxPath = path.join(process.cwd(), 'policy.docx');
  const txtPath = path.join(process.cwd(), 'policy.txt');

  // Try reading Word (.docx) first
  if (fs.existsSync(docxPath)) {
    try {
      const buffer = fs.readFileSync(docxPath);
      const result = await mammoth.extractRawText({ buffer });
      if (result.value && result.value.trim().length > 0) {
        cachedPolicyText = result.value.trim();
        return cachedPolicyText;
      }
    } catch (err) {
      console.warn('Error reading policy.docx with mammoth, falling back to txt:', err);
    }
  }

  // Fallback to policy.txt
  if (fs.existsSync(txtPath)) {
    cachedPolicyText = fs.readFileSync(txtPath, 'utf-8').trim();
    return cachedPolicyText;
  }

  return 'TechMart Policy: Electronics returnable within 15 days. General merchandise within 30 days.';
}

export async function getCompanyPolicySections(): Promise<PolicySection[]> {
  if (cachedPolicySections) return cachedPolicySections;

  const fullText = await getCompanyPolicyText();
  const rawSections = fullText.split(/\n(?=[A-Z\s]{4,30}\b)/);
  const sections: PolicySection[] = [];

  for (const raw of rawSections) {
    const trimmed = raw.trim();
    if (!trimmed) continue;
    const lines = trimmed.split('\n');
    const title = lines[0].trim();
    const content = lines.slice(1).join('\n').trim() || title;
    sections.push({ title, content });
  }

  cachedPolicySections = sections;
  return sections;
}
