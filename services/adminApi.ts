/**
 * Admin API service for managing SaaS API keys, usage, and plans.
 */

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/$/, '');

export interface PlanInfo {
  label: string;
  max_analyses_per_month: number;
  max_requests_per_minute: number;
  price_eur: number;
}

export interface ApiKeyInfo {
  id: number;
  key_prefix: string;
  owner: string;
  email: string;
  plan: string;
  active: number;
  created_at: string;
  updated_at: string;
  usage_this_month?: { analyses: number; requests: number };
  plan_info?: PlanInfo;
  usage?: UsageInfo;
}

export interface UsageInfo {
  key_id: number;
  month: string;
  analyses_count: number;
  requests_count: number;
  recent_requests: { endpoint: string; timestamp: string }[];
}

export interface UsageSummary {
  month: string;
  total_analyses: number;
  total_requests: number;
  active_keys: number;
  top_users: { key_id: number; owner: string; plan: string; analyses_count: number; requests_count: number }[];
}

export interface CreateKeyResult {
  id: number;
  raw_key: string;
  key_prefix: string;
  owner: string;
  email: string;
  plan: string;
  created_at: string;
}

const adminHeaders = (token: string) => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`,
  'ngrok-skip-browser-warning': 'true',
});

export const fetchPlans = async (baseUrl: string, token: string): Promise<Record<string, PlanInfo>> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/plans`, { headers: adminHeaders(token) });
  if (!resp.ok) throw new Error(`Plans: ${resp.status}`);
  const data = await resp.json();
  return data.plans;
};

export const fetchKeys = async (baseUrl: string, token: string, includeInactive = false): Promise<ApiKeyInfo[]> => {
  const url = `${normalizeBaseUrl(baseUrl)}/admin/keys?include_inactive=${includeInactive}`;
  const resp = await fetch(url, { headers: adminHeaders(token) });
  if (!resp.ok) throw new Error(`Keys: ${resp.status}`);
  const data = await resp.json();
  return data.keys;
};

export const fetchKeyDetail = async (baseUrl: string, token: string, keyId: number): Promise<ApiKeyInfo> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/keys/${keyId}`, { headers: adminHeaders(token) });
  if (!resp.ok) throw new Error(`Key ${keyId}: ${resp.status}`);
  return resp.json();
};

export const createKey = async (
  baseUrl: string,
  token: string,
  owner: string,
  email: string,
  plan: string
): Promise<CreateKeyResult> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/keys`, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify({ owner, email, plan }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Create: ${resp.status}`);
  }
  return resp.json();
};

export const updateKey = async (
  baseUrl: string,
  token: string,
  keyId: number,
  updates: { plan?: string; active?: boolean; owner?: string; email?: string }
): Promise<void> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/keys/${keyId}`, {
    method: 'PATCH',
    headers: adminHeaders(token),
    body: JSON.stringify(updates),
  });
  if (!resp.ok) throw new Error(`Update: ${resp.status}`);
};

export const revokeKey = async (baseUrl: string, token: string, keyId: number): Promise<void> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/keys/${keyId}/revoke`, {
    method: 'POST',
    headers: adminHeaders(token),
  });
  if (!resp.ok) throw new Error(`Revoke: ${resp.status}`);
};

export const deleteKey = async (baseUrl: string, token: string, keyId: number): Promise<void> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/keys/${keyId}`, {
    method: 'DELETE',
    headers: adminHeaders(token),
  });
  if (!resp.ok) throw new Error(`Delete: ${resp.status}`);
};

export const fetchKeyUsage = async (baseUrl: string, token: string, keyId: number, month?: string): Promise<UsageInfo> => {
  const url = month
    ? `${normalizeBaseUrl(baseUrl)}/admin/keys/${keyId}/usage?month=${month}`
    : `${normalizeBaseUrl(baseUrl)}/admin/keys/${keyId}/usage`;
  const resp = await fetch(url, { headers: adminHeaders(token) });
  if (!resp.ok) throw new Error(`Usage: ${resp.status}`);
  return resp.json();
};

export const fetchUsageSummary = async (baseUrl: string, token: string): Promise<UsageSummary> => {
  const resp = await fetch(`${normalizeBaseUrl(baseUrl)}/admin/usage/summary`, { headers: adminHeaders(token) });
  if (!resp.ok) throw new Error(`Summary: ${resp.status}`);
  return resp.json();
};
