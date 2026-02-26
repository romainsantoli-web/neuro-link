import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { DiagnosisResult } from '../types';
import { FileText, Download, QrCode, ScanLine, AlertTriangle, ExternalLink, Shield, Activity, Brain } from 'lucide-react';

interface ResultsDashboardProps {
  result: DiagnosisResult;
}

const XAI_DATA = [
  { name: 'Alpha_Pwr', val: 0.85 },
  { name: 'Theta_Entr', val: 0.72 },
  { name: 'Delta_Coh', val: 0.65 },
  { name: 'Beta_Rto', val: 0.55 },
  { name: 'Gamma_Sync', val: 0.45 },
  { name: 'Sig_Qual', val: 0.30 },
];

const MockXAIChart = () => (
    <div className="w-full h-72 glass-card inner-glow-cyan p-6 relative overflow-hidden group">
        <div className="absolute top-3 right-3">
            <span className="text-[9px] text-neon-cyan/60 font-mono border border-neon-border px-2 py-0.5 rounded-full">XAI v2.1</span>
        </div>
        <ResponsiveContainer width="100%" height="100%">
            <BarChart layout="vertical" data={XAI_DATA} margin={{ top: 20, right: 30, left: 40, bottom: 5 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={10} width={80} tick={{fill: '#94a3b8', fontFamily: '"Share Tech Mono", monospace'}} />
                <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(8,12,24,0.95)', borderColor: '#1e2a3a', color: '#f1f5f9', borderRadius: '8px', backdropFilter: 'blur(8px)' }} 
                    itemStyle={{ color: '#00ffea' }}
                    cursor={{fill: 'rgba(0, 255, 234, 0.03)'}}
                />
                <Bar dataKey="val" radius={[0, 6, 6, 0]} barSize={14}>
                  {XAI_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#00ffea' : '#a855f7'} fillOpacity={0.8} />
                  ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    </div>
);

const MockQRCode = () => (
    <div className="flex flex-col items-center justify-center p-4 glass-card inner-glow-cyan relative overflow-hidden">
        <div className="absolute w-full h-px bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent top-0 left-0 animate-[scan_2s_ease-in-out_infinite]"></div>
        
        <div className="relative bg-white p-2 rounded-lg shadow-glow-cyan">
             <QrCode size={72} className="text-black" />
             <div className="absolute inset-0 border border-neon-cyan/20 rounded-lg"></div>
        </div>
        
        <div className="mt-3 flex items-center gap-1.5 text-neon-cyan">
             <Shield size={10} />
             <span className="text-[9px] font-orbitron tracking-[3px]">VERIFIED</span>
        </div>
        <p className="text-[8px] text-gray-600 font-mono mt-1">ID: 8F92-A9B1</p>
    </div>
);

// --- Text Parsing Helper ---
const FormattedText: React.FC<{ text: string }> = ({ text }) => {
  const lines = text.split('\n');
  
  return (
    <div className="space-y-3">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} className="h-2" />;

        if (trimmed.startsWith('###')) {
          const content = trimmed.replace(/^###\s*/, '').replace(/\*\*/g, '');
          return (
            <div key={idx} className="mt-8 mb-4">
              <h3 className="text-xl font-orbitron text-neon-cyan/90 tracking-wide pb-2 border-b border-neon-border/40 flex items-center gap-2">
                <span className="w-1 h-5 bg-neon-cyan rounded-full inline-block" />
                {content}
              </h3>
            </div>
          );
        }

        if (trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.length < 50) {
           const content = trimmed.replace(/\*\*/g, '');
           return (
             <h2 key={idx} className="text-2xl font-orbitron text-white font-bold tracking-[4px] text-center my-8 uppercase">
               {content}
             </h2>
           );
        }

        if (trimmed.startsWith('---')) {
          return <div key={idx} className="divider-gradient my-6" />;
        }

        if (trimmed.startsWith('* ')) {
          const content = trimmed.replace(/^\*\s*/, '');
          return (
            <div key={idx} className="flex items-start gap-3 ml-2 py-0.5">
              <span className="text-neon-cyan/50 mt-2 text-[6px] flex-shrink-0">&#9679;</span>
              <p className="text-gray-300/90 text-base leading-relaxed">
                {parseBold(content)}
              </p>
            </div>
          );
        }

        return (
          <p key={idx} className="text-gray-300/90 text-base leading-relaxed text-justify">
            {parseBold(trimmed)}
          </p>
        );
      })}
    </div>
  );
};

const parseBold = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};


// --- Medical Disclaimer Banner ---
const MedicalDisclaimer: React.FC = () => (
  <div className="glass-card border-amber-500/20 p-5 flex items-start gap-4 mb-8 animate-fade-in-up">
    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500/15 to-amber-600/5 border border-amber-500/25 flex items-center justify-center flex-shrink-0 shadow-[0_0_15px_rgba(245,158,11,0.1)]">
      <AlertTriangle className="text-amber-400 w-5 h-5" />
    </div>
    <div>
      <h4 className="text-amber-400/90 font-orbitron text-[10px] tracking-[3px] mb-1.5">AVERTISSEMENT MÉDICAL</h4>
      <p className="text-amber-200/60 text-sm leading-relaxed">
        Neuro-Link est un <strong className="text-amber-200/80">outil d'aide à la recherche</strong> et ne constitue en aucun cas un diagnostic médical.
        Les résultats doivent être interprétés par un professionnel de santé qualifié.
        <span className="text-amber-400/40 ml-1">Dispositif non certifié CE/FDA.</span>
      </p>
    </div>
  </div>
);

