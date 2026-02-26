import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { NarratorBox } from '../../components/NarratorBox';

describe('NarratorBox', () => {
  it('renders the narrator message', () => {
    render(<NarratorBox message="Analyse en cours..." />);
    expect(screen.getByText(/"Analyse en cours\.\.\."/)).toBeInTheDocument();
  });

  it('shows AI INTERPRETER label', () => {
    render(<NarratorBox message="Test" />);
    expect(screen.getByText('AI INTERPRETER')).toBeInTheDocument();
  });

  it('shows THINKING MODE label when type is thinking', () => {
    render(<NarratorBox message="Réflexion..." logigramType="thinking" />);
    expect(screen.getByText('THINKING MODE')).toBeInTheDocument();
  });

  it('does not show THINKING MODE for default type', () => {
    render(<NarratorBox message="Standby" logigramType="default" />);
    expect(screen.queryByText('THINKING MODE')).not.toBeInTheDocument();
  });

  it('does not show THINKING MODE for neural type', () => {
    render(<NarratorBox message="Processing" logigramType="neural" />);
    expect(screen.queryByText('THINKING MODE')).not.toBeInTheDocument();
  });
});
