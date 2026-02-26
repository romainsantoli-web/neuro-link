import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusHUD } from '../../components/StatusHUD';

describe('StatusHUD', () => {
  it('shows ESTABLISHED when connected', () => {
    render(<StatusHUD isConnected={true} />);
    expect(screen.getByText('ESTABLISHED')).toBeInTheDocument();
  });

  it('shows OFFLINE when disconnected', () => {
    render(<StatusHUD isConnected={false} />);
    expect(screen.getByText('OFFLINE')).toBeInTheDocument();
  });

  it('displays KERNEL LINK card', () => {
    render(<StatusHUD isConnected={true} />);
    expect(screen.getByText('KERNEL LINK')).toBeInTheDocument();
  });

  it('displays AI MODELS card', () => {
    render(<StatusHUD isConnected={true} />);
    expect(screen.getByText('AI MODELS')).toBeInTheDocument();
  });

  it('shows AD-FORMER V2 when connected', () => {
    render(<StatusHUD isConnected={true} />);
    expect(screen.getByText('AD-FORMER V2')).toBeInTheDocument();
  });

  it('shows STANDBY for AI when disconnected', () => {
    render(<StatusHUD isConnected={false} />);
    expect(screen.getByText('STANDBY')).toBeInTheDocument();
  });

  it('shows SECURITY card always', () => {
    render(<StatusHUD isConnected={false} />);
    expect(screen.getByText('SECURITY')).toBeInTheDocument();
    expect(screen.getByText('ENCRYPTED')).toBeInTheDocument();
  });

  it('renders all 4 status cards', () => {
    render(<StatusHUD isConnected={true} />);
    expect(screen.getByText('KERNEL LINK')).toBeInTheDocument();
    expect(screen.getByText('STORAGE / DRIVE')).toBeInTheDocument();
    expect(screen.getByText('AI MODELS')).toBeInTheDocument();
    expect(screen.getByText('SECURITY')).toBeInTheDocument();
  });
});
