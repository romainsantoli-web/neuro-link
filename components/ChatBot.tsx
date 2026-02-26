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
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full 
                     bg-gradient-to-br from-neon-cyan to-blue-600 
                     text-black shadow-[0_0_25px_rgba(0,255,234,0.4)] 
                     hover:shadow-[0_0_35px_rgba(0,255,234,0.6)] 
                     transition-all duration-300 flex items-center justify-center
                     hover:scale-110 active:scale-95"
          aria-label="Ouvrir le chat"
        >
          <MessageCircle size={24} />
          {/* Notification dot */}
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-neon-green rounded-full border-2 border-black animate-pulse" />
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
            border border-neon-cyan/30 bg-[#0a0a0f] 
            shadow-[0_0_40px_rgba(0,255,234,0.15)]`}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-gray-900 to-[#0d1117] border-b border-neon-cyan/20">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center">
                <Bot size={16} className="text-neon-cyan" />
              </div>
              <div>
                <h3 className="text-sm font-orbitron font-bold text-white tracking-wider">
                  NEURO-ASSISTANT
                </h3>
                <p className="text-[10px] text-neon-cyan/60 font-mono">Gemini AI • En ligne</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1.5 text-gray-500 hover:text-white transition-colors rounded hover:bg-white/5"
                aria-label={isExpanded ? 'Réduire' : 'Agrandir'}
              >
                {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>
              <button
                onClick={() => { setIsOpen(false); setIsExpanded(false); }}
                className="p-1.5 text-gray-500 hover:text-red-400 transition-colors rounded hover:bg-white/5"
                aria-label="Fermer le chat"
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex gap-2.5 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                <div
                  className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs
                    ${msg.role === 'user'
                      ? 'bg-blue-600/20 border border-blue-500/30'
                      : 'bg-neon-cyan/10 border border-neon-cyan/30'
                    }`}
                >
                  {msg.role === 'user' ? (
                    <User size={13} className="text-blue-400" />
                  ) : (
                    <Bot size={13} className="text-neon-cyan" />
                  )}
                </div>

                {/* Bubble */}
                <div
                  className={`max-w-[80%] px-3.5 py-2.5 rounded-xl text-sm leading-relaxed
                    ${msg.role === 'user'
                      ? 'bg-blue-600/20 border border-blue-500/20 text-blue-50 rounded-tr-sm'
                      : 'bg-gray-800/60 border border-gray-700/40 text-gray-200 rounded-tl-sm'
                    }`}
                >
                  {renderContent(msg.content)}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex gap-2.5">
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center">
                  <Bot size={13} className="text-neon-cyan" />
                </div>
                <div className="bg-gray-800/60 border border-gray-700/40 rounded-xl rounded-tl-sm px-4 py-3">
                  <div className="flex items-center gap-2 text-neon-cyan/70 text-sm">
                    <Loader2 size={14} className="animate-spin" />
                    <span className="font-mono text-xs animate-pulse">Analyse en cours...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-gray-800 bg-[#080810]">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Posez votre question..."
                disabled={isLoading}
                className="flex-1 bg-gray-900/80 border border-gray-700/50 rounded-lg px-3.5 py-2.5 
                           text-sm text-white placeholder-gray-500 font-rajdhani
                           focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/20
                           disabled:opacity-50 transition-all"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className="w-10 h-10 rounded-lg bg-neon-cyan/10 border border-neon-cyan/30
                           text-neon-cyan hover:bg-neon-cyan/20 
                           disabled:opacity-30 disabled:cursor-not-allowed
                           transition-all duration-200 flex items-center justify-center
                           hover:shadow-[0_0_15px_rgba(0,255,234,0.2)]"
                aria-label="Envoyer"
              >
                <Send size={16} />
              </button>
            </div>
            <p className="text-[10px] text-gray-600 mt-1.5 text-center font-mono">
              Neuro-Link AI • Ne remplace pas un avis médical
            </p>
          </div>
        </div>
      )}
    </>
  );
};
