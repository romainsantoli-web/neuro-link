import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '../../components/Header';

describe('Header', () => {
  it('renders the application title', () => {
    render(<Header />);
    expect(screen.getByText('NEURO-LINK')).toBeInTheDocument();
  });

  it('displays the version tag', () => {
    render(<Header />);
    expect(screen.getByText('v18.0')).toBeInTheDocument();
  });

  it('shows the subtitle', () => {
    render(<Header />);
    expect(screen.getByText('Advanced Alzheimer Diagnostic Interface')).toBeInTheDocument();
  });

  it('shows system online status', () => {
    render(<Header />);
    expect(screen.getByText('SYSTEM ONLINE')).toBeInTheDocument();
  });
});
