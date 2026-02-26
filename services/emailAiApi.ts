/**
 * Email AI Agent API service — frontend client for the AI email management system.
 */

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/$/, '');

const adminHeaders = (token: string) => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`,
  'ngrok-skip-browser-warning': 'true',
});

// ── Types ──

export interface EmailDraft {
  id: string;
  type: string;
  to: string;
  subject: string;
  body: string;
  target_type?: string;
  campaign_id?: string;
  timestamp: string;
}

export interface InboxMessage {
  gmail_id: string;
  thread_id: string;
  from_addr: string;
  to: string;
  subject: string;
  date: string;
  body: string;
  snippet: string;
  labels: string[];
}

export interface MemoryResult {
  query: string;
  count: number;
  results: EmailMemoryRecord[];
}

export interface EmailMemoryRecord {
  id: string;
  type: string;
  to: string;
  from_addr?: string;
  subject: string;
  body: string;
  thread_id?: string;
  campaign_id?: string;
  target_type?: string;
  timestamp: string;
}

export interface CampaignTemplate {
  id: string;
  name: string;
  target_type: string;
  steps: number;
}

export interface CampaignInstance {
  instance_id: string;
  campaign_id: string;
  campaign_name: string;
  to: string;
  target_name: string;
  target_type: string;
  started_at: string;
  current_step: number;
  total_steps: number;
  status: string;
  steps_completed: { step: number; type: string; draft_id: string; processed_at: string }[];
}

export interface AnalysisResult {
  action: string;
  priority: string;
  summary: string;
  draft?: EmailDraft;
}

// ── API Functions ──

export const composeEmail = async (
  baseUrl: string,
  token: string,
  instruction: string,
  to?: string,
): Promise<EmailDraft> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/compose`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({ instruction, to: to || undefined }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Compose: ${resp.status}`);
  }
  return resp.json();
};

export const draftProspection = async (
  baseUrl: string,
  token: string,
  targetType: string,
  targetName: string,
  targetInfo: string = '',
  autoResearch: boolean = true,
): Promise<EmailDraft> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/draft`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({
      target_type: targetType,
      target_name: targetName,
      target_info: targetInfo,
      auto_research: autoResearch,
    }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Draft: ${resp.status}`);
  }
  return resp.json();
};

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

export interface ScrapedPage {
  url: string;
  title: string;
  meta_description: string;
  text_length: number;
}

export interface ResearchReport {
  company_name: string;
  company_type: string;
  search_results: SearchResult[];
  scraped_pages: ScrapedPage[];
  extracted_emails: string[];
  research_summary: string;
  memory_id?: string;
}

export const researchTarget = async (
  baseUrl: string,
  token: string,
  targetName: string,
  targetType: string = '',
  extraKeywords: string = '',
): Promise<ResearchReport> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/research`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({
      target_name: targetName,
      target_type: targetType,
      extra_keywords: extraKeywords,
    }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Research: ${resp.status}`);
  }
  return resp.json();
};

export const replyToEmail = async (
  baseUrl: string,
  token: string,
  emailId: string,
): Promise<EmailDraft> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/reply`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({ email_id: emailId }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Reply: ${resp.status}`);
  }
  return resp.json();
};

export const sendDraft = async (
  baseUrl: string,
  token: string,
  draftId: string,
): Promise<{ status: string; send_result: unknown }> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/send`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({ draft_id: draftId }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Send: ${resp.status}`);
  }
  return resp.json();
};

export const fetchInbox = async (
  baseUrl: string,
  token: string,
  limit: number = 20,
): Promise<InboxMessage[]> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/inbox?limit=${limit}`, {
    headers: adminHeaders(token),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Inbox: ${resp.status}`);
  }
  return resp.json();
};

export const queryMemory = async (
  baseUrl: string,
  token: string,
  query: string = '',
  limit: number = 20,
): Promise<MemoryResult> => {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  params.set('limit', String(limit));
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/memory?${params}`, {
    headers: adminHeaders(token),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Memory: ${resp.status}`);
  }
  return resp.json();
};

export const listCampaignTemplates = async (
  baseUrl: string,
  token: string,
): Promise<CampaignTemplate[]> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/campaign/list`, {
    headers: adminHeaders(token),
  });
  if (!resp.ok) throw new Error(`Campaign list: ${resp.status}`);
  return resp.json();
};

export const startCampaign = async (
  baseUrl: string,
  token: string,
  campaignId: string,
  to: string,
  targetName: string,
  targetInfo: string = '',
): Promise<CampaignInstance> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/campaign/start`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({ campaign_id: campaignId, to, target_name: targetName, target_info: targetInfo }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Campaign start: ${resp.status}`);
  }
  return resp.json();
};

export const getCampaignStatus = async (
  baseUrl: string,
  token: string,
): Promise<CampaignInstance[]> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/campaign/status`, {
    headers: adminHeaders(token),
  });
  if (!resp.ok) throw new Error(`Campaign status: ${resp.status}`);
  return resp.json();
};

export const triggerCampaignCheck = async (
  baseUrl: string,
  token: string,
): Promise<unknown[]> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/campaign/check`, {
    method: 'POST',
    headers: adminHeaders(token),
  });
  if (!resp.ok) throw new Error(`Campaign check: ${resp.status}`);
  return resp.json();
};

// ── Inbox Processing ──

export interface ProcessedEmail {
  gmail_id: string;
  from_addr: string;
  subject: string;
  classification: string;
  is_relevant: boolean;
  urgency: string;
  action: string;
  summary: string;
  memory_id: string;
  draft_id: string | null;
}

export interface InboxProcessingReport {
  total_fetched: number;
  already_processed: number;
  newly_processed: number;
  classifications: Record<string, number>;
  auto_replies_drafted: number;
  auto_replies_sent: number;
  emails: ProcessedEmail[];
  errors: string[];
}

export const processInbox = async (
  baseUrl: string,
  token: string,
  maxEmails: number = 20,
  autoReply: boolean = true,
  autoSend: boolean = false,
): Promise<InboxProcessingReport> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/process-inbox`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({ max_emails: maxEmails, auto_reply: autoReply, auto_send: autoSend }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Process inbox: ${resp.status}`);
  }
  return resp.json();
};

export interface DraftEmail {
  id: string;
  type: string;
  to: string;
  subject: string;
  body: string;
  target_type?: string;
  auto_reply?: boolean;
  in_reply_to?: string;
  thread_id?: string;
  timestamp: string;
}

export const fetchDrafts = async (
  baseUrl: string,
  token: string,
): Promise<DraftEmail[]> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/drafts`, {
    headers: adminHeaders(token),
  });
  if (!resp.ok) throw new Error(`Drafts: ${resp.status}`);
  return resp.json();
};
