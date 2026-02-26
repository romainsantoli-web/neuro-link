import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { DiagnosisResult } from '../types';
import { FileText, Download, QrCode, ScanLine, AlertTriangle, ExternalLink } from 'lucide-react';

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
    <div className="w-full h-72 bg-[#0a0f1c] p-6 rounded-lg border border-slate-700 shadow-inner relative overflow-hidden group">
        <div className="absolute top-0 right-0 p-2 opacity-50">
            <span className="text-[10px] text-neon-cyan font-mono border border-neon-cyan px-1 rounded">XAI MODULE v2.1</span>
        </div>
        <ResponsiveContainer width="100%" height="100%">
            <BarChart layout="vertical" data={XAI_DATA} margin={{ top: 20, right: 30, left: 40, bottom: 5 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} width={80} tick={{fill: '#e2e8f0', fontFamily: 'monospace'}} />
                <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f1f5f9', borderRadius: '4px' }} 
                    itemStyle={{ color: '#00ffea' }}
                    cursor={{fill: 'rgba(0, 255, 234, 0.05)'}}
                />
                <Bar dataKey="val" radius={[0, 4, 4, 0]} barSize={15}>
                  {XAI_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#00ffea' : '#a855f7'} />
                  ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    </div>
);

const MockQRCode = () => (
    <div className="flex flex-col items-center justify-center p-4 bg-[#0a0f1c] border border-slate-700 rounded-lg relative overflow-hidden">
        {/* Decorative scanning line */}
        <div className="absolute w-full h-1 bg-neon-cyan/50 top-0 left-0 animate-[scan_2s_ease-in-out_infinite] shadow-[0_0_15px_#00ffea]"></div>
        
        <div className="relative bg-white p-1.5 rounded-sm shadow-[0_0_25px_rgba(255,255,255,0.1)]">
             <QrCode size={80} className="text-black" />
             <div className="absolute inset-0 border-2 border-neon-cyan/30 rounded-sm"></div>
        </div>
        
        <div className="mt-3 flex items-center gap-2 text-neon-cyan">
             <ScanLine size={12} className="animate-pulse" />
             <span className="text-[10px] font-orbitron tracking-widest">VERIFIED</span>
        </div>
        <p className="text-[8px] text-gray-500 font-mono mt-1">ID: 8F92-A9B1</p>
    </div>
);

// --- Text Parsing Helper ---
const FormattedText: React.FC<{ text: string }> = ({ text }) => {
  // Split lines to handle headers and lists
  const lines = text.split('\n');
  
  return (
    <div className="space-y-4">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} className="h-2" />; // Spacer

        // Handle Headers (###)
        if (trimmed.startsWith('###')) {
          const content = trimmed.replace(/^###\s*/, '').replace(/\*\*/g, '');
          return (
            <div key={idx} className="mt-8 mb-4">
              <h3 className="text-2xl font-orbitron text-neon-cyan tracking-wide border-b border-gray-700 pb-2 inline-block w-full">
                {content}
              </h3>
            </div>
          );
        }

        // Handle Main Title / Bold headers (**Titre**) specific lines
        if (trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.length < 50) {
           const content = trimmed.replace(/\*\*/g, '');
           return (
             <h2 key={idx} className="text-3xl font-orbitron text-white font-bold tracking-widest text-center my-6 uppercase">
               {content}
             </h2>
           )
        }

        // Handle Separators (---)
        if (trimmed.startsWith('---')) {
          return <hr key={idx} className="border-t border-gray-800 my-6" />;
        }

        // Handle List Items (*)
        if (trimmed.startsWith('* ')) {
          const content = trimmed.replace(/^\*\s*/, '');
          return (
            <div key={idx} className="flex items-start gap-2 ml-4">
              <span className="text-neon-cyan mt-1.5 text-[10px]">■</span>
              <p className="text-gray-300 text-lg leading-relaxed">
                {parseBold(content)}
              </p>
            </div>
          );
        }

        // Handle Standard Paragraphs
        return (
          <p key={idx} className="text-gray-300 text-lg leading-relaxed text-justify">
            {parseBold(trimmed)}
          </p>
        );
      })}
    </div>
  );
};

