import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../types';
import { Terminal } from 'lucide-react';

interface ConsoleBoxProps {
  logs: LogEntry[];
}

const typeColors: Record<string, string> = {
  cmd: 'text-amber-400',
  info: 'text-neon-green',
  success: 'text-emerald-400',
  warning: 'text-orange-400',
  error: 'text-red-400',
};

export const ConsoleBox: React.FC<ConsoleBoxProps> = ({ logs }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full glass-panel overflow-hidden relative group">
      {/* Left accent bar */}
      <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-neon-green via-neon-green/50 to-transparent" />
      
      {/* Header */}
      <div className="px-5 py-2.5 border-b border-neon-border/50 flex justify-between items-center bg-black/30">
        <span className="text-neon-green font-orbitron text-[10px] tracking-[3px] flex items-center gap-2 uppercase">
          <Terminal size={12} />
          Kernel Logs
        </span>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-neon-green/60 animate-pulse" />
          <span className="text-[9px] text-gray-600 font-mono">/var/log/neuro-link</span>
        </div>
      </div>
      
      {/* Log entries */}
      <div className="flex-1 p-4 pl-5 overflow-y-auto font-mono text-xs space-y-0.5 max-h-[300px] min-h-[300px]">
        {logs.map((log, i) => (
          <div 
            key={log.id} 
            className="break-words py-0.5 flex items-start gap-2 animate-fade-in"
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <span className="text-gray-700 select-none flex-shrink-0 text-[10px] mt-0.5">
              {new Date().toLocaleTimeString().split(' ')[0]}
            </span>
            <span className="text-gray-700 select-none flex-shrink-0">
              {log.type === 'cmd' ? '>' : log.type === 'error' ? '!' : log.type === 'warning' ? '~' : '-'}
            </span>
            <span className={`${typeColors[log.type] || 'text-gray-400'} leading-relaxed`}>
              {log.message}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
};
