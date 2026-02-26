import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatBot } from '../../components/ChatBot';

describe('ChatBot', () => {
  it('does not render when API is disconnected', () => {
    const { container } = render(
      <ChatBot apiUrl="/api" isApiConnected={false} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders the floating button when connected', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    expect(screen.getByLabelText('Ouvrir le chat')).toBeInTheDocument();
  });

  it('opens chat window when button is clicked', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    expect(screen.getByText('NEURO-ASSISTANT')).toBeInTheDocument();
  });

  it('shows the welcome message on open', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    expect(screen.getByText(/assistant IA de Neuro-Link/i)).toBeInTheDocument();
  });

  it('has an input field for typing messages', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    expect(screen.getByPlaceholderText('Posez votre question...')).toBeInTheDocument();
  });

  it('has a send button', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    expect(screen.getByLabelText('Envoyer')).toBeInTheDocument();
  });

  it('closes chat when X is clicked', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    expect(screen.getByText('NEURO-ASSISTANT')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Fermer le chat'));
    expect(screen.queryByText('NEURO-ASSISTANT')).not.toBeInTheDocument();
  });

  it('shows disclaimer about medical advice', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    expect(screen.getByText(/Ne remplace pas un avis médical/)).toBeInTheDocument();
  });

  it('shows Gemini AI label in header', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    expect(screen.getByText(/Gemini AI/)).toBeInTheDocument();
  });

  it('disables send button when input is empty', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    const sendBtn = screen.getByLabelText('Envoyer');
    expect(sendBtn).toBeDisabled();
  });

  it('enables send button when text is typed', () => {
    render(<ChatBot apiUrl="/api" isApiConnected={true} />);
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));
    fireEvent.change(screen.getByPlaceholderText('Posez votre question...'), {
      target: { value: 'Bonjour' },
    });
    const sendBtn = screen.getByLabelText('Envoyer');
    expect(sendBtn).not.toBeDisabled();
  });

  it('adds analysis notification when results arrive', () => {
    const { rerender } = render(
      <ChatBot apiUrl="/api" isApiConnected={true} analysisContext={null} />
    );
    fireEvent.click(screen.getByLabelText('Ouvrir le chat'));

    // Rerender with analysis results
    rerender(
      <ChatBot
        apiUrl="/api"
        isApiConnected={true}
        analysisContext={{ status: 'ALZHEIMER', confidence: 0.87 }}
      />
    );

    expect(screen.getByText(/résultats de votre analyse/)).toBeInTheDocument();
  });
});
