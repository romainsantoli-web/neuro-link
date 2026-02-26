import React from 'react';
import { Bot, Sparkles } from 'lucide-react';

export type LogigramType = 'default' | 'neural' | 'waveform' | 'hex' | 'thinking';

interface NarratorBoxProps {
  message: string;
  logigramType?: LogigramType;
}

const Logigram: React.FC<{ type: LogigramType }> = ({ type }) => {
  if (type === 'default') return null;

  return (
    <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-20 group-hover:opacity-40 transition-opacity duration-1000 pointer-events-none">
      {/* THINKING MODE (Complex) */}
      {type === 'thinking' && (
        <div className="relative w-24 h-24 flex items-center justify-center">
           <div className="absolute inset-0 border border-neon-purple rounded-full animate-[spin_4s_linear_infinite] opacity-30 border-t-transparent border-l-transparent"></div>
           <div className="absolute inset-2 border border-neon-cyan rounded-full animate-[spin_3s_linear_infinite_reverse] opacity-30 border-b-transparent border-r-transparent"></div>
           <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-2 h-2 bg-white rounded-full animate-ping"></div>
           </div>
           {/* Floating particles */}
           <div className="absolute top-0 left-1/2 w-1 h-1 bg-neon-purple rounded-full animate-pulse"></div>
           <div className="absolute bottom-0 left-1/2 w-1 h-1 bg-neon-cyan rounded-full animate-pulse delay-75"></div>
           <div className="absolute left-0 top-1/2 w-1 h-1 bg-white rounded-full animate-pulse delay-150"></div>
        </div>
      )}

      {/* NEURAL (Nodes) */}
      {type === 'neural' && (
        <svg width="80" height="80" viewBox="0 0 100 100" className="animate-pulse">
           <circle cx="50" cy="50" r="4" fill="#a855f7" />
           <circle cx="20" cy="80" r="3" fill="#a855f7" className="animate-bounce delay-100" />
           <circle cx="80" cy="20" r="3" fill="#a855f7" className="animate-bounce delay-200" />
           <circle cx="80" cy="80" r="3" fill="#a855f7" className="animate-bounce delay-300" />
           <line x1="50" y1="50" x2="20" y2="80" stroke="#a855f7" strokeWidth="1" opacity="0.5" />
           <line x1="50" y1="50" x2="80" y2="20" stroke="#a855f7" strokeWidth="1" opacity="0.5" />
           <line x1="50" y1="50" x2="80" y2="80" stroke="#a855f7" strokeWidth="1" opacity="0.5" />
        </svg>
      )}

      {/* WAVEFORM (Bars) */}
      {type === 'waveform' && (
        <div className="flex gap-1 items-center h-12">
            <div className="w-1 bg-neon-cyan h-4 animate-[pulse_1s_ease-in-out_infinite]"></div>
            <div className="w-1 bg-neon-cyan h-8 animate-[pulse_1.2s_ease-in-out_infinite] delay-75"></div>
            <div className="w-1 bg-neon-cyan h-6 animate-[pulse_0.8s_ease-in-out_infinite] delay-150"></div>
            <div className="w-1 bg-neon-cyan h-10 animate-[pulse_1.5s_ease-in-out_infinite] delay-100"></div>
            <div className="w-1 bg-neon-cyan h-5 animate-[pulse_1.1s_ease-in-out_infinite] delay-200"></div>
        </div>
      )}

      {/* HEX (Structure) */}
      {type === 'hex' && (
        <svg width="80" height="80" viewBox="0 0 100 100" className="animate-[spin_8s_linear_infinite]">
            <polygon points="50,10 85,30 85,70 50,90 15,70 15,30" fill="none" stroke="#3fb950" strokeWidth="1" opacity="0.6" />
            <polygon points="50,20 75,35 75,65 50,80 25,65 25,35" fill="none" stroke="#3fb950" strokeWidth="1" opacity="0.3" />
            <circle cx="50" cy="50" r="2" fill="#3fb950" className="animate-ping" />
        </svg>
      )}
    </div>
  );
};

export const NarratorBox: React.FC<NarratorBoxProps> = ({ message, logigramType = 'default' }) => {
  return (
    <div className="flex flex-col h-full border border-neon-purple/50 bg-slate-900/90 shadow-[0_0_25px_rgba(168,85,247,0.15)] border-r-4 border-r-neon-purple rounded-lg overflow-hidden relative group">
       {/* Background Grid Effect */}
       <div className="absolute inset-0 bg-[linear-gradient(rgba(168,85,247,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(168,85,247,0.03)_1px,transparent_1px)] bg-[size:20px_20px]" />
      
       {/* Logigram Layer */}
       <Logigram type={logigramType} />

      <div className="px-4 py-2 bg-slate-900/50 border-b border-neon-purple/20 flex justify-between items-center z-10 relative">
        <span className="text-neon-purple font-orbitron text-xs tracking-widest flex items-center gap-2">
          <Bot size={14} /> AI INTERPRETER
        </span>
        <div className="flex gap-2 items-center">
            {logigramType === 'thinking' && (
                 <span className="text-[10px] font-mono text-white/70 animate-pulse flex items-center gap-1">
                    <Sparkles size={10} /> THINKING MODE
                 </span>
            )}
            <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-neon-purple animate-pulse"></div>
                <div className="w-2 h-2 rounded-full bg-neon-purple animate-pulse delay-75"></div>
                <div className="w-2 h-2 rounded-full bg-neon-purple animate-pulse delay-150"></div>
            </div>
        </div>
      </div>
      
      <div className="flex-1 p-6 flex items-center justify-center z-10 relative">
        <p className="text-slate-200 font-rajdhani text-lg md:text-xl leading-relaxed text-center animate-pulse-fast drop-shadow-[0_0_5px_rgba(168,85,247,0.5)]">
          "{message}"
        </p>
      </div>
    </div>
  );
};