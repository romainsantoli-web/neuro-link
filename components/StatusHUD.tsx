import React from 'react';
import { Terminal, Bot, BrainCircuit, ShieldCheck, WifiOff, HardDrive } from 'lucide-react';

interface StatusHUDProps {
  isConnected: boolean;
}

const Card: React.FC<{ title: string; value: string; color: string; icon: React.ReactNode; animate?: boolean }> = ({ title, value, color, icon, animate }) => (
  <div className={`bg-neon-panel border border-neon-border p-4 rounded-lg flex items-center justify-between shadow-[inset_0_0_20px_rgba(0,0,0,0.5)] transition-all duration-500 ${animate ? 'animate-pulse' : ''}`} style={{ borderColor: `${color}40` }}>
    <div>
      <h4 className="text-gray-500 text-xs font-orbitron tracking-widest mb-1">{title}</h4>
      <h2 className={`text-xl font-bold font-orbitron tracking-wide transition-colors duration-300`} style={{ color }}>{value}</h2>
    </div>
    <div style={{ color }} className="opacity-80">
      {icon}
    </div>
  </div>
);

export const StatusHUD: React.FC<StatusHUDProps> = ({ isConnected }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <Card 
        title="KERNEL LINK" 
        value={isConnected ? "ESTABLISHED" : "OFFLINE"} 
        color={isConnected ? "#00ffea" : "#555"} 
        icon={isConnected ? <Terminal size={24} /> : <WifiOff size={24} />} 
      />
      <Card 
        title="STORAGE / DRIVE" 
        value={isConnected ? "MOUNTED" : "UNREACHABLE"} 
        color={isConnected ? "#3fb950" : "#555"} 
        icon={<HardDrive size={24} />} 
      />
      <Card 
        title="AI MODELS" 
        value={isConnected ? "AD-FORMER V2" : "STANDBY"} 
        color={isConnected ? "#a855f7" : "#555"} 
        icon={<BrainCircuit size={24} />} 
        animate={isConnected}
      />
      <Card 
        title="SECURITY" 
        value="ENCRYPTED" 
        color="#ff3333" 
        icon={<ShieldCheck size={24} />} 
      />
    </div>
  );
};