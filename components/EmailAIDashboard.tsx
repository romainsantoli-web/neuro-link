import React, { useState, useEffect, useCallback } from 'react';
import {
  composeEmail, draftProspection, sendDraft, fetchInbox, queryMemory,
  listCampaignTemplates, startCampaign, getCampaignStatus, triggerCampaignCheck,
  processInbox, fetchDrafts, researchTarget,
  type EmailDraft, type InboxMessage, type EmailMemoryRecord,
  type CampaignTemplate, type CampaignInstance,
  type ProcessedEmail, type InboxProcessingReport, type DraftEmail,
  type ResearchReport,
} from '../services/emailAiApi';
import {
  Mail, Send, Brain, Inbox, Megaphone, Search, RefreshCw,
  AlertTriangle, X, Check, ChevronRight, Clock, User, FileText, Zap,
  Shield, Filter, MailCheck, ToggleLeft, ToggleRight, Eye, Rocket,
  Globe, ExternalLink, Copy,
} from 'lucide-react';

interface EmailAIDashboardProps {
  apiUrl: string;
  token: string;
}

type Tab = 'compose' | 'prospection' | 'research' | 'inbox' | 'drafts' | 'campaigns' | 'memory';

const TARGET_TYPES = [
  { value: 'chu', label: 'CHU / Hôpital', emoji: '🏥' },
  { value: 'ehpad', label: 'EHPAD', emoji: '🏠' },
  { value: 'neurologue', label: 'Neurologue', emoji: '🧠' },
  { value: 'investisseur', label: 'Investisseur / VC', emoji: '💰' },
  { value: 'partenaire_tech', label: 'Partenaire Tech', emoji: '🔧' },
];

export const EmailAIDashboard: React.FC<EmailAIDashboardProps> = ({ apiUrl, token }) => {
  const [activeTab, setActiveTab] = useState<Tab>('compose');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Compose state
  const [instruction, setInstruction] = useState('');
  const [composeTo, setComposeTo] = useState('');
  const [currentDraft, setCurrentDraft] = useState<EmailDraft | null>(null);
  const [sendSuccess, setSendSuccess] = useState('');

  // Prospection state
  const [targetType, setTargetType] = useState('chu');
  const [targetName, setTargetName] = useState('');
  const [targetInfo, setTargetInfo] = useState('');
  const [prospectionDraft, setProspectionDraft] = useState<EmailDraft | null>(null);
  const [researchReport, setResearchReport] = useState<ResearchReport | null>(null);
  const [researching, setResearching] = useState(false);

  // Standalone Research state
  const [researchName, setResearchName] = useState('');
  const [researchType, setResearchType] = useState('chu');
  const [researchKeywords, setResearchKeywords] = useState('');
  const [standaloneReport, setStandaloneReport] = useState<ResearchReport | null>(null);
  const [standaloneResearching, setStandaloneResearching] = useState(false);
  const [researchHistory, setResearchHistory] = useState<ResearchReport[]>([]);

  // Inbox state
  const [inboxMessages, setInboxMessages] = useState<InboxMessage[]>([]);
  const [selectedInbox, setSelectedInbox] = useState<InboxMessage | null>(null);
  const [processingReport, setProcessingReport] = useState<InboxProcessingReport | null>(null);
  const [autoReply, setAutoReply] = useState(true);
  const [autoSend, setAutoSend] = useState(false);
  const [processing, setProcessing] = useState(false);

  // Drafts state
  const [drafts, setDrafts] = useState<DraftEmail[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<DraftEmail | null>(null);
  const [sendingDraftId, setSendingDraftId] = useState('');

  // Campaign state
  const [templates, setTemplates] = useState<CampaignTemplate[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignInstance[]>([]);
  const [campTemplate, setCampTemplate] = useState('');
  const [campTo, setCampTo] = useState('');
  const [campName, setCampName] = useState('');
  const [campInfo, setCampInfo] = useState('');

  // Memory state
  const [memoryQuery, setMemoryQuery] = useState('');
  const [memoryResults, setMemoryResults] = useState<EmailMemoryRecord[]>([]);
  const [memoryCount, setMemoryCount] = useState(0);

  // ── Compose ──
  const handleCompose = async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    setError('');
    setCurrentDraft(null);
    setSendSuccess('');
    try {
      const draft = await composeEmail(apiUrl, token, instruction, composeTo || undefined);
      setCurrentDraft(draft);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Prospection ──
  const handleResearch = async () => {
    if (!targetName.trim()) return;
    setResearching(true);
    setError('');
    setResearchReport(null);
    try {
      const report = await researchTarget(apiUrl, token, targetName, targetType, targetInfo);
      setResearchReport(report);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setResearching(false);
    }
  };

  // ── Standalone Research ──
  const handleStandaloneResearch = async () => {
    if (!researchName.trim()) return;
    setStandaloneResearching(true);
    setError('');
    setStandaloneReport(null);
    try {
      const report = await researchTarget(apiUrl, token, researchName, researchType, researchKeywords);
      setStandaloneReport(report);
      setResearchHistory(prev => [report, ...prev].slice(0, 10));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setStandaloneResearching(false);
    }
  };

  const handleProspection = async () => {
    if (!targetName.trim()) return;
    setLoading(true);
    setError('');
    setProspectionDraft(null);
    try {
      const draft = await draftProspection(apiUrl, token, targetType, targetName, targetInfo, true);
      setProspectionDraft(draft);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Send draft ──
  const handleSend = async (draftId: string) => {
    setLoading(true);
    setError('');
    try {
      await sendDraft(apiUrl, token, draftId);
      setSendSuccess(draftId);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Inbox ──
  const loadInbox = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const msgs = await fetchInbox(apiUrl, token, 20);
      setInboxMessages(msgs);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token]);

  // ── Process Inbox (classify + auto-reply) ──
  const handleProcessInbox = async () => {
    setProcessing(true);
    setError('');
    setProcessingReport(null);
    try {
      const report = await processInbox(apiUrl, token, 20, autoReply, autoSend);
      setProcessingReport(report);
      // Refresh inbox list after processing
      const msgs = await fetchInbox(apiUrl, token, 20);
      setInboxMessages(msgs);
      // Refresh drafts if auto-reply created some
      if (report.auto_replies_drafted > 0) {
        const d = await fetchDrafts(apiUrl, token);
        setDrafts(d);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setProcessing(false);
    }
  };

  // ── Drafts ──
  const loadDrafts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const d = await fetchDrafts(apiUrl, token);
      setDrafts(d);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token]);

  const handleSendDraft = async (draftId: string) => {
    setSendingDraftId(draftId);
    setError('');
    try {
      await sendDraft(apiUrl, token, draftId);
      setSendSuccess(draftId);
      // Remove from local list
      setDrafts(prev => prev.filter(d => d.id !== draftId));
      setSelectedDraft(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSendingDraftId('');
    }
  };

  // ── Campaigns ──
  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [tpls, status] = await Promise.all([
        listCampaignTemplates(apiUrl, token),
        getCampaignStatus(apiUrl, token),
      ]);
      setTemplates(tpls);
      setCampaigns(status);
      if (tpls.length > 0 && !campTemplate) setCampTemplate(tpls[0].id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, campTemplate]);

  const handleStartCampaign = async () => {
    if (!campTemplate || !campTo.trim() || !campName.trim()) return;
    setLoading(true);
    setError('');
    try {
      await startCampaign(apiUrl, token, campTemplate, campTo, campName, campInfo);
      setCampTo('');
      setCampName('');
      setCampInfo('');
      loadCampaigns();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCampaignCheck = async () => {
    setLoading(true);
    setError('');
    try {
      await triggerCampaignCheck(apiUrl, token);
      loadCampaigns();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Memory ──
  const loadMemory = useCallback(async (q?: string) => {
    setLoading(true);
    setError('');
    try {
      const result = await queryMemory(apiUrl, token, q || '', 30);
      setMemoryResults(result.results);
      setMemoryCount(result.count);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token]);

  // Load data on tab change
  useEffect(() => {
    if (activeTab === 'inbox') loadInbox();
    else if (activeTab === 'drafts') loadDrafts();
    else if (activeTab === 'campaigns') loadCampaigns();
    else if (activeTab === 'memory') loadMemory();
  }, [activeTab, loadInbox, loadDrafts, loadCampaigns, loadMemory]);

  const tabs: { id: Tab; label: string; icon: React.FC<any> }[] = [
    { id: 'compose', label: 'COMPOSER', icon: Mail },
    { id: 'prospection', label: 'PROSPECTION', icon: Zap },
    { id: 'research', label: 'RECHERCHE WEB', icon: Globe },
    { id: 'inbox', label: 'INBOX', icon: Inbox },
    { id: 'drafts', label: 'BROUILLONS', icon: FileText },
    { id: 'campaigns', label: 'CAMPAGNES', icon: Megaphone },
    { id: 'memory', label: 'MÉMOIRE', icon: Brain },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 bg-red-900/30 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm">
          <AlertTriangle size={16} />
          {error}
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      {/* Success banner */}
      {sendSuccess && (
        <div className="flex items-center gap-2 bg-green-900/30 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg text-sm">
          <Check size={16} />
          Email envoyé avec succès ! (Draft: {sendSuccess})
          <button onClick={() => setSendSuccess('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      {/* Sub-tabs */}
      <div className="flex gap-1 bg-[#0a0a0a] p-1 rounded-lg border border-gray-800 overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded font-orbitron text-xs tracking-wider transition-all whitespace-nowrap
              ${activeTab === tab.id
                ? 'bg-neon-purple/10 text-neon-purple border border-neon-purple/30'
                : 'text-gray-500 hover:text-gray-300'}`}>
            <tab.icon size={14} /> {tab.label}
          </button>
        ))}
      </div>

      {/* ── COMPOSE TAB ── */}
      {activeTab === 'compose' && (
        <div className="space-y-4">
          <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 space-y-4">
            <h3 className="font-orbitron text-sm text-neon-purple tracking-wider flex items-center gap-2">
              <Mail size={16} /> COMPOSITION IA LIBRE
            </h3>
            <p className="text-xs text-gray-500">
              Décrivez l'email que l'IA doit rédiger. L'agent utilise sa mémoire complète pour contextualiser.
            </p>

            <div>
              <label className="block text-xs text-gray-500 font-mono mb-1">DESTINATAIRE (optionnel)</label>
              <input
                type="email"
                value={composeTo}
                onChange={e => setComposeTo(e.target.value)}
                placeholder="contact@exemple.fr"
                className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                           focus:border-neon-purple focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 font-mono mb-1">INSTRUCTION *</label>
              <textarea
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                placeholder="Ex: Rédige un email de relance pour le CHU de Lyon suite à notre premier contact la semaine dernière..."
                rows={4}
                className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                           focus:border-neon-purple focus:outline-none resize-none"
              />
            </div>

            <button onClick={handleCompose} disabled={loading || !instruction.trim()}
              className="bg-gradient-to-r from-neon-purple to-pink-500 text-white font-orbitron font-bold
                         px-6 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed
                         flex items-center gap-2">
              {loading ? <RefreshCw size={16} className="animate-spin" /> : <Brain size={16} />}
              GÉNÉRER AVEC L'IA
            </button>
          </div>

          {/* Draft preview */}
          {currentDraft && (
            <DraftPreview draft={currentDraft} onSend={handleSend} loading={loading} sent={sendSuccess === currentDraft.id} />
          )}
        </div>
      )}

      {/* ── PROSPECTION TAB ── */}
      {activeTab === 'prospection' && (
        <div className="space-y-4">
          <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 space-y-4">
            <h3 className="font-orbitron text-sm text-neon-purple tracking-wider flex items-center gap-2">
              <Zap size={16} /> EMAIL DE PROSPECTION
            </h3>

            <div>
              <label className="block text-xs text-gray-500 font-mono mb-2">TYPE DE CIBLE</label>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {TARGET_TYPES.map(t => (
                  <button key={t.value} onClick={() => setTargetType(t.value)}
                    className={`p-3 rounded-lg border text-left text-sm transition-all
                      ${targetType === t.value
                        ? 'border-neon-purple/50 bg-purple-900/20 text-neon-purple'
                        : 'border-gray-700 text-gray-500 hover:border-gray-500'}`}>
                    <span className="text-lg">{t.emoji}</span>
                    <div className="mt-1 text-xs font-mono">{t.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">NOM DE LA CIBLE *</label>
                <input
                  type="text"
                  value={targetName}
                  onChange={e => setTargetName(e.target.value)}
                  placeholder="CHU Montpellier — Dr. Martin"
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-purple focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">INFOS COMPLÉMENTAIRES</label>
                <input
                  type="text"
                  value={targetInfo}
                  onChange={e => setTargetInfo(e.target.value)}
                  placeholder="Service neurologie, 50 lits, intéressé par le dépistage précoce"
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-purple focus:outline-none"
                />
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={handleResearch} disabled={researching || !targetName.trim()}
                className="bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-orbitron font-bold
                           px-5 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed
                           flex items-center gap-2">
                {researching ? <RefreshCw size={16} className="animate-spin" /> : <Globe size={16} />}
                {researching ? 'RECHERCHE...' : 'RECHERCHER'}
              </button>
              <button onClick={handleProspection} disabled={loading || !targetName.trim()}
                className="bg-gradient-to-r from-neon-purple to-pink-500 text-white font-orbitron font-bold
                           px-5 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed
                           flex items-center gap-2">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Zap size={16} />}
                GÉNÉRER EMAIL
              </button>
            </div>
          </div>

          {/* ── Research Results ── */}
          {researchReport && (
            <div className="bg-[#0a0a0a] border border-cyan-800/40 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-orbitron text-xs text-cyan-300 tracking-wider flex items-center gap-2">
                  <Globe size={14} /> RECHERCHE WEB — {researchReport.company_name}
                </h4>
                <button onClick={() => setResearchReport(null)} className="text-gray-500 hover:text-gray-300">
                  <X size={14} />
                </button>
              </div>

              <div className="flex gap-3 text-xs font-mono text-gray-400">
                <span>{researchReport.search_results.length} résultats trouvés</span>
                <span>•</span>
                <span>{researchReport.scraped_pages.length} pages analysées</span>
              </div>

              {/* Search results */}
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {researchReport.search_results.map((sr, i) => (
                  <div key={i} className="bg-black/40 border border-gray-800 rounded-lg p-3">
                    <a href={sr.url} target="_blank" rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 text-sm font-medium flex items-center gap-1.5">
                      {sr.title || sr.url}
                      <ExternalLink size={10} className="flex-shrink-0" />
                    </a>
                    <div className="text-gray-600 text-xs mt-0.5 truncate">{sr.url}</div>
                    <div className="text-gray-400 text-xs mt-1">{sr.snippet}</div>
                  </div>
                ))}
              </div>

              {/* Scraped pages summary */}
              {researchReport.scraped_pages.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs text-gray-500 font-mono">PAGES ANALYSÉES :</div>
                  <div className="flex flex-wrap gap-2">
                    {researchReport.scraped_pages.map((sp, i) => (
                      <span key={i} className="text-xs bg-cyan-900/20 text-cyan-300 border border-cyan-800/30 px-2.5 py-1 rounded-full font-mono">
                        {sp.title || 'Page'} ({Math.round(sp.text_length / 1000)}k chars)
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {prospectionDraft && (
            <DraftPreview draft={prospectionDraft} onSend={handleSend} loading={loading} sent={sendSuccess === prospectionDraft.id} />
          )}
        </div>
      )}

      {/* ── RECHERCHE WEB TAB ── */}
      {activeTab === 'research' && (
        <div className="space-y-4">
          {/* Search form */}
          <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 space-y-4">
            <h3 className="font-orbitron text-sm text-cyan-300 tracking-wider flex items-center gap-2">
              <Globe size={16} /> RECHERCHE WEB INTELLIGENTE
            </h3>
            <p className="text-xs text-gray-500">
              Recherchez des informations sur une cible (hôpital, investisseur, partenaire…) avant de la démarcher.
              L'agent scanne le web et analyse les pages pertinentes.
            </p>

            <div>
              <label className="block text-xs text-gray-500 font-mono mb-2">TYPE DE CIBLE</label>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {TARGET_TYPES.map(t => (
                  <button key={t.value} onClick={() => setResearchType(t.value)}
                    className={`p-3 rounded-lg border text-left text-sm transition-all
                      ${researchType === t.value
                        ? 'border-cyan-500/50 bg-cyan-900/20 text-cyan-300'
                        : 'border-gray-700 text-gray-500 hover:border-gray-500'}`}>
                    <span className="text-lg">{t.emoji}</span>
                    <div className="mt-1 text-xs font-mono">{t.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">NOM DE LA CIBLE *</label>
                <input
                  type="text"
                  value={researchName}
                  onChange={e => setResearchName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleStandaloneResearch()}
                  placeholder="CHU Montpellier, Partech Partners, Dr. Martin..."
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-cyan-400 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">MOTS-CLÉS SUPPLÉMENTAIRES</label>
                <input
                  type="text"
                  value={researchKeywords}
                  onChange={e => setResearchKeywords(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleStandaloneResearch()}
                  placeholder="neurologie, Alzheimer, EEG, dépistage..."
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-cyan-400 focus:outline-none"
                />
              </div>
            </div>

            <button onClick={handleStandaloneResearch} disabled={standaloneResearching || !researchName.trim()}
              className="bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-orbitron font-bold
                         px-6 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed
                         flex items-center gap-2 shadow-lg shadow-cyan-900/30">
              {standaloneResearching ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
              {standaloneResearching ? 'RECHERCHE EN COURS...' : 'LANCER LA RECHERCHE'}
            </button>
          </div>

          {/* Research Results */}
          {standaloneReport && (
            <div className="space-y-4">
              {/* KPI bar */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold font-mono text-cyan-400">{standaloneReport.search_results.length}</div>
                  <div className="text-xs text-gray-500 mt-1">Résultats trouvés</div>
                </div>
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold font-mono text-blue-400">{standaloneReport.scraped_pages.length}</div>
                  <div className="text-xs text-gray-500 mt-1">Pages analysées</div>
                </div>
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold font-mono text-purple-400">
                    {Math.round(standaloneReport.scraped_pages.reduce((acc, p) => acc + p.text_length, 0) / 1000)}k
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Caractères extraits</div>
                </div>
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-4 text-center">
                  <div className="text-lg font-bold font-mono text-green-400 truncate">
                    {TARGET_TYPES.find(t => t.value === standaloneReport.company_type)?.emoji || '🔍'} {standaloneReport.company_type || 'N/A'}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Type de cible</div>
                </div>
              </div>

              {/* Main content: 2 columns */}
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                {/* Left: Search results */}
                <div className="lg:col-span-2 bg-[#0a0a0a] border border-gray-800 rounded-xl p-5 space-y-3">
                  <h4 className="font-orbitron text-xs text-cyan-300 tracking-wider flex items-center gap-2">
                    <Search size={14} /> RÉSULTATS DE RECHERCHE
                  </h4>
                  <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                    {standaloneReport.search_results.map((sr, i) => (
                      <div key={i} className="bg-black/40 border border-gray-800 rounded-lg p-3 hover:border-cyan-800/40 transition-colors">
                        <a href={sr.url} target="_blank" rel="noopener noreferrer"
                          className="text-cyan-400 hover:text-cyan-300 text-sm font-medium flex items-center gap-1.5">
                          <span className="truncate">{sr.title || sr.url}</span>
                          <ExternalLink size={10} className="flex-shrink-0" />
                        </a>
                        <div className="text-gray-600 text-xs mt-0.5 truncate">{sr.url}</div>
                        <div className="text-gray-400 text-xs mt-1 line-clamp-2">{sr.snippet}</div>
                      </div>
                    ))}
                  </div>

                  {/* Scraped pages badges */}
                  {standaloneReport.scraped_pages.length > 0 && (
                    <div className="border-t border-gray-800 pt-3 space-y-2">
                      <div className="text-xs text-gray-500 font-mono">PAGES SCRAPÉES :</div>
                      <div className="space-y-1.5">
                        {standaloneReport.scraped_pages.map((sp, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span className="w-2 h-2 rounded-full bg-cyan-400 flex-shrink-0" />
                            <a href={sp.url} target="_blank" rel="noopener noreferrer"
                              className="text-cyan-300/70 hover:text-cyan-300 truncate flex-1">
                              {sp.title || sp.url}
                            </a>
                            <span className="text-gray-600 font-mono flex-shrink-0">{Math.round(sp.text_length / 1000)}k</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Right: Research Summary (AI-compiled) */}
                <div className="lg:col-span-3 bg-[#0a0a0a] border border-cyan-800/30 rounded-xl p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-orbitron text-xs text-cyan-300 tracking-wider flex items-center gap-2">
                      <Brain size={14} /> SYNTHÈSE COMPLÈTE — {standaloneReport.company_name}
                    </h4>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(standaloneReport.research_summary);
                      }}
                      className="text-gray-500 hover:text-cyan-300 text-xs font-mono flex items-center gap-1 border border-gray-700 px-2 py-1 rounded hover:border-cyan-800/50 transition-colors">
                      <Copy size={10} /> Copier
                    </button>
                  </div>
                  <div className="max-h-[500px] overflow-y-auto pr-1">
                    <pre className="text-gray-300 text-xs font-mono whitespace-pre-wrap leading-relaxed">
                      {standaloneReport.research_summary}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Research History */}
          {researchHistory.length > 1 && (
            <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-5">
              <h4 className="font-orbitron text-xs text-gray-400 tracking-wider mb-3 flex items-center gap-2">
                <Clock size={14} /> HISTORIQUE DES RECHERCHES
              </h4>
              <div className="flex flex-wrap gap-2">
                {researchHistory.slice(1).map((report, i) => (
                  <button key={i} onClick={() => setStandaloneReport(report)}
                    className="text-xs bg-gray-800 text-gray-300 border border-gray-700 px-3 py-1.5 rounded-lg hover:border-cyan-800/50 hover:text-cyan-300 transition-colors font-mono flex items-center gap-1.5">
                    {TARGET_TYPES.find(t => t.value === report.company_type)?.emoji || '🔍'}
                    {report.company_name}
                    <span className="text-gray-600">({report.search_results.length})</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── INBOX TAB ── */}
      {activeTab === 'inbox' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h3 className="font-orbitron text-sm text-neon-purple tracking-wider flex items-center gap-2">
              <Inbox size={16} /> INBOX GMAIL
            </h3>
            <div className="flex items-center gap-2">
              {/* Auto-reply toggle */}
              <button onClick={() => setAutoReply(!autoReply)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono border rounded-lg transition-colors
                  ${autoReply ? 'text-green-400 border-green-800/50 bg-green-900/10' : 'text-gray-500 border-gray-700'}`}>
                {autoReply ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                Brouillons {autoReply ? 'ON' : 'OFF'}
              </button>
              {/* Auto-send toggle */}
              <button onClick={() => setAutoSend(!autoSend)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono border rounded-lg transition-colors
                  ${autoSend ? 'text-red-400 border-red-800/50 bg-red-900/10 animate-pulse' : 'text-gray-500 border-gray-700'}`}>
                {autoSend ? <Rocket size={14} /> : <ToggleLeft size={14} />}
                Envoi auto {autoSend ? 'ON' : 'OFF'}
              </button>
              {/* Process inbox button */}
              <button onClick={handleProcessInbox} disabled={processing || loading}
                className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-40 text-white rounded-lg text-xs font-mono font-bold transition-all shadow-lg shadow-purple-900/30">
                <Brain size={12} className={processing ? 'animate-pulse' : ''} />
                {processing ? 'TRAITEMENT...' : 'TRAITER INBOX'}
              </button>
              {/* Refresh button */}
              <button onClick={loadInbox} disabled={loading}
                className="flex items-center gap-2 px-3 py-1.5 text-gray-400 hover:text-neon-purple border border-gray-700 rounded-lg text-xs font-mono transition-colors">
                <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> ACTUALISER
              </button>
            </div>
          </div>

          {/* ── Processing Report ── */}
          {processingReport && (
            <div className="bg-[#0a0a0a] border border-purple-800/40 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-orbitron text-xs text-purple-300 tracking-wider flex items-center gap-2">
                  <Filter size={14} /> RAPPORT DE TRAITEMENT
                </h4>
                <button onClick={() => setProcessingReport(null)} className="text-gray-500 hover:text-gray-300">
                  <X size={14} />
                </button>
              </div>

              {/* KPI cards */}
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                {[
                  { label: 'Récupérés', value: processingReport.total_fetched, color: 'text-blue-400' },
                  { label: 'Déjà traités', value: processingReport.already_processed, color: 'text-gray-400' },
                  { label: 'Nouveaux', value: processingReport.newly_processed, color: 'text-cyan-400' },
                  { label: 'Brouillons', value: processingReport.auto_replies_drafted, color: 'text-green-400' },
                  { label: 'Envoyés', value: processingReport.auto_replies_sent ?? 0, color: 'text-pink-400' },
                  { label: 'Erreurs', value: processingReport.errors.length, color: processingReport.errors.length > 0 ? 'text-red-400' : 'text-gray-500' },
                ].map(kpi => (
                  <div key={kpi.label} className="bg-black/50 border border-gray-800 rounded-lg p-3 text-center">
                    <div className={`text-2xl font-bold font-mono ${kpi.color}`}>{kpi.value}</div>
                    <div className="text-xs text-gray-500 mt-1">{kpi.label}</div>
                  </div>
                ))}
              </div>

              {/* Classification breakdown */}
              {Object.keys(processingReport.classifications).length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs text-gray-400 font-mono">CLASSIFICATIONS :</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(processingReport.classifications).map(([cls, count]) => {
                      const colors: Record<string, string> = {
                        spam: 'bg-red-900/40 text-red-300 border-red-800/50',
                        publicite: 'bg-orange-900/30 text-orange-300 border-orange-800/40',
                        newsletter: 'bg-yellow-900/30 text-yellow-300 border-yellow-800/40',
                        notification_auto: 'bg-gray-800/60 text-gray-400 border-gray-700',
                        prospect_entrant: 'bg-green-900/40 text-green-300 border-green-800/50',
                        client: 'bg-blue-900/40 text-blue-300 border-blue-800/50',
                        partenaire: 'bg-purple-900/40 text-purple-300 border-purple-800/50',
                        investisseur: 'bg-amber-900/40 text-amber-300 border-amber-800/50',
                        candidature: 'bg-teal-900/40 text-teal-300 border-teal-800/50',
                        support: 'bg-cyan-900/40 text-cyan-300 border-cyan-800/50',
                        autre: 'bg-gray-800/50 text-gray-300 border-gray-700',
                      };
                      return (
                        <span key={cls} className={`px-2.5 py-1 rounded-full text-xs font-mono border ${colors[cls] || colors.autre}`}>
                          {cls.replace('_', ' ')} × {count}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Per-email results */}
              {processingReport.emails.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs text-gray-400 font-mono">DÉTAIL DES EMAILS :</div>
                  <div className="max-h-[300px] overflow-y-auto space-y-1.5 pr-1">
                    {processingReport.emails.map(em => {
                      const relevantColor = em.is_relevant ? 'border-l-green-500' : 'border-l-gray-700';
                      const urgencyIcon = em.urgency === 'haute' ? '🔴' : em.urgency === 'moyenne' ? '🟡' : '⚪';
                      const clsColors: Record<string, string> = {
                        spam: 'bg-red-900/40 text-red-300',
                        publicite: 'bg-orange-900/30 text-orange-300',
                        newsletter: 'bg-yellow-900/30 text-yellow-300',
                        prospect_entrant: 'bg-green-900/40 text-green-300',
                        client: 'bg-blue-900/40 text-blue-300',
                        partenaire: 'bg-purple-900/40 text-purple-300',
                        investisseur: 'bg-amber-900/40 text-amber-300',
                      };
                      return (
                        <div key={em.gmail_id} className={`bg-black/40 border border-gray-800 border-l-2 ${relevantColor} rounded-lg p-3 flex items-center gap-3`}>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className={`px-2 py-0.5 rounded text-xs font-mono ${clsColors[em.classification] || 'bg-gray-800 text-gray-400'}`}>
                                {em.classification.replace('_', ' ')}
                              </span>
                              <span className="text-xs">{urgencyIcon}</span>
                              {em.draft_id && (
                                <span className="flex items-center gap-1 text-xs text-green-400">
                                  <MailCheck size={10} /> Brouillon créé
                                </span>
                              )}
                            </div>
                            <div className="text-white text-xs font-medium truncate">{em.subject}</div>
                            <div className="text-gray-500 text-xs truncate">{em.from_addr}</div>
                            <div className="text-gray-600 text-xs mt-0.5 line-clamp-1">{em.summary}</div>
                          </div>
                          <div className="flex-shrink-0 text-xs text-gray-600 font-mono">
                            {em.action.replace('_', ' ')}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Errors */}
              {processingReport.errors.length > 0 && (
                <div className="space-y-1">
                  <div className="text-xs text-red-400 font-mono">ERREURS :</div>
                  {processingReport.errors.map((err, i) => (
                    <div key={i} className="text-xs text-red-300/70 bg-red-900/10 border border-red-900/30 rounded px-3 py-1.5 font-mono">
                      {err}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {inboxMessages.length === 0 && !loading && (
            <div className="text-center py-12 text-gray-500 font-mono text-sm">
              <Inbox size={40} className="mx-auto mb-3 opacity-30" />
              Aucun message ou connexion Gmail non configurée.
              <br />
              <span className="text-xs text-gray-600">Lancez <code className="bg-gray-800 px-1 rounded">python -m backend.gmail_reader auth</code> d'abord.</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Message list */}
            <div className="md:col-span-1 space-y-1 max-h-[600px] overflow-y-auto pr-1">
              {inboxMessages.map(msg => (
                <button key={msg.gmail_id}
                  onClick={() => setSelectedInbox(msg)}
                  className={`w-full text-left p-3 rounded-lg border transition-all text-sm
                    ${selectedInbox?.gmail_id === msg.gmail_id
                      ? 'border-neon-purple/50 bg-purple-900/10'
                      : 'border-gray-800 hover:border-gray-600 bg-[#0a0a0a]'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <User size={12} className="text-gray-500 flex-shrink-0" />
                    <span className="text-gray-300 truncate text-xs">{msg.from_addr}</span>
                  </div>
                  <div className="text-white font-medium truncate text-xs">{msg.subject || '(sans objet)'}</div>
                  <div className="text-gray-600 text-xs mt-1 truncate">{msg.snippet}</div>
                  <div className="text-gray-600 text-xs mt-1 flex items-center gap-1">
                    <Clock size={10} /> {new Date(msg.date).toLocaleDateString('fr-FR')}
                  </div>
                </button>
              ))}
            </div>

            {/* Message detail */}
            <div className="md:col-span-2">
              {selectedInbox ? (
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-white font-medium">{selectedInbox.subject || '(sans objet)'}</h4>
                      <div className="text-gray-400 text-xs mt-1">De: {selectedInbox.from_addr}</div>
                      <div className="text-gray-500 text-xs">Le: {new Date(selectedInbox.date).toLocaleString('fr-FR')}</div>
                    </div>
                    <div className="flex gap-1">
                      {selectedInbox.labels?.map(l => (
                        <span key={l} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{l}</span>
                      ))}
                    </div>
                  </div>
                  <div className="border-t border-gray-800 pt-4">
                    <pre className="text-gray-300 text-sm font-mono whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
                      {selectedInbox.body}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-12 text-center text-gray-600 text-sm">
                  <Mail size={40} className="mx-auto mb-3 opacity-20" />
                  Sélectionnez un message pour le lire
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── DRAFTS TAB ── */}
      {activeTab === 'drafts' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-orbitron text-sm text-neon-purple tracking-wider flex items-center gap-2">
              <FileText size={16} /> BROUILLONS ({drafts.length})
            </h3>
            <button onClick={loadDrafts} disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 text-gray-400 hover:text-neon-purple border border-gray-700 rounded-lg text-xs font-mono transition-colors">
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> ACTUALISER
            </button>
          </div>

          {drafts.length === 0 && !loading && (
            <div className="text-center py-12 text-gray-500 font-mono text-sm">
              <FileText size={40} className="mx-auto mb-3 opacity-30" />
              Aucun brouillon en attente.
              <br />
              <span className="text-xs text-gray-600">Traitez votre inbox pour générer des brouillons automatiques.</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Drafts list */}
            <div className="md:col-span-1 space-y-1 max-h-[600px] overflow-y-auto pr-1">
              {drafts.map(draft => (
                <button key={draft.id}
                  onClick={() => setSelectedDraft(draft)}
                  className={`w-full text-left p-3 rounded-lg border transition-all text-sm
                    ${selectedDraft?.id === draft.id
                      ? 'border-neon-purple/50 bg-purple-900/10'
                      : 'border-gray-800 hover:border-gray-600 bg-[#0a0a0a]'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    {draft.auto_reply && (
                      <span className="text-xs bg-green-900/40 text-green-300 px-1.5 py-0.5 rounded font-mono">AUTO</span>
                    )}
                    <span className="text-gray-300 truncate text-xs">{draft.to}</span>
                  </div>
                  <div className="text-white font-medium truncate text-xs">{draft.subject || '(sans objet)'}</div>
                  <div className="text-gray-600 text-xs mt-1 flex items-center gap-1">
                    <Clock size={10} /> {new Date(draft.timestamp).toLocaleString('fr-FR')}
                  </div>
                </button>
              ))}
            </div>

            {/* Draft detail + send */}
            <div className="md:col-span-2">
              {selectedDraft ? (
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-white font-medium">{selectedDraft.subject || '(sans objet)'}</h4>
                      <div className="text-gray-400 text-xs mt-1">À: {selectedDraft.to}</div>
                      <div className="text-gray-500 text-xs">Créé: {new Date(selectedDraft.timestamp).toLocaleString('fr-FR')}</div>
                      <div className="flex gap-2 mt-2">
                        {selectedDraft.auto_reply && (
                          <span className="text-xs bg-green-900/40 text-green-300 border border-green-800/40 px-2 py-0.5 rounded-full font-mono">
                            Auto-réponse IA
                          </span>
                        )}
                        {selectedDraft.target_type && (
                          <span className="text-xs bg-purple-900/30 text-purple-300 border border-purple-800/40 px-2 py-0.5 rounded-full font-mono">
                            {selectedDraft.target_type}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleSendDraft(selectedDraft.id)}
                      disabled={sendingDraftId === selectedDraft.id || sendSuccess === selectedDraft.id}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-mono font-bold transition-all
                        ${sendSuccess === selectedDraft.id
                          ? 'bg-green-900/30 text-green-400 border border-green-800/40'
                          : 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white shadow-lg shadow-green-900/30'
                        } disabled:opacity-50`}>
                      {sendSuccess === selectedDraft.id ? (
                        <><Check size={14} /> ENVOYÉ</>
                      ) : sendingDraftId === selectedDraft.id ? (
                        <><RefreshCw size={14} className="animate-spin" /> ENVOI...</>
                      ) : (
                        <><Send size={14} /> ENVOYER</>
                      )}
                    </button>
                  </div>
                  <div className="border-t border-gray-800 pt-4">
                    <pre className="text-gray-300 text-sm font-mono whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
                      {selectedDraft.body}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-12 text-center text-gray-600 text-sm">
                  <FileText size={40} className="mx-auto mb-3 opacity-20" />
                  Sélectionnez un brouillon pour le lire et l'envoyer
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── CAMPAIGNS TAB ── */}
      {activeTab === 'campaigns' && (
        <div className="space-y-6">
          {/* Start new campaign */}
          <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 space-y-4">
            <h3 className="font-orbitron text-sm text-neon-purple tracking-wider flex items-center gap-2">
              <Megaphone size={16} /> LANCER UNE CAMPAGNE
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">TEMPLATE</label>
                <select value={campTemplate} onChange={e => setCampTemplate(e.target.value)}
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-purple focus:outline-none">
                  {templates.map(t => (
                    <option key={t.id} value={t.id} className="bg-[#0a0a0a]">
                      {t.name} ({t.steps} étapes)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">EMAIL DESTINATAIRE *</label>
                <input type="email" value={campTo} onChange={e => setCampTo(e.target.value)}
                  placeholder="dr.martin@chu-montpellier.fr"
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-purple focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">NOM DE LA CIBLE *</label>
                <input type="text" value={campName} onChange={e => setCampName(e.target.value)}
                  placeholder="CHU Montpellier — Dr. Martin"
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-purple focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">INFOS COMPLÉMENTAIRES</label>
                <input type="text" value={campInfo} onChange={e => setCampInfo(e.target.value)}
                  placeholder="Service neurologie, intéressé par le dépistage"
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-purple focus:outline-none" />
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={handleStartCampaign}
                disabled={loading || !campTo.trim() || !campName.trim() || !campTemplate}
                className="bg-gradient-to-r from-neon-purple to-pink-500 text-white font-orbitron font-bold
                           px-6 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed
                           flex items-center gap-2">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Megaphone size={16} />}
                LANCER
              </button>
              <button onClick={handleCampaignCheck} disabled={loading}
                className="px-4 py-3 text-gray-400 hover:text-neon-purple border border-gray-700 rounded-lg font-mono text-xs transition-colors
                           flex items-center gap-2">
                <Clock size={14} /> VÉRIFIER ÉTAPES DUES
              </button>
            </div>
          </div>

          {/* Active campaigns */}
          <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-orbitron text-sm text-gray-400 tracking-wider">CAMPAGNES EN COURS</h3>
              <button onClick={loadCampaigns} disabled={loading}
                className="text-gray-500 hover:text-neon-purple transition-colors">
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>

            {campaigns.length === 0 ? (
              <div className="text-center py-8 text-gray-600 text-sm font-mono">
                Aucune campagne en cours
              </div>
            ) : (
              <div className="space-y-3">
                {campaigns.map(c => (
                  <div key={c.instance_id}
                    className="border border-gray-800 rounded-lg p-4 hover:border-gray-600 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-mono
                          ${c.status === 'active'
                            ? 'bg-green-900/30 text-green-400 border border-green-700/30'
                            : 'bg-gray-800 text-gray-400 border border-gray-700'}`}>
                          {c.status.toUpperCase()}
                        </span>
                        <span className="text-white font-medium text-sm">{c.campaign_name}</span>
                      </div>
                      <span className="text-gray-500 text-xs font-mono">
                        {c.current_step}/{c.total_steps} étapes
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1"><User size={10} /> {c.target_name}</span>
                      <span className="flex items-center gap-1"><Mail size={10} /> {c.to}</span>
                      <span className="flex items-center gap-1"><Clock size={10} /> {new Date(c.started_at).toLocaleDateString('fr-FR')}</span>
                    </div>
                    {/* Progress bar */}
                    <div className="mt-3 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-neon-purple to-pink-500 rounded-full transition-all"
                        style={{ width: `${c.total_steps > 0 ? (c.current_step / c.total_steps) * 100 : 0}%` }} />
                    </div>
                    {/* Steps */}
                    {c.steps_completed?.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {c.steps_completed.map((s, i) => (
                          <span key={i} className="text-xs bg-purple-900/20 text-purple-300 px-2 py-0.5 rounded border border-purple-800/30">
                            {s.type}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── MEMORY TAB ── */}
      {activeTab === 'memory' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                value={memoryQuery}
                onChange={e => setMemoryQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && loadMemory(memoryQuery)}
                placeholder="Recherche sémantique dans la mémoire email..."
                className="w-full bg-[#050505] border border-gray-700 rounded-lg pl-10 pr-4 py-2.5 text-white font-mono text-sm
                           focus:border-neon-purple focus:outline-none"
              />
            </div>
            <button onClick={() => loadMemory(memoryQuery)} disabled={loading}
              className="px-4 py-2.5 bg-neon-purple/10 text-neon-purple border border-neon-purple/30 rounded-lg font-mono text-xs
                         hover:bg-neon-purple/20 transition-colors flex items-center gap-2">
              <Search size={14} /> CHERCHER
            </button>
          </div>

          <div className="text-xs text-gray-500 font-mono">{memoryCount} résultat(s)</div>

          <div className="space-y-2">
            {memoryResults.map(rec => (
              <div key={rec.id} className="bg-[#0a0a0a] border border-gray-800 rounded-lg p-4 hover:border-gray-600 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-mono
                      ${rec.type === 'sent' ? 'bg-blue-900/30 text-blue-300 border border-blue-700/30'
                        : rec.type === 'received' ? 'bg-green-900/30 text-green-300 border border-green-700/30'
                        : rec.type === 'draft' ? 'bg-yellow-900/30 text-yellow-300 border border-yellow-700/30'
                        : 'bg-purple-900/30 text-purple-300 border border-purple-700/30'}`}>
                      {rec.type.toUpperCase()}
                    </span>
                    <span className="text-white font-medium text-sm truncate">{rec.subject}</span>
                  </div>
                  <span className="text-gray-600 text-xs font-mono flex-shrink-0">
                    {new Date(rec.timestamp).toLocaleDateString('fr-FR')}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500 mb-2">
                  {rec.to && <span>→ {rec.to}</span>}
                  {rec.from_addr && <span>← {rec.from_addr}</span>}
                  {rec.target_type && <span className="bg-gray-800 px-1.5 py-0.5 rounded">{rec.target_type}</span>}
                  {rec.campaign_id && <span className="bg-gray-800 px-1.5 py-0.5 rounded">campagne</span>}
                </div>
                <p className="text-gray-400 text-xs line-clamp-2">{rec.body}</p>
              </div>
            ))}
            {memoryResults.length === 0 && !loading && (
              <div className="text-center py-12 text-gray-600 text-sm font-mono">
                <Brain size={40} className="mx-auto mb-3 opacity-20" />
                {memoryQuery ? 'Aucun résultat pour cette recherche' : 'Mémoire vide — les emails envoyés et reçus apparaîtront ici'}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ── Draft Preview sub-component ──
const DraftPreview: React.FC<{
  draft: EmailDraft;
  onSend: (id: string) => void;
  loading: boolean;
  sent: boolean;
}> = ({ draft, onSend, loading, sent }) => (
  <div className="bg-[#0a0a0a] border border-neon-purple/20 rounded-xl p-6 space-y-4">
    <div className="flex items-center justify-between">
      <h4 className="font-orbitron text-sm text-neon-purple tracking-wider flex items-center gap-2">
        <FileText size={16} /> BROUILLON GÉNÉRÉ
      </h4>
      <span className="text-xs font-mono text-gray-600">{draft.id}</span>
    </div>

    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-gray-500 font-mono text-xs w-12">À:</span>
        <span className="text-white">{draft.to || '—'}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-gray-500 font-mono text-xs w-12">Objet:</span>
        <span className="text-white font-medium">{draft.subject}</span>
      </div>
    </div>

    <div className="border-t border-gray-800 pt-4">
      <pre className="text-gray-300 text-sm font-mono whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
        {draft.body}
      </pre>
    </div>

    <div className="flex items-center gap-3 pt-2">
      {sent ? (
        <div className="flex items-center gap-2 text-green-400 text-sm font-mono">
          <Check size={16} /> Envoyé !
        </div>
      ) : (
        <button onClick={() => onSend(draft.id)} disabled={loading}
          className="bg-gradient-to-r from-green-600 to-emerald-500 text-white font-orbitron font-bold
                     px-6 py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed
                     flex items-center gap-2 text-sm">
          <Send size={14} /> ENVOYER
        </button>
      )}
      <span className="text-xs text-gray-600 font-mono">
        {draft.target_type && `[${draft.target_type}]`} {draft.timestamp && new Date(draft.timestamp).toLocaleString('fr-FR')}
      </span>
    </div>
  </div>
);
