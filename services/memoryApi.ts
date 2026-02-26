export interface MemoryContextResponse {
  context: string;
  sourceCount: number;
}

export interface MemoryIngestPayload {
  sessionId: string;
  fileName: string;
  diagnosisStatus: string | null;
  stage: string;
  confidence: number;
  report: string;
  features: Record<string, number>;
  createdAt: string;
}

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.replace(/\/$/, '');

export const checkMemoryHealth = async (baseUrl: string): Promise<boolean> => {
  if (!baseUrl) return false;

  const cleanUrl = normalizeBaseUrl(baseUrl);
  const response = await fetch(`${cleanUrl}/memory/health`, {
    method: 'GET',
    headers: {
      'ngrok-skip-browser-warning': 'true',
      'Content-Type': 'application/json',
    },
  });

  return response.ok;
};

export const getMemoryContext = async (
  baseUrl: string,
  query: string,
  sessionId: string
): Promise<MemoryContextResponse | null> => {
  if (!baseUrl || !query.trim()) return null;

  const cleanUrl = normalizeBaseUrl(baseUrl);
  const response = await fetch(`${cleanUrl}/memory/context`, {
    method: 'POST',
    headers: {
      'ngrok-skip-browser-warning': 'true',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      sessionId,
      limit: 5,
    }),
  });

  if (!response.ok) return null;

  const data = await response.json();
  return {
    context: data.context ?? '',
    sourceCount: Number(data.sourceCount ?? 0),
  };
};

export const ingestMemoryRecord = async (
  baseUrl: string,
  payload: MemoryIngestPayload
): Promise<boolean> => {
  if (!baseUrl) return false;

  const cleanUrl = normalizeBaseUrl(baseUrl);
  const response = await fetch(`${cleanUrl}/memory/ingest`, {
    method: 'POST',
    headers: {
      'ngrok-skip-browser-warning': 'true',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return response.ok;
};