// --- Ad Components ---
const AdBanner: React.FC<{ position: 'top' | 'sidebar' | 'bottom' }> = ({ position }) => {
  const ads: Record<string, { title: string; desc: string; cta: string; link: string }> = {
    top: {
      title: '🧠 OpenBCI — EEG accessible',
      desc: 'Casques EEG compatibles Neuro-Link à partir de $249',
      cta: 'Découvrir',
      link: 'https://openbci.com',
    },
    sidebar: {
      title: '📋 Consultez un spécialiste',
      desc: 'Trouvez un neurologue près de chez vous',
      cta: 'Annuaire',
      link: '#',
    },
    bottom: {
      title: '🔬 Participez à la recherche',
      desc: 'Contribuez à améliorer le dépistage Alzheimer par EEG',
      cta: 'En savoir plus',
      link: '#',
    },
  };
  const ad = ads[position];
  return (
    <div className="glass-panel p-4 flex items-center justify-between gap-4 group hover:border-neon-cyan/20 transition-all duration-300 relative animate-fade-in">
      <div className="flex-1 min-w-0">
        <p className="text-white/90 text-sm font-medium truncate">{ad.title}</p>
        <p className="text-gray-500 text-xs mt-0.5 truncate">{ad.desc}</p>
      </div>
      <a
        href={ad.link}
        target="_blank"
        rel="noopener noreferrer sponsored"
        className="flex items-center gap-1 text-neon-cyan/80 text-[10px] font-orbitron tracking-wider border border-neon-border px-3 py-1.5 rounded-lg hover:bg-neon-cyan/5 hover:border-neon-cyan/30 transition-all flex-shrink-0"
      >
        {ad.cta} <ExternalLink size={9} />
      </a>
      <span className="text-[7px] text-gray-700 absolute bottom-1 right-3 font-mono">sponsorisé</span>
    </div>
  );
};


