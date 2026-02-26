import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../types';

interface ConsoleBoxProps {
  logs: LogEntry[];
}

export const ConsoleBox: React.FC<ConsoleBoxProps> = ({ logs }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full border border-neon-border bg-neon-panel shadow-[inset_0_0_30px_#000] border-l-4 border-l-neon-green rounded-lg overflow-hidden">
      <div className="px-4 py-2 bg-gray-900 border-b border-gray-800 flex justify-between items-center">
        <span className="text-neon-green font-orbitron text-xs tracking-widest">KERNEL LOGS</span>
        <span className="text-[10px] text-gray-500 font-mono">/var/log/neuro-link.log</span>
      </div>
      <div className="flex-1 p-4 overflow-y-auto font-mono text-xs md:text-sm space-y-1 custom-scrollbar max-h-[300px] min-h-[300px]">
        {logs.map((log) => (
          <div key={log.id} className="break-words">
            <span className="text-gray-600 mr-2">[{new Date().toLocaleTimeString().split(' ')[0]}]</span>
            <span className={`
              ${log.type === 'cmd' ? 'text-yellow-400' : ''}
              ${log.type === 'info' ? 'text-neon-green' : ''}
              ${log.type === 'warning' ? 'text-orange-500' : ''}
              ${log.type === 'error' ? 'text-red-500' : ''}
            `}>
              {log.type === 'cmd' ? '> ' : ''}{log.message}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
};