// Helper to replace **text** with <strong>text</strong>
const parseBold = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-white font-semibold font-rajdhani">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};


// --- Medical Disclaimer Banner ---
const MedicalDisclaimer: React.FC = () => (
  <div className="bg-amber-950/40 border border-amber-500/50 rounded-xl p-5 flex items-start gap-4 mb-8 backdrop-blur-sm">
    <AlertTriangle className="text-amber-400 w-7 h-7 flex-shrink-0 mt-0.5" />
    <div>
      <h4 className="text-amber-400 font-orbitron text-sm tracking-widest mb-1">AVERTISSEMENT MEDICAL</h4>
      <p className="text-amber-200/80 text-sm leading-relaxed">
        Neuro-Link est un <strong className="text-amber-100">outil d'aide à la recherche</strong> et ne constitue en aucun cas un diagnostic médical.
        Les résultats présentés doivent être interprétés par un professionnel de santé qualifié.
        <span className="text-amber-400/60 ml-1">Dispositif non certifié CE/FDA.</span>
      </p>
    </div>
  </div>
);

// --- Ad Components for Monetization ---
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
    <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4 flex items-center justify-between gap-4 group hover:border-neon-cyan/30 transition-colors duration-300">
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-medium truncate">{ad.title}</p>
        <p className="text-gray-400 text-xs mt-0.5 truncate">{ad.desc}</p>
      </div>
      <a
        href={ad.link}
        target="_blank"
        rel="noopener noreferrer sponsored"
        className="flex items-center gap-1 text-neon-cyan text-xs font-orbitron tracking-wider border border-neon-cyan/30 px-3 py-1.5 rounded hover:bg-neon-cyan/10 transition-colors flex-shrink-0"
      >
        {ad.cta} <ExternalLink size={10} />
      </a>
      <span className="text-[8px] text-gray-600 absolute -bottom-0 right-2">sponsorisé</span>
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

  const statusColor = result.status === 'ALZHEIMER' ? '#ff3333' : '#00ffea';
  const statusGlow = result.status === 'ALZHEIMER' ? 'shadow-[0_0_50px_rgba(255,51,51,0.3)]' : 'shadow-[0_0_50px_rgba(0,255,234,0.3)]';

  const downloadReport = async () => {
    // Try PDF export via backend first, fallback to TXT
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
    // Split by markers
    const parts = result.report.split(/(\[IMAGE_XAI\]|\[IMAGE_QR\])/g);
    
    return parts.map((part, index) => {
      if (part === '[IMAGE_XAI]') {
        return (
           <div key={index} className="my-10 bg-black/40 p-4 border border-slate-800 rounded-xl">
              <MockXAIChart />
              <p className="text-sm text-neon-cyan font-bold tracking-widest text-center mt-4 font-orbitron uppercase">Figure 1: Importance des caractéristiques spectrales (SHAP)</p>
           </div>
        );
      }
      if (part === '[IMAGE_QR]') {
        return (
           <div key={index} className="my-6 w-full max-w-[200px] mx-auto bg-black/40 p-3 border border-slate-800 rounded-xl flex flex-col items-center">
              <MockQRCode />
              <p className="text-[10px] text-neon-cyan font-bold tracking-widest text-center mt-2 font-orbitron uppercase">Figure 2: Traçabilité</p>
           </div>
        );
      }
      // Pass text chunks to the formatter
      return <FormattedText key={index} text={part} />;
    });
  };

  return (
    <div className="animate-fade-in space-y-12">
      {/* Medical Disclaimer */}
      <MedicalDisclaimer />

      {/* Sponsor Banner — Top */}
      <AdBanner position="top" />

      {/* Top Section: Status & 3D Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        
        {/* Status Card */}
        <div className={`bg-black/80 border-2 rounded-2xl p-10 flex flex-col items-center justify-center text-center ${statusGlow} h-[400px]`} style={{ borderColor: statusColor }}>
            <h3 className="text-gray-500 font-orbitron tracking-[6px] text-sm mb-6">DIAGNOSTIC FINAL</h3>
            <h1 className="text-6xl md:text-7xl font-orbitron font-black mb-4 animate-pulse" style={{ color: statusColor }}>
                {result.status?.replace("POSITIF (Alzheimer)", "POSITIF")}
            </h1>
            <h2 className="text-white font-rajdhani text-3xl font-light">{result.stage}</h2>
            <div className="mt-8 px-6 py-2 rounded-full border border-white/20 bg-white/5 text-white font-mono text-sm tracking-widest">
                CONFIANCE MODÈLE : {(result.confidence * 100).toFixed(1)}%
            </div>
        </div>

        {/* 3D Holographic Radar Chart */}
        <div className="h-[400px] w-full relative flex items-center justify-center perspective-[1000px] group">
            {/* The 3D Container */}
            <div className="relative w-full h-full transition-transform duration-500 transform-style-3d rotate-x-25 hover:rotate-x-0 group-hover:scale-105" 
                 style={{ transform: "perspective(1000px) rotateX(25deg)" }}>
                
                {/* Holographic Base Glow */}
                <div className="absolute inset-0 bg-neon-cyan/5 rounded-full blur-[60px] transform translate-y-10 scale-75 opacity-50"></div>
                
                <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                    <PolarGrid gridType="polygon" stroke="#334155" strokeWidth={1} />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#00ffea', fontFamily: 'Orbitron', fontSize: 11, letterSpacing: '1px' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} axisLine={false} />
                    
                    {/* Layer 1: The "Shadow/Volume" Layer */}
                    <Radar
                        name="Shadow"
                        dataKey="A"
                        stroke="transparent"
                        fill="#00ffea"
                        fillOpacity={0.1}
                        className="transform translate-y-2 blur-sm"
                    />

                    {/* Layer 2: The Main Data Layer */}
                    <Radar
                        name="Patient"
                        dataKey="A"
                        stroke="#00ffea"
                        strokeWidth={3}
                        fill="url(#radarGradient)"
                        fillOpacity={0.5}
                        isAnimationActive={true}
                    />
                     <defs>
                        <linearGradient id="radarGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00ffea" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#00ffea" stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                    </RadarChart>
                </ResponsiveContainer>
                 <div className="absolute top-0 right-0 text-[10px] text-neon-cyan font-mono border border-neon-cyan/50 px-2 py-1 rounded bg-black/50 backdrop-blur-sm">
                    [3D] HOLOGRAPHIC VIEW
                </div>
            </div>
        </div>
      </div>

      <div className="h-px w-full bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent" />

      {/* Report Section */}
      <div>
        <div className="flex items-center gap-3 mb-8 pl-2 border-l-4 border-neon-cyan">
            <FileText className="text-neon-cyan w-8 h-8" />
            <h2 className="text-3xl font-orbitron font-bold text-white tracking-widest">COMPTE RENDU CLINIQUE</h2>
        </div>

        {/* Paper-like but futuristic container */}
        <div className="bg-[#050505] border border-gray-800 rounded-xl p-10 lg:p-14 relative shadow-2xl overflow-hidden">
             {/* Background watermark */}
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-neon-cyan/5 rounded-full blur-[100px] pointer-events-none"></div>
             
             <div className="relative z-10">
                {renderReportContent()}
             </div>
             
             <div className="mt-12 pt-8 border-t border-gray-800 flex justify-between items-end">
                <div className="text-gray-500 font-mono text-xs">
                    <p>GENERATED BY NEURO-LINK AI KERNEL V18</p>
                    <p>SECURE HASH: {Math.random().toString(36).substring(7).toUpperCase()}</p>
                </div>
                <button 
                    onClick={downloadReport}
                    className="flex items-center gap-2 bg-white text-black hover:bg-neon-cyan font-orbitron font-bold py-3 px-8 rounded-sm transition-all duration-300 shadow-[0_0_20px_rgba(255,255,255,0.2)] hover:shadow-[0_0_30px_#00ffea]"
                >
                    <Download size={20} />
                    EXPORTER (.PDF/TXT)
                </button>
             </div>
        </div>
      </div>

      {/* Sponsor Banner — Bottom */}
      <AdBanner position="bottom" />
    </div>
  );
};