import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot, User, Loader2, Minimize2, Maximize2 } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface AnalysisContext {
  status?: string;
  stage?: string;
  confidence?: number;
  features?: Record<string, number>;
  report?: string;
}

interface ChatBotProps {
  apiUrl: string;
  isApiConnected: boolean;
  analysisContext?: AnalysisContext | null;
}

export const ChatBot: React.FC<ChatBotProps> = ({ apiUrl, isApiConnected, analysisContext }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        "Bonjour ! Je suis l'assistant IA de Neuro-Link. Je suis là pour vous accompagner pendant votre analyse EEG. " +
        "N'hésitez pas à me poser des questions sur le processus, les résultats ou la maladie d'Alzheimer.",
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  // Notify when analysis results arrive
  useEffect(() => {
    if (analysisContext?.status && messages.length > 0) {
      const alreadyNotified = messages.some(
        (m) => m.role === 'assistant' && m.content.includes('résultats de votre analyse')
      );
      if (!alreadyNotified) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content:
              `Les résultats de votre analyse sont disponibles (${analysisContext.status}, ` +
              `confiance ${((analysisContext.confidence ?? 0) * 100).toFixed(1)}%). ` +
              "N'hésitez pas à me poser des questions pour mieux comprendre le rapport.",
          },
        ]);
      }
    }
  }, [analysisContext?.status]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: text };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const endpoint = apiUrl.startsWith('/') ? `${apiUrl}/chat` : `${apiUrl}/chat`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
        },
        body: JSON.stringify({
          messages: newMessages
            .filter((m) => m.role === 'user' || m.role === 'assistant')
            .slice(-20) // keep last 20 messages for context window
            .map((m) => ({ role: m.role, content: m.content })),
          analysisContext: analysisContext || null,
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            "Désolé, je n'ai pas pu traiter votre message. Vérifiez la connexion au serveur et réessayez.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Render markdown-light (bold, line breaks)
  const renderContent = (text: string) => {
    return text.split('\n').map((line, i) => {
      const parts = line.split(/(\*\*.*?\*\*)/g).map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={j} className="text-white font-semibold">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return <span key={j}>{part}</span>;
      });
      return (
        <React.Fragment key={i}>
          {parts}
          {i < text.split('\n').length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  if (!isApiConnected) return null;

  return (
    <>
      {/* Floating button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-2xl 
                     bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 
                     border border-neon-cyan/30
                     text-neon-cyan shadow-glow-cyan
                     hover:shadow-glow-cyan-lg
                     transition-all duration-300 flex items-center justify-center
                     hover:scale-110 active:scale-95 backdrop-blur-sm"
          aria-label="Ouvrir le chat"
        >
          <MessageCircle size={22} />
          <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full border-2 border-neon-bg animate-pulse">
            <span className="absolute inset-0 rounded-full bg-neon-green"></span>
            <span className="absolute inset-0 rounded-full bg-neon-green animate-ping opacity-75"></span>
          </span>
        </button>
      )}

      {/* Chat window */}
      {isOpen && (
        <div
          className={`fixed z-50 transition-all duration-300 ease-in-out
            ${isExpanded
              ? 'inset-4 md:inset-8'
              : 'bottom-6 right-6 w-[380px] md:w-[420px] h-[560px]'
            }
            flex flex-col rounded-xl overflow-hidden
            border border-neon-border bg-neon-bg
            shadow-[0_0_40px_rgba(0,0,0,0.5)] backdrop-blur-md`}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-neon-panel border-b border-neon-border">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-cyan/15 to-neon-purple/10 border border-neon-cyan/25 flex items-center justify-center">
                <Bot size={15} className="text-neon-cyan" />
              </div>
              <div>
                <h3 className="text-xs font-orbitron font-bold text-white tracking-wider">
                  NEURO-ASSISTANT
                </h3>
                <p className="text-[9px] text-neon-cyan/50 font-mono">Gemini AI • En ligne</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1.5 text-gray-600 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                aria-label={isExpanded ? 'Réduire' : 'Agrandir'}
              >
                {isExpanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
              </button>
              <button
                onClick={() => { setIsOpen(false); setIsExpanded(false); }}
                className="p-1.5 text-gray-600 hover:text-red-400 transition-colors rounded-lg hover:bg-white/5"
                aria-label="Fermer le chat"
              >
                <X size={13} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex gap-2.5 animate-fade-in ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                <div
                  className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center
                    ${msg.role === 'user'
                      ? 'bg-neon-purple/10 border border-neon-purple/25'
                      : 'bg-neon-cyan/10 border border-neon-cyan/25'
                    }`}
                >
                  {msg.role === 'user' ? (
                    <User size={12} className="text-neon-purple" />
                  ) : (
                    <Bot size={12} className="text-neon-cyan" />
                  )}
                </div>

                <div
                  className={`max-w-[80%] px-3.5 py-2.5 rounded-xl text-sm leading-relaxed
                    ${msg.role === 'user'
                      ? 'bg-neon-purple/10 border border-neon-purple/15 text-gray-200 rounded-tr-sm'
                      : 'bg-neon-panel border border-neon-border/50 text-gray-300 rounded-tl-sm'
                    }`}
                >
                  {renderContent(msg.content)}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-2.5 animate-fade-in">
                <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-neon-cyan/10 border border-neon-cyan/25 flex items-center justify-center">
                  <Bot size={12} className="text-neon-cyan" />
                </div>
                <div className="bg-neon-panel border border-neon-border/50 rounded-xl rounded-tl-sm px-4 py-3">
                  <div className="flex items-center gap-2 text-neon-cyan/60 text-sm">
                    <Loader2 size={13} className="animate-spin" />
                    <span className="font-mono text-[10px] animate-pulse">Analyse en cours...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-neon-border bg-neon-panel">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Posez votre question..."
                disabled={isLoading}
                className="flex-1 bg-neon-bg border border-neon-border rounded-lg px-3.5 py-2.5 
                           text-sm text-white/90 placeholder-gray-600 font-rajdhani
                           focus:outline-none focus:border-neon-cyan/40 focus:ring-1 focus:ring-neon-cyan/15
                           disabled:opacity-50 transition-all"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className="w-10 h-10 rounded-lg bg-neon-cyan/10 border border-neon-cyan/25
                           text-neon-cyan hover:bg-neon-cyan/20 
                           disabled:opacity-30 disabled:cursor-not-allowed
                           transition-all duration-200 flex items-center justify-center
                           hover:shadow-glow-cyan"
                aria-label="Envoyer"
              >
                <Send size={15} />
              </button>
            </div>
            <p className="text-[9px] text-gray-600 mt-1.5 text-center font-mono tracking-wider">
              Neuro-Link AI • Ne remplace pas un avis médical
            </p>
          </div>
        </div>
      )}
    </>
  );
};
