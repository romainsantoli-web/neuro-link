import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { StatusHUD } from './components/StatusHUD';
import { ConsoleBox } from './components/ConsoleBox';
import { NarratorBox, LogigramType } from './components/NarratorBox';
import { ResultsDashboard } from './components/ResultsDashboard';
import { ChatBot } from './components/ChatBot';
import { AdminDashboard } from './components/AdminDashboard';
import { PricingPage } from './components/PricingPage';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { IDLE_WAVE_DATA, MOCK_REPORT_TEMPLATE } from './constants';
import { AppState, LogEntry, DiagnosisResult } from './types';
import { checkMemoryHealth, getMemoryContext, ingestMemoryRecord } from './services/memoryApi';
import { UploadCloud, Link as LinkIcon, Wifi, WifiOff, ServerCog } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

export default function App() {
  const [appState, setAppState] = useState<AppState>('IDLE');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [narratorMessage, setNarratorMessage] = useState<string>("SYSTEM STANDBY // AWAITING NEURAL DATA");
  const [logigramType, setLogigramType] = useState<LogigramType>('default');
  const [result, setResult] = useState<DiagnosisResult | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => uuidv4());
  const [showAdmin, setShowAdmin] = useState(false);
  const [showPricing, setShowPricing] = useState(false);
  
  // API State
  // In production (integrated), the API is at the same origin under /api
  const [apiUrl, setApiUrl] = useState<string>(""); 
  const [isApiConnected, setIsApiConnected] = useState<boolean>(false);
  const [isMemoryConnected, setIsMemoryConnected] = useState<boolean>(false);
  const [isAutoConnecting, setIsAutoConnecting] = useState<boolean>(true);

  // Helper to add logs
  const addLog = (msg: string, type: LogEntry['type'] = 'info') => {
    setLogs(prev => [...prev, { id: uuidv4(), message: msg, type }]);
  };

  // Helper delay
  const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  // --- AUTO-CONNECTION ON MOUNT ---
  useEffect(() => {
    // Secret admin shortcut: Ctrl+Shift+A
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'A') {
        e.preventDefault();
        setShowAdmin(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    const autoConnect = async () => {
      // 1. Try standard production path first
      const productionPath = "/api"; 
      const success = await attemptConnection(productionPath, true);
      
      if (success) {
        setApiUrl(productionPath);
      } else {
        // 2. Fallback to localhost for dev
        const localPath = "http://localhost:8000";
        const localSuccess = await attemptConnection(localPath, true);
        if (localSuccess) setApiUrl(localPath);
      }
      setIsAutoConnecting(false);
    };
    autoConnect();
  }, []);

  const attemptConnection = async (url: string, silent: boolean = false): Promise<boolean> => {
    if (!silent) addLog(`PINGING KERNEL AT ${url}...`, 'cmd');
    
    try {
      // Normalize URL: remove trailing slash
      const cleanUrl = url.replace(/\/$/, "");
      
      const response = await fetch(`${cleanUrl}/health`, { 
        method: 'GET',
        headers: { 
          'ngrok-skip-browser-warning': 'true',
          'Content-Type': 'application/json'
        } 
      });
      
      if (response.ok) {
        setIsApiConnected(true);

        const memoryConnected = await checkMemoryHealth(cleanUrl);
        setIsMemoryConnected(memoryConnected);

        if (!silent) {
           addLog("KERNEL CONNECTION ESTABLISHED", 'success');
          addLog(memoryConnected ? "MEMORY PIPELINE ONLINE" : "MEMORY PIPELINE OFFLINE", memoryConnected ? 'success' : 'warning');
           setLogigramType('hex');
           setNarratorMessage("Noyau IA connecté. Modèles chargés.");
           await wait(1000);
           setLogigramType('default');
        }
        return true;
      }
    } catch (e) {
      setIsApiConnected(false);
      setIsMemoryConnected(false);
      if (!silent) {
        addLog(`CONNECTION FAILED: ${e}`, 'error');
        setNarratorMessage("Connexion échouée. Vérifiez l'URL du backend.");
      }
    }
    return false;
  };

  const manualConnect = () => {
     attemptConnection(apiUrl);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // --- MODE RÉEL (API) ---
    if (isApiConnected) {
        setAppState('ANALYZING');
        setLogs([]);
        setLogigramType('hex');
        setNarratorMessage("Transmission des données au noyau unifié...");
        addLog(`UPLOADING: ${file.name} -> INTEGRATED KERNEL`, 'cmd');

        try {
            const formData = new FormData();
            formData.append('file', file);

            if (isMemoryConnected) {
                const contextResponse = await getMemoryContext(
                  apiUrl,
                  `EEG analysis context for file ${file.name}`,
                  sessionId
                );

                if (contextResponse?.context) {
                  formData.append('memory_context', contextResponse.context);
                  addLog(`MEMORY CONTEXT ATTACHED (${contextResponse.sourceCount} SOURCES)`, 'info');
                } else {
                  addLog('NO MEMORY CONTEXT FOUND FOR THIS INPUT', 'warning');
                }
            }

            formData.append('session_id', sessionId);

            const visualFeedbackInterval = setInterval(() => {
                 setLogigramType(prev => prev === 'neural' ? 'waveform' : 'neural');
            }, 2000);

            // Clean URL handling for relative paths
            const endpoint = apiUrl.startsWith('/') ? `${apiUrl}/analyze` : `${apiUrl}/analyze`;

            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: { 'ngrok-skip-browser-warning': 'true' }
            });

            clearInterval(visualFeedbackInterval);

            if (!response.ok) throw new Error("Server Error");

            setLogigramType('thinking');
            setNarratorMessage("Inférence en cours (PyTorch/Transformers)...");
            addLog("DATA RECEIVED. PROCESSING SEQUENCES...", 'info');

            const data = await response.json();

            if (data.error) throw new Error(data.error);

            setResult({
                status: data.status,
                stage: data.stage,
                confidence: data.confidence,
                features: data.features,
                report: data.report
            });

            if (isMemoryConnected) {
              const memorySaved = await ingestMemoryRecord(apiUrl, {
                sessionId,
                fileName: file.name,
                diagnosisStatus: data.status ?? null,
                stage: data.stage ?? '',
                confidence: Number(data.confidence ?? 0),
                features: data.features ?? {},
                report: data.report ?? '',
                createdAt: new Date().toISOString(),
              });

              addLog(
                memorySaved
                  ? 'MEMORY UPDATED WITH LATEST ANALYSIS'
                  : 'MEMORY UPDATE FAILED (NON-BLOCKING)',
                memorySaved ? 'success' : 'warning'
              );
            }

            addLog("ANALYSIS COMPLETE.", 'success');
            setNarratorMessage("Analyse terminée. Rapport généré.");
            setAppState('COMPLETE');
            setLogigramType('default');

        } catch (error) {
            console.error(error);
            addLog(`KERNEL ERROR: ${error}`, 'error');
            setNarratorMessage("Erreur critique lors de la communication avec le noyau.");
            setAppState('IDLE');
            setLogigramType('default');
        }
        return;
    }

    // --- MODE SIMULATION (Fallback) ---
    addLog("WARNING: NO KERNEL DETECTED. RUNNING SIMULATION MODE.", 'warning');
    runSimulation(file);
  };

  const runSimulation = async (file: File) => {
    setAppState('ANALYZING');
    setLogs([]); 
    
    // Step 1: Initialization
    setLogigramType('hex');
    setNarratorMessage("MODE SIMULATION: Démarrage du protocole.");
    addLog(`MOUNTING SCRIPT: /script-alz/patient_depistage.py --file ${file.name}`, 'cmd');
    await wait(1000);
    
    // Step 2: Processing
    setLogigramType('waveform');
    addLog("FILTER: Notch 50Hz Applied", 'success');
    setNarratorMessage("Filtrage des interférences électriques ambiantes.");
    await wait(1500);

    setLogigramType('neural');
    addLog("EXTRACT: Alpha/Beta Power Ratios", 'info');
    setNarratorMessage("Extraction des biomarqueurs Alpha et Theta.");
    await wait(1500);

    // Step 3: Finding Report 
    setLogigramType('default');
    addLog(`REPORT FOUND: /data/${uuidv4().substring(0,8)}/rapport.txt`, 'success');
    await wait(1200);

    // Step 4: Staging
    setLogigramType('hex');
    addLog("DETECTED: POSITIVE (94.2%). Starting Staging...", 'warning');
    setNarratorMessage("ALERTE : Marqueurs positifs détectés. Classification en cours.");
    await wait(1500);

    // Step 5: Gemini Generation (Thinking Mode)
    setLogigramType('thinking');
    addLog("INITIATING GEMINI 3 PRO PREVIEW...", 'cmd');
    setNarratorMessage("Activation du 'Thinking Mode' Gemini 3.0.");
    await wait(3000);
    
    addLog("PIPELINE SUCCESS. Report Ready.", 'success');
    setNarratorMessage("Simulation terminée.");
    setLogigramType('default');

    // Set Final Result
    const now = new Date();
    const finalReport = MOCK_REPORT_TEMPLATE
      .replace('{{DATE}}', now.toLocaleDateString())
      .replace('{{TIME}}', now.toLocaleTimeString())
      .replace('{{STATUS}}', 'POSITIF (Alzheimer)')
      .replace('{{STAGE}}', 'Stade 2 (Modéré)')
      .replace('{{CONFIDENCE}}', '94.2');

    setResult({
      status: 'ALZHEIMER',
      stage: 'Stade 2 (Modéré)',
      confidence: 0.942,
      features: { Alpha: 0.35, Entropy: 0.82, Theta: 0.7 },
      report: finalReport
    });
    
    setAppState('COMPLETE');
  };

  const resetAnalysis = () => {
    setAppState('IDLE');
    setLogs([]);
    setResult(null);
    setSessionId(uuidv4());
    setNarratorMessage("SYSTEM STANDBY // AWAITING NEURAL DATA");
    setLogigramType('default');
  };

  return (
    <div className="min-h-screen font-rajdhani text-slate-200 pb-20">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6">
        
        {/* ─── CONNECTION BAR ─── */}
        <div className="mb-8 glass-panel animate-fade-in-down overflow-hidden">
             <div className="flex flex-col md:flex-row gap-3 items-center p-3 text-sm">
                {/* Status indicator */}
                <div className={`flex items-center gap-2.5 whitespace-nowrap px-3 py-1 rounded-lg transition-all duration-300 ${isApiConnected 
                    ? 'bg-neon-green/8 text-neon-green' 
                    : 'text-gray-500'}`}>
                    {isApiConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
                    <span className="font-orbitron font-bold tracking-wider text-xs">
                      {isApiConnected ? 'KERNEL ONLINE' : 'DISCONNECTED'}
                    </span>
                </div>
                
                {/* URL input */}
                <div className="flex-1 w-full flex items-center gap-2 border-l border-neon-border pl-4 relative">
                    {isAutoConnecting && (
                      <span className="absolute right-0 text-xs text-neon-cyan animate-pulse mr-4 font-mono">
                        AUTO-DETECTING...
                      </span>
                    )}
                    <ServerCog size={14} className="text-gray-600" />
                    <input 
                        type="text" 
                        placeholder={isApiConnected ? `Connected via ${apiUrl}` : "Backend URL (default: /api)"}
                        className="w-full bg-transparent text-white/90 font-mono text-sm placeholder-gray-600 outline-none disabled:opacity-50"
                        value={apiUrl}
                        onChange={(e) => setApiUrl(e.target.value)}
                        disabled={isAutoConnecting}
                    />
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-2">
                  <button 
                      onClick={manualConnect}
                      disabled={!apiUrl || isAutoConnecting}
                      className={`px-5 py-2 rounded-lg font-orbitron font-bold text-xs transition-all duration-300 ${isApiConnected 
                          ? 'bg-neon-green/15 text-neon-green border border-neon-green/25 shadow-glow-green cursor-default' 
                          : 'bg-neon-border/30 text-gray-400 hover:bg-neon-border/50 hover:text-white border border-neon-border'}`}
                  >
                      {isApiConnected ? 'ONLINE' : 'CONNECT'}
                  </button>

                  {isApiConnected && (
                    <button
                      onClick={() => setShowPricing(true)}
                      className="px-3 py-2 rounded-lg font-orbitron text-[10px] font-bold text-neon-cyan/70 border border-neon-cyan/20
                                 hover:text-neon-cyan hover:border-neon-cyan/40 hover:bg-neon-cyan/5 transition-all duration-300"
                      title="Voir les plans et tarifs"
                    >
                      PLANS
                    </button>
                  )}
                </div>
             </div>
        </div>

        {/* ─── IDLE STATE ─── */}
        {appState === 'IDLE' && (
          <div className="animate-fade-in">
             <StatusHUD isConnected={isApiConnected} />
               
             {/* Waveform Visualization */}
             <div className="h-44 w-full mb-8 relative glass-panel overflow-hidden">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={IDLE_WAVE_DATA}>
                    <Line type="monotone" dataKey="alpha" stroke="#60A5FA" strokeWidth={2} dot={false} animationDuration={3000} />
                    <Line type="monotone" dataKey="theta" stroke="#818CF8" strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
                    </LineChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <h3 className="text-gray-600 font-orbitron text-sm md:text-base opacity-40 tracking-[8px] uppercase">
                      Awaiting Neural Data
                    </h3>
                </div>
                {/* Fade edges */}
                <div className="absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-neon-panel to-transparent pointer-events-none" />
                <div className="absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-neon-panel to-transparent pointer-events-none" />
             </div>

             {/* Upload Zone */}
             <div className="mt-10 glass-card border-2 border-dashed border-neon-border hover:border-neon-cyan/40 p-10 md:p-14 transition-all duration-500 group relative overflow-hidden cursor-pointer animate-fade-in-up" style={{ animationDelay: '200ms' }}>
                {/* Background gradient on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/[0.03] via-transparent to-neon-purple/[0.02] opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                {/* Scan line effect on hover */}
                <div className="absolute inset-0 overflow-hidden opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <div className="absolute w-full h-px bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent" style={{ animation: 'line-scan 3s ease-in-out infinite' }} />
                </div>
                
                <div className="flex flex-col items-center justify-center text-center relative z-10">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-neon-cyan/10 to-neon-purple/10 border border-neon-border group-hover:border-neon-cyan/30 flex items-center justify-center mb-6 transition-all duration-300 group-hover:shadow-glow-cyan">
                    <UploadCloud className="w-8 h-8 text-gray-500 group-hover:text-neon-cyan transition-colors duration-300" />
                  </div>
                  
                  <h3 className="text-xl md:text-2xl font-orbitron text-white/90 mb-2 tracking-wide">
                    DRAG & DROP EEG FILE
                  </h3>
                  <p className="text-gray-500 mb-8 font-mono text-xs tracking-wide">
                    Supported: EEGLAB (.set) &bull; European Data Format (.edf)
                  </p>
                  
                  <label className="cursor-pointer">
                    <span className="btn-primary font-orbitron text-sm inline-flex items-center gap-2">
                      <UploadCloud className="w-4 h-4" />
                      {isApiConnected ? 'INITIATE ANALYSIS' : 'INITIATE SIMULATION'}
                    </span>
                    <input type="file" className="hidden" accept=".set,.edf" onChange={handleFileUpload} />
                  </label>
                </div>
             </div>
          </div>
        )}

        {/* ─── PROCESSING & COMPLETE ─── */}
        {(appState === 'ANALYZING' || appState === 'COMPLETE') && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8 animate-fade-in-up">
            <div className="h-[350px] animate-slide-in-left">
              <ConsoleBox logs={logs} />
            </div>
            <div className="h-[350px] animate-slide-in-right">
              <NarratorBox message={narratorMessage} logigramType={logigramType} />
            </div>
          </div>
        )}

        {/* ─── RESULTS ─── */}
        {appState === 'COMPLETE' && result && (
          <div className="mt-10">
            <ResultsDashboard result={result} />
            
            <div className="mt-14 text-center">
                <button 
                  onClick={resetAnalysis}
                  className="text-gray-500 hover:text-neon-cyan font-mono text-sm transition-colors duration-300 group"
                >
                  <span className="border-b border-gray-700 group-hover:border-neon-cyan/30 pb-0.5">
                    START NEW SESSION
                  </span>
                </button>
            </div>
          </div>
        )}

      </main>

      {/* Chatbot IA flottant */}
      <ChatBot
        apiUrl={apiUrl}
        isApiConnected={isApiConnected}
        analysisContext={result ? {
          status: result.status ?? undefined,
          stage: result.stage,
          confidence: result.confidence,
          features: result.features,
          report: result.report,
        } : null}
      />

      {/* Admin Dashboard (overlay — Ctrl+Shift+A) */}
      {showAdmin && (
        <AdminDashboard apiUrl={apiUrl} onClose={() => setShowAdmin(false)} />
      )}

      {/* Pricing Page (overlay) */}
      {showPricing && (
        <PricingPage apiUrl={apiUrl} onClose={() => setShowPricing(false)} />
      )}
    </div>
  );
}