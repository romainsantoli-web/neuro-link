import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConsoleBox } from '../../components/ConsoleBox';

describe('ConsoleBox', () => {
  const baseLogs = [
    { id: '1', message: 'Starting pipeline...', type: 'info' as const },
    { id: '2', message: 'WARNING: high noise', type: 'warning' as const },
    { id: '3', message: 'Error in processing', type: 'error' as const },
    { id: '4', message: '> run_pipeline.py', type: 'cmd' as const },
  ];

  it('renders the KERNEL LOGS header', () => {
    render(<ConsoleBox logs={[]} />);
    expect(screen.getByText('KERNEL LOGS')).toBeInTheDocument();
  });

  it('renders the log path', () => {
    render(<ConsoleBox logs={[]} />);
    expect(screen.getByText('/var/log/neuro-link.log')).toBeInTheDocument();
  });

  it('displays all log messages', () => {
    render(<ConsoleBox logs={baseLogs} />);
    expect(screen.getByText('Starting pipeline...')).toBeInTheDocument();
    expect(screen.getByText('WARNING: high noise')).toBeInTheDocument();
    expect(screen.getByText('Error in processing')).toBeInTheDocument();
  });

  it('renders cmd logs with > prefix', () => {
    render(<ConsoleBox logs={baseLogs} />);
    expect(screen.getByText(/> run_pipeline\.py/)).toBeInTheDocument();
  });

  it('handles empty logs gracefully', () => {
    const { container } = render(<ConsoleBox logs={[]} />);
    expect(container.querySelector('.font-mono')).not.toBeNull();
  });
});
