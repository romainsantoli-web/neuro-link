import React from 'react';
import { Activity, Brain, Shield } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="relative">
      {/* Top accent gradient line */}
      <div className="h-[2px] bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-60" />
      
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center py-6 px-6 mb-6">
        <div className="animate-fade-in-down">
          {/* Logo / Brand */}
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30 flex items-center justify-center shadow-glow-cyan">
              <Brain className="w-5 h-5 text-neon-cyan" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-orbitron font-black text-white tracking-widest leading-none">
                NEURO-LINK
                <span className="text-sm text-neon-cyan/50 font-medium align-top ml-2 tracking-normal">v18.0</span>
              </h1>
            </div>
          </div>
          <p className="text-gray-400 font-rajdhani font-medium tracking-[3px] mt-2 uppercase text-xs md:text-sm ml-14">
            Advanced Alzheimer Diagnostic Interface
          </p>
        </div>
        
        {/* System Status Badge */}
        <div className="mt-4 md:mt-0 animate-fade-in">
          <div className="glass-card px-5 py-3 flex flex-col items-end gap-1.5 group hover:border-neon-green/30">
            <div className="flex items-center gap-2.5 text-neon-green font-orbitron text-xs font-bold tracking-wider">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-green opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-neon-green"></span>
              </span>
              SYSTEM ONLINE
            </div>
            <div className="flex items-center gap-3 text-[10px] text-gray-500 font-mono group-hover:text-gray-400 transition-colors">
              <span className="flex items-center gap-1">
                <Shield className="w-3 h-3" /> AES-256
              </span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Bottom subtle divider */}
      <div className="divider-gradient" />
    </header>
  );
};