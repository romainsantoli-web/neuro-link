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
): Promise<EmailDraft> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/email-ai/draft`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({ target_type: targetType, target_name: targetName, target_info: targetInfo }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Draft: ${resp.status}`);
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
