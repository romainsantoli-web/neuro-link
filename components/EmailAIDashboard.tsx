import React, { useState, useEffect, useCallback } from 'react';
import {
  composeEmail, draftProspection, sendDraft, fetchInbox, queryMemory,
  listCampaignTemplates, startCampaign, getCampaignStatus, triggerCampaignCheck,
  type EmailDraft, type InboxMessage, type EmailMemoryRecord,
  type CampaignTemplate, type CampaignInstance,
} from '../services/emailAiApi';
import {
  Mail, Send, Brain, Inbox, Megaphone, Search, RefreshCw,
  AlertTriangle, X, Check, ChevronRight, Clock, User, FileText, Zap,
} from 'lucide-react';

interface EmailAIDashboardProps {
  apiUrl: string;
  token: string;
}

type Tab = 'compose' | 'prospection' | 'inbox' | 'campaigns' | 'memory';

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

  // Inbox state
  const [inboxMessages, setInboxMessages] = useState<InboxMessage[]>([]);
  const [selectedInbox, setSelectedInbox] = useState<InboxMessage | null>(null);

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
  const handleProspection = async () => {
    if (!targetName.trim()) return;
    setLoading(true);
    setError('');
    setProspectionDraft(null);
    try {
      const draft = await draftProspection(apiUrl, token, targetType, targetName, targetInfo);
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
    else if (activeTab === 'campaigns') loadCampaigns();
    else if (activeTab === 'memory') loadMemory();
  }, [activeTab, loadInbox, loadCampaigns, loadMemory]);

  const tabs: { id: Tab; label: string; icon: React.FC<any> }[] = [
    { id: 'compose', label: 'COMPOSER', icon: Mail },
    { id: 'prospection', label: 'PROSPECTION', icon: Zap },
    { id: 'inbox', label: 'INBOX', icon: Inbox },
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

            <button onClick={handleProspection} disabled={loading || !targetName.trim()}
              className="bg-gradient-to-r from-neon-purple to-pink-500 text-white font-orbitron font-bold
                         px-6 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed
                         flex items-center gap-2">
              {loading ? <RefreshCw size={16} className="animate-spin" /> : <Zap size={16} />}
              GÉNÉRER EMAIL PROSPECTION
            </button>
          </div>

          {prospectionDraft && (
            <DraftPreview draft={prospectionDraft} onSend={handleSend} loading={loading} sent={sendSuccess === prospectionDraft.id} />
          )}
        </div>
      )}

      {/* ── INBOX TAB ── */}
      {activeTab === 'inbox' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-orbitron text-sm text-neon-purple tracking-wider flex items-center gap-2">
              <Inbox size={16} /> INBOX GMAIL
            </h3>
            <button onClick={loadInbox} disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 text-gray-400 hover:text-neon-purple border border-gray-700 rounded-lg text-xs font-mono transition-colors">
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> ACTUALISER
            </button>
          </div>

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