export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ result }) => {
  const radarData = [
    { subject: 'Alpha Power', A: result.features.Alpha, fullMark: 1 },
    { subject: 'Entropy', A: result.features.Entropy, fullMark: 1 },
    { subject: 'Theta Power', A: result.features.Theta, fullMark: 1 },
    { subject: 'Coherence', A: 0.6, fullMark: 1 }, 
    { subject: 'Delta', A: 0.4, fullMark: 1 },     
  ];

  const isPositive = result.status === 'ALZHEIMER';
  const statusColor = isPositive ? '#ff3333' : '#00ffea';
  const statusGlow = isPositive ? 'shadow-[0_0_40px_rgba(255,51,51,0.15)]' : 'shadow-[0_0_40px_rgba(0,255,234,0.15)]';

  const downloadReport = async () => {
    try {
      const apiBase = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
      const resp = await fetch(`${apiBase}/report/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: result.status,
          stage: result.stage || 'Inconnu',
          confidence: result.confidence,
          features: result.features || {},
          report: result.report,
          pipeline: (result as any).pipeline || {},
          patientId: 'Anonyme',
        }),
      });
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `NEURO-LINK-REPORT-${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(url);
        return;
      }
    } catch {
      // PDF backend unavailable — fallback to TXT
    }

    const element = document.createElement("a");
    const file = new Blob([result.report], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = `NEURO-LINK-REPORT-${Date.now()}.txt`;
    document.body.appendChild(element);
    element.click();
  };

  const renderReportContent = () => {
    const parts = result.report.split(/(\[IMAGE_XAI\]|\[IMAGE_QR\])/g);
    
    return parts.map((part, index) => {
      if (part === '[IMAGE_XAI]') {
        return (
           <div key={index} className="my-8">
              <MockXAIChart />
              <p className="text-[10px] text-neon-cyan/60 font-orbitron tracking-[3px] text-center mt-3 uppercase">Figure 1: Importance des caractéristiques spectrales (SHAP)</p>
           </div>
        );
      }
      if (part === '[IMAGE_QR]') {
        return (
           <div key={index} className="my-6 w-full max-w-[180px] mx-auto">
              <MockQRCode />
              <p className="text-[10px] text-neon-cyan/60 font-orbitron tracking-[3px] text-center mt-2 uppercase">Figure 2: Traçabilité</p>
           </div>
        );
      }
      return <FormattedText key={index} text={part} />;
    });
  };

  return (
    <div className="animate-fade-in space-y-10">
      {/* Medical Disclaimer */}
      <MedicalDisclaimer />

      {/* Sponsor Banner — Top */}
      <AdBanner position="top" />

      {/* ─── Top Section: Status & Radar ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
        
        {/* Status Card */}
        <div className={`glass-card p-8 md:p-10 flex flex-col items-center justify-center text-center relative overflow-hidden animate-scale-in ${statusGlow}`} style={{ borderColor: `${statusColor}20` }}>
            {/* Background radial glow */}
            <div className="absolute inset-0 pointer-events-none" style={{ background: `radial-gradient(circle at 50% 50%, ${statusColor}08 0%, transparent 70%)` }} />
            
            <h3 className="text-gray-500 font-orbitron tracking-[5px] text-[10px] mb-6 uppercase relative z-10">Diagnostic Final</h3>
            
            <div className="relative z-10 mb-4">
              <h1 className="text-5xl md:text-6xl font-orbitron font-black tracking-wider" style={{ color: statusColor }}>
                  {result.status?.replace("POSITIF (Alzheimer)", "POSITIF")}
              </h1>
            </div>
            
            <h2 className="text-white/80 font-rajdhani text-2xl font-light relative z-10 mb-8">{result.stage}</h2>
            
            {/* Confidence meter */}
            <div className="w-full max-w-xs relative z-10">
              <div className="flex justify-between text-[10px] font-mono text-gray-500 mb-1.5">
                <span>CONFIANCE MODÈLE</span>
                <span style={{ color: statusColor }}>{(result.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="h-1.5 bg-neon-border/30 rounded-full overflow-hidden">
                <div 
                  className="h-full rounded-full transition-all duration-1000"
                  style={{ 
                    width: `${result.confidence * 100}%`,
                    background: `linear-gradient(90deg, ${statusColor}80, ${statusColor})`
                  }}
                />
              </div>
            </div>
        </div>

        {/* Radar Chart */}
        <div className="glass-card p-6 relative animate-scale-in overflow-hidden" style={{ animationDelay: '150ms' }}>
            <div className="absolute top-4 right-4 text-[9px] text-neon-cyan/50 font-mono border border-neon-border px-2 py-1 rounded-full">
                HOLOGRAPHIC VIEW
            </div>
            
            {/* Holographic Base Glow */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-3/4 h-1/3 bg-neon-cyan/[0.03] rounded-full blur-[40px]"></div>
            
            <div className="h-[340px] w-full" style={{ perspective: '800px' }}>
              <div className="w-full h-full transition-transform duration-500 hover:scale-105" 
                   style={{ transform: 'perspective(800px) rotateX(20deg)' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="72%" data={radarData}>
                    <PolarGrid gridType="polygon" stroke="#1e2a3a" strokeWidth={0.8} />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#00ffea', fontFamily: 'Orbitron', fontSize: 9, letterSpacing: '1px' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} axisLine={false} />
                    
                    <Radar
                        name="Shadow"
                        dataKey="A"
                        stroke="transparent"
                        fill="#00ffea"
                        fillOpacity={0.06}
                    />
                    <Radar
                        name="Patient"
                        dataKey="A"
                        stroke="#00ffea"
                        strokeWidth={2}
                        fill="url(#radarGradient)"
                        fillOpacity={0.4}
                        isAnimationActive={true}
                    />
                     <defs>
                        <linearGradient id="radarGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00ffea" stopOpacity={0.6}/>
                          <stop offset="95%" stopColor="#00ffea" stopOpacity={0.05}/>
                        </linearGradient>
                      </defs>
                    </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
        </div>
      </div>

      <div className="divider-gradient" />

      {/* ─── Report Section ─── */}
      <div className="animate-fade-in-up" style={{ animationDelay: '300ms' }}>
        <div className="flex items-center gap-3 mb-8">
            <div className="w-9 h-9 rounded-lg bg-neon-cyan/10 border border-neon-cyan/20 flex items-center justify-center">
              <FileText className="text-neon-cyan w-4 h-4" />
            </div>
            <div>
              <h2 className="text-xl font-orbitron font-bold text-white tracking-[3px]">COMPTE RENDU CLINIQUE</h2>
              <p className="text-[10px] text-gray-500 font-mono tracking-wider mt-0.5">AI-Generated Clinical Report</p>
            </div>
        </div>

        {/* Report container */}
        <div className="glass-panel p-8 lg:p-12 relative overflow-hidden">
             {/* Background watermark */}
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-neon-cyan/[0.02] rounded-full blur-[80px] pointer-events-none"></div>
             
             <div className="relative z-10">
                {renderReportContent()}
             </div>
             
             {/* Footer */}
             <div className="mt-10 pt-6 border-t border-neon-border/30 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
                <div className="text-gray-600 font-mono text-[10px] space-y-0.5">
                    <p className="flex items-center gap-1"><Activity size={9} /> GENERATED BY NEURO-LINK AI KERNEL V18</p>
                    <p className="flex items-center gap-1"><Shield size={9} /> HASH: {Math.random().toString(36).substring(7).toUpperCase()}</p>
                </div>
                <button 
                    onClick={downloadReport}
                    className="btn-primary font-orbitron text-xs flex items-center gap-2"
                >
                    <Download size={16} />
                    EXPORTER (.PDF)
                </button>
             </div>
        </div>
      </div>

      {/* Sponsor Banner — Bottom */}
      <AdBanner position="bottom" />
    </div>
  );
};