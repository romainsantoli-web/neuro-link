import React from 'react';
import { Terminal, Bot, BrainCircuit, ShieldCheck, WifiOff, HardDrive } from 'lucide-react';

interface StatusHUDProps {
  isConnected: boolean;
}

const Card: React.FC<{ title: string; value: string; color: string; icon: React.ReactNode; animate?: boolean; delay?: string }> = ({ title, value, color, icon, animate, delay = '0ms' }) => (
  <div 
    className={`glass-card inner-glow-cyan p-5 flex items-center gap-4 group hover:scale-[1.02] transition-all duration-300 animate-fade-in-up`}
    style={{ animationDelay: delay }}
  >
    {/* Icon container */}
    <div 
      className={`w-11 h-11 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-300 ${animate ? 'animate-pulse-slow' : ''}`}
      style={{ 
        background: `linear-gradient(135deg, ${color}15, ${color}08)`,
        border: `1px solid ${color}30`,
        boxShadow: `0 0 15px ${color}10`
      }}
    >
      <div style={{ color }} className="opacity-90 group-hover:opacity-100 transition-opacity">
        {icon}
      </div>
    </div>
    
    {/* Text */}
    <div className="min-w-0">
      <h4 className="text-gray-500 text-[10px] font-orbitron tracking-[3px] mb-1 uppercase">{title}</h4>
      <h2 
        className="text-lg font-bold font-orbitron tracking-wide transition-colors duration-300 truncate"
        style={{ color }}
      >
        {value}
      </h2>
    </div>
  </div>
);

export const StatusHUD: React.FC<StatusHUDProps> = ({ isConnected }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <Card 
        title="KERNEL LINK" 
        value={isConnected ? "ESTABLISHED" : "OFFLINE"} 
        color={isConnected ? "#60A5FA" : "#555"} 
        icon={isConnected ? <Terminal size={20} /> : <WifiOff size={20} />}
        delay="0ms"
      />
      <Card 
        title="STORAGE" 
        value={isConnected ? "MOUNTED" : "UNREACHABLE"} 
        color={isConnected ? "#3fb950" : "#555"} 
        icon={<HardDrive size={20} />}
        delay="100ms"
      />
      <Card 
        title="AI MODELS" 
        value={isConnected ? "AD-FORMER V2" : "STANDBY"} 
        color={isConnected ? "#818CF8" : "#555"} 
        icon={<BrainCircuit size={20} />} 
        animate={isConnected}
        delay="200ms"
      />
      <Card 
        title="SECURITY" 
        value="ENCRYPTED" 
        color="#f59e0b" 
        icon={<ShieldCheck size={20} />}
        delay="300ms"
      />
    </div>
  );
};