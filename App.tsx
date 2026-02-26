import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { StatusHUD } from './components/StatusHUD';
import { ConsoleBox } from './components/ConsoleBox';
import { NarratorBox, LogigramType } from './components/NarratorBox';
import { ResultsDashboard } from './components/ResultsDashboard';
import { ChatBot } from './components/ChatBot';
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

      <main className="max-w-7xl mx-auto px-4">
        
        {/* API LINK BAR (Auto-hides partially when connected or acts as status) */}
        <div className="mb-8 p-1 rounded-lg bg-gradient-to-r from-gray-800 to-gray-900 border border-gray-700 shadow-lg transition-all duration-500">
             <div className="flex flex-col md:flex-row gap-4 items-center bg-[#050505] p-3 rounded text-sm">
                <div className={`flex items-center gap-2 whitespace-nowrap px-2 transition-colors ${isApiConnected ? 'text-neon-green' : 'text-gray-500'}`}>
                    {isApiConnected ? <Wifi size={18} /> : <WifiOff size={18} />}
                    <span className="font-orbitron font-bold tracking-wider">
                      {isApiConnected ? 'INTEGRATED KERNEL' : 'KERNEL DISCONNECTED'}
                    </span>
                </div>
                
                <div className="flex-1 w-full flex items-center gap-2 border-l border-gray-800 pl-4 relative">
                    {isAutoConnecting && <span className="absolute right-0 text-xs text-neon-cyan animate-pulse mr-4">AUTO-DETECTING...</span>}
                    <ServerCog size={14} className="text-gray-500" />
                    <input 
                        type="text" 
                        placeholder={isApiConnected ? `Connected via ${apiUrl}` : "Enter Backend URL (default: /api)"}
                        className="w-full bg-transparent text-white font-mono placeholder-gray-600 outline-none disabled:opacity-50"
                        value={apiUrl}
                        onChange={(e) => setApiUrl(e.target.value)}
                        disabled={isAutoConnecting}
                    />
                </div>

                <button 
                    onClick={manualConnect}
                    disabled={!apiUrl || isAutoConnecting}
                    className={`px-6 py-2 rounded font-orbitron font-bold transition-all duration-300 ${isApiConnected 
                        ? 'bg-neon-green text-black shadow-[0_0_15px_rgba(63,185,80,0.4)] cursor-default' 
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'}`}
                >
                    {isApiConnected ? 'ONLINE' : 'CONNECT'}
                </button>
             </div>
        </div>

        {/* IDLE STATE: Dashboard visuals */}
        {appState === 'IDLE' && (
          <div className="animate-fade-in">
             <StatusHUD isConnected={isApiConnected} />
               
             {/* Waveform Visualization */}
             <div className="h-48 w-full mb-8 relative">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={IDLE_WAVE_DATA}>
                    <Line type="monotone" dataKey="alpha" stroke="#00ffea" strokeWidth={3} dot={false} animationDuration={3000} />
                    <Line type="monotone" dataKey="theta" stroke="#a855f7" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                    </LineChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <h3 className="text-gray-600 font-orbitron text-xl opacity-50 tracking-[8px]">WAITING FOR INPUT</h3>
                </div>
             </div>

             {/* Upload Zone */}
             <div className="mt-12 border-2 border-dashed border-gray-700 hover:border-neon-cyan rounded-2xl p-12 transition-all duration-300 group bg-slate-900/50 relative overflow-hidden">
                <div className="absolute inset-0 bg-neon-cyan/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                
                <div className="flex flex-col items-center justify-center text-center relative z-10">
                  <UploadCloud className="w-16 h-16 text-gray-500 group-hover:text-neon-cyan mb-4 transition-colors" />
                  <h3 className="text-2xl font-orbitron text-white mb-2">DRAG & DROP EEG FILE (.SET / .EDF)</h3>
                  <p className="text-gray-400 mb-6 font-mono text-sm">Supported formats: EEGLAB (.set), European Data Format (.edf)</p>
                  
                  <label className="cursor-pointer">
                    <span className="bg-gradient-to-r from-neon-cyan to-blue-500 text-black font-orbitron font-bold py-3 px-8 rounded hover:opacity-90 transition-opacity shadow-[0_0_15px_rgba(0,255,234,0.5)]">
                      {isApiConnected ? 'INITIATE ANALYSIS' : 'INITIATE SIMULATION'}
                    </span>
                    <input type="file" className="hidden" accept=".set,.edf" onChange={handleFileUpload} />
                  </label>
                </div>
             </div>
          </div>
        )}

        {/* PROCESSING & COMPLETE STATES */}
        {(appState === 'ANALYZING' || appState === 'COMPLETE') && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 animate-fade-in-up">
            <div className="h-[350px]">
              <ConsoleBox logs={logs} />
            </div>
            <div className="h-[350px]">
              <NarratorBox message={narratorMessage} logigramType={logigramType} />
            </div>
          </div>
        )}

        {/* RESULT DASHBOARD */}
        {appState === 'COMPLETE' && result && (
          <div className="mt-12">
            <ResultsDashboard result={result} />
            
            <div className="mt-12 text-center">
                <button 
                  onClick={resetAnalysis}
                  className="text-gray-500 hover:text-white underline font-mono text-sm"
                >
                  START NEW SESSION
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
    </div>
  );
}