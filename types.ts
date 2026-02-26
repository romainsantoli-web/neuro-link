export interface DiagnosisFeatures {
  Alpha: number;
  Entropy: number;
  Theta: number;
}

export interface DiagnosisResult {
  status: 'ALZHEIMER' | 'NON-ALZHEIMER' | 'INCONCLUSIVE' | null;
  stage: string;
  confidence: number;
  features: DiagnosisFeatures;
  report: string;
}

export type AppState = 'IDLE' | 'ANALYZING' | 'COMPLETE';

export interface LogEntry {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'cmd';
}
