import React from 'react';
import { Cpu, Activity, Brain } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="flex flex-col md:flex-row justify-between items-start md:items-center py-6 px-4 mb-6 border-b border-neon-cyan/20">
      <div>
        <h1 className="text-5xl md:text-6xl font-orbitron font-black text-white tracking-widest leading-none">
          NEURO-LINK <span className="text-xl text-gray-500 font-normal align-top opacity-50">v18.0</span>
        </h1>
        <p className="text-neon-cyan font-rajdhani font-semibold tracking-[4px] mt-2 uppercase text-sm md:text-base">
          Advanced Alzheimer Diagnostic Interface
        </p>
      </div>
      
      <div className="mt-4 md:mt-0 flex flex-col items-end">
        <div className="border border-neon-cyan rounded px-4 py-2 bg-neon-cyan/5 backdrop-blur-sm group hover:bg-neon-cyan/10 transition-colors">
          <div className="flex items-center gap-2 text-neon-cyan font-bold font-orbitron text-sm">
            <Activity className="w-4 h-4 animate-pulse" />
            SYSTEM: ONLINE
          </div>
          <div className="text-[10px] text-gray-400 font-mono text-right mt-1 flex items-center justify-end gap-1 group-hover:text-white transition-colors">
            <Cpu className="w-3 h-3" /> GPU: T4 / <Brain className="w-3 h-3 ml-1" /> GEMINI 3 PRO
          </div>
        </div>
      </div>
    </header>
  );
};