import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResultsDashboard } from '../../components/ResultsDashboard';
import { DiagnosisResult } from '../../types';

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  RadarChart: ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
  Radar: () => <div />,
  PolarGrid: () => <div />,
  PolarAngleAxis: () => <div />,
  PolarRadiusAxis: () => <div />,
  BarChart: ({ children }: any) => <div>{children}</div>,
  Bar: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  Tooltip: () => <div />,
  Cell: () => <div />,
}));

const alzheimerResult: DiagnosisResult = {
  status: 'ALZHEIMER',
  stage: 'Stade 2 (Modéré)',
  confidence: 0.942,
  features: { Alpha: 0.35, Entropy: 0.82, Theta: 0.7 },
  report: '**NEURO-LINK REPORT**\n\nAnalyse terminée.\n\n[IMAGE_XAI]\n\nConclusion.\n\n[IMAGE_QR]',
};

const normalResult: DiagnosisResult = {
  status: 'NON-ALZHEIMER',
  stage: 'Normal',
  confidence: 0.95,
  features: { Alpha: 0.8, Entropy: 0.3, Theta: 0.2 },
  report: 'Aucune anomalie détectée.',
};

describe('ResultsDashboard', () => {
  describe('Medical Disclaimer', () => {
    it('renders the medical disclaimer banner', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText('AVERTISSEMENT MEDICAL')).toBeInTheDocument();
    });

    it('mentions research tool disclaimer', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/outil d'aide à la recherche/i)).toBeInTheDocument();
    });

    it('mentions CE/FDA non-certification', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/non certifié CE\/FDA/i)).toBeInTheDocument();
    });
  });

  describe('Diagnosis display', () => {
    it('displays ALZHEIMER status', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText('ALZHEIMER')).toBeInTheDocument();
    });

    it('displays NON-ALZHEIMER status', () => {
      render(<ResultsDashboard result={normalResult} />);
      expect(screen.getByText('NON-ALZHEIMER')).toBeInTheDocument();
    });

    it('shows the stage', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText('Stade 2 (Modéré)')).toBeInTheDocument();
    });

    it('shows confidence percentage', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/94\.2%/)).toBeInTheDocument();
    });

    it('shows DIAGNOSTIC FINAL label', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText('DIAGNOSTIC FINAL')).toBeInTheDocument();
    });
  });

  describe('Ad Banners', () => {
    it('renders OpenBCI ad banner', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/OpenBCI/)).toBeInTheDocument();
    });

    it('renders research participation banner', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/Participez à la recherche/)).toBeInTheDocument();
    });
  });

  describe('Report section', () => {
    it('renders COMPTE RENDU CLINIQUE header', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText('COMPTE RENDU CLINIQUE')).toBeInTheDocument();
    });

    it('renders export button', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/EXPORTER/)).toBeInTheDocument();
    });

    it('renders XAI figure caption', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/Importance des caractéristiques spectrales/)).toBeInTheDocument();
    });

    it('renders QR traceability caption', () => {
      render(<ResultsDashboard result={alzheimerResult} />);
      expect(screen.getByText(/Traçabilité/)).toBeInTheDocument();
    });
  });
});
