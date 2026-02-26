import React from 'react';
import { Bot, Sparkles, BrainCircuit } from 'lucide-react';

export type LogigramType = 'default' | 'neural' | 'waveform' | 'hex' | 'thinking';

interface NarratorBoxProps {
  message: string;
  logigramType?: LogigramType;
}

const Logigram: React.FC<{ type: LogigramType }> = ({ type }) => {
  if (type === 'default') return null;

  return (
    <div className="absolute right-6 top-1/2 -translate-y-1/2 opacity-15 group-hover:opacity-30 transition-opacity duration-1000 pointer-events-none">
      {/* THINKING MODE */}
      {type === 'thinking' && (
        <div className="relative w-20 h-20 flex items-center justify-center">
           <div className="absolute inset-0 border border-neon-purple/40 rounded-full animate-[spin_4s_linear_infinite] border-t-transparent border-l-transparent"></div>
           <div className="absolute inset-3 border border-neon-cyan/30 rounded-full animate-[spin_3s_linear_infinite_reverse] border-b-transparent border-r-transparent"></div>
           <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-1.5 h-1.5 bg-white rounded-full animate-ping"></div>
           </div>
        </div>
      )}

      {/* NEURAL */}
      {type === 'neural' && (
        <svg width="70" height="70" viewBox="0 0 100 100" className="animate-pulse">
           <circle cx="50" cy="50" r="3" fill="#a855f7" />
           <circle cx="20" cy="80" r="2.5" fill="#a855f7" className="animate-bounce" style={{ animationDelay: '100ms' }} />
           <circle cx="80" cy="20" r="2.5" fill="#a855f7" className="animate-bounce" style={{ animationDelay: '200ms' }} />
           <circle cx="80" cy="80" r="2.5" fill="#a855f7" className="animate-bounce" style={{ animationDelay: '300ms' }} />
           <line x1="50" y1="50" x2="20" y2="80" stroke="#a855f7" strokeWidth="0.8" opacity="0.4" />
           <line x1="50" y1="50" x2="80" y2="20" stroke="#a855f7" strokeWidth="0.8" opacity="0.4" />
           <line x1="50" y1="50" x2="80" y2="80" stroke="#a855f7" strokeWidth="0.8" opacity="0.4" />
        </svg>
      )}

      {/* WAVEFORM */}
      {type === 'waveform' && (
        <div className="flex gap-[3px] items-center h-10">
            {[4, 8, 5, 10, 6].map((h, i) => (
              <div 
                key={i} 
                className="w-[2px] bg-neon-cyan rounded-full" 
                style={{ height: `${h * 3}px`, animation: `pulse ${1 + i * 0.2}s ease-in-out infinite`, animationDelay: `${i * 50}ms` }}
              />
            ))}
        </div>
      )}

      {/* HEX */}
      {type === 'hex' && (
        <svg width="70" height="70" viewBox="0 0 100 100" className="animate-[spin_10s_linear_infinite]">
            <polygon points="50,10 85,30 85,70 50,90 15,70 15,30" fill="none" stroke="#3fb950" strokeWidth="0.8" opacity="0.5" />
            <polygon points="50,20 75,35 75,65 50,80 25,65 25,35" fill="none" stroke="#3fb950" strokeWidth="0.8" opacity="0.25" />
            <circle cx="50" cy="50" r="2" fill="#3fb950" className="animate-ping" />
        </svg>
      )}
    </div>
  );
};

export const NarratorBox: React.FC<NarratorBoxProps> = ({ message, logigramType = 'default' }) => {
  return (
    <div className="flex flex-col h-full glass-panel overflow-hidden relative group">
       {/* Right accent bar */}
       <div className="absolute right-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-neon-purple via-neon-purple/50 to-transparent" />
      
       {/* Subtle grid background */}
       <div className="absolute inset-0 bg-[linear-gradient(rgba(168,85,247,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(168,85,247,0.015)_1px,transparent_1px)] bg-[size:24px_24px]" />
      
       {/* Logigram Layer */}
       <Logigram type={logigramType} />

      {/* Header */}
      <div className="px-5 py-2.5 border-b border-neon-border/50 flex justify-between items-center z-10 relative bg-black/30">
        <span className="text-neon-purple font-orbitron text-[10px] tracking-[3px] flex items-center gap-2 uppercase">
          <BrainCircuit size={12} /> AI Interpreter
        </span>
        <div className="flex gap-2 items-center">
            {logigramType === 'thinking' && (
                 <span className="text-[9px] font-mono text-white/60 animate-pulse flex items-center gap-1.5">
                    <Sparkles size={9} /> THINKING
                 </span>
            )}
            <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-neon-purple/60 animate-pulse"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-neon-purple/40 animate-pulse" style={{ animationDelay: '100ms' }}></div>
                <div className="w-1.5 h-1.5 rounded-full bg-neon-purple/20 animate-pulse" style={{ animationDelay: '200ms' }}></div>
            </div>
        </div>
      </div>
      
      {/* Message */}
      <div className="flex-1 p-6 flex items-center justify-center z-10 relative">
        <p className="text-slate-300 font-rajdhani text-lg md:text-xl leading-relaxed text-center max-w-md">
          <span className="text-neon-purple/40 mr-1">&ldquo;</span>
          {message}
          <span className="text-neon-purple/40 ml-1">&rdquo;</span>
        </p>
      </div>
    </div>
  );
};