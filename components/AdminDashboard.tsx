import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchPlans, fetchKeys, createKey, updateKey, revokeKey, deleteKey,
  fetchUsageSummary,
  type ApiKeyInfo, type PlanInfo, type UsageSummary, type CreateKeyResult,
} from '../services/adminApi';
import { EmailAIDashboard } from './EmailAIDashboard';
import {
  Shield, Key, Users, BarChart3, Plus, Trash2, Ban, RefreshCw,
  ChevronUp, Copy, Check, AlertTriangle, X, Eye, EyeOff, Mail
} from 'lucide-react';

interface AdminDashboardProps {
  apiUrl: string;
  onClose: () => void;
}

type Tab = 'overview' | 'keys' | 'create' | 'email-ai';

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ apiUrl, onClose }) => {
  // Auth
  const [token, setToken] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState('');
  const [showToken, setShowToken] = useState(false);

  // Data
  const [plans, setPlans] = useState<Record<string, PlanInfo>>({});
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [showInactive, setShowInactive] = useState(false);

  // Create form
  const [newOwner, setNewOwner] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPlan, setNewPlan] = useState('free');
  const [createdKey, setCreatedKey] = useState<CreateKeyResult | null>(null);
  const [copied, setCopied] = useState(false);

  // UI
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    setError('');
    try {
      const [p, k, s] = await Promise.all([
        fetchPlans(apiUrl, token),
        fetchKeys(apiUrl, token, showInactive),
        fetchUsageSummary(apiUrl, token),
      ]);
      setPlans(p);
      setKeys(k);
      setSummary(s);
    } catch (e: any) {
      setError(e.message || 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, isAuthenticated, showInactive]);

  useEffect(() => {
    if (isAuthenticated) loadData();
  }, [isAuthenticated, loadData]);

  const handleLogin = async () => {
    setAuthError('');
    try {
      await fetchPlans(apiUrl, token);
      setIsAuthenticated(true);
    } catch {
      setAuthError('Token invalide ou API inaccessible');
    }
  };

  const handleCreate = async () => {
    if (!newOwner.trim()) return;
    setError('');
    try {
      const result = await createKey(apiUrl, token, newOwner.trim(), newEmail.trim(), newPlan);
      setCreatedKey(result);
      setNewOwner('');
      setNewEmail('');
      setNewPlan('free');
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRevoke = async (keyId: number) => {
    try {
      await revokeKey(apiUrl, token, keyId);
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (keyId: number) => {
    if (!confirm('Supprimer définitivement cette clé et ses données ?')) return;
    try {
      await deleteKey(apiUrl, token, keyId);
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handlePlanChange = async (keyId: number, plan: string) => {
    try {
      await updateKey(apiUrl, token, keyId, { plan });
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleReactivate = async (keyId: number) => {
    try {
      await updateKey(apiUrl, token, keyId, { active: true });
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const planColor = (plan: string) => {
    switch (plan) {
      case 'free': return 'text-gray-400';
      case 'starter': return 'text-neon-cyan';
      case 'clinique': return 'text-neon-purple';
      case 'institution': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const planBadge = (plan: string) => {
    const colors: Record<string, string> = {
      free: 'bg-gray-700 text-gray-300',
      starter: 'bg-cyan-900/50 text-neon-cyan border border-neon-cyan/30',
      clinique: 'bg-purple-900/50 text-neon-purple border border-neon-purple/30',
      institution: 'bg-yellow-900/50 text-yellow-400 border border-yellow-500/30',
    };
    return colors[plan] || colors.free;
  };

  // ── Login screen ──
  if (!isAuthenticated) {
    return (
      <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
        <div className="bg-[#0a0a0a] border border-neon-cyan/20 rounded-xl p-8 max-w-md w-full shadow-2xl shadow-neon-cyan/5">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-neon-cyan" />
              <h2 className="font-orbitron text-xl text-white tracking-wider">ADMIN ACCESS</h2>
            </div>
            <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
              <X size={20} />
            </button>
          </div>

          <p className="text-gray-400 text-sm mb-6 font-mono">
            Entrez le token d'administration (ADMIN_TOKEN env var)
          </p>

          <div className="relative mb-4">
            <input
              type={showToken ? 'text' : 'password'}
              value={token}
              onChange={e => setToken(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
              placeholder="admin-token..."
              className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-3 text-white font-mono
                         focus:border-neon-cyan focus:outline-none pr-10"
            />
            <button
              onClick={() => setShowToken(!showToken)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
            >
              {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {authError && (
            <div className="flex items-center gap-2 text-neon-red text-sm mb-4">
              <AlertTriangle size={14} /> {authError}
            </div>
          )}

          <button
            onClick={handleLogin}
            disabled={!token.trim()}
            className="w-full bg-gradient-to-r from-neon-cyan to-blue-500 text-black font-orbitron font-bold
                       py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
          >
            AUTHENTICATE
          </button>
        </div>
      </div>
    );
  }

  // ── Main dashboard ──
  return (
    <div className="fixed inset-0 bg-black/95 backdrop-blur-md z-50 overflow-auto">
      {/* Header */}
      <div className="sticky top-0 bg-[#050505]/95 backdrop-blur border-b border-neon-cyan/20 px-6 py-4 z-10">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Shield className="w-6 h-6 text-neon-cyan" />
            <h1 className="font-orbitron text-xl text-white tracking-wider">ADMIN DASHBOARD</h1>
            <span className="text-xs font-mono text-gray-500 bg-gray-800 px-2 py-1 rounded">SaaS API Management</span>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={loadData} disabled={loading}
              className="p-2 text-gray-400 hover:text-neon-cyan transition-colors disabled:animate-spin">
              <RefreshCw size={18} />
            </button>
            <button onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white font-mono text-sm border border-gray-700 rounded hover:border-gray-500 transition-colors">
              FERMER
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Error banner */}
        {error && (
          <div className="mb-4 flex items-center gap-2 bg-red-900/30 border border-neon-red/30 text-neon-red px-4 py-3 rounded-lg text-sm">
            <AlertTriangle size={16} />
            {error}
            <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-[#0a0a0a] p-1 rounded-lg border border-gray-800 w-fit">
          {([
            { id: 'overview' as Tab, label: 'VUE D\'ENSEMBLE', icon: BarChart3 },
            { id: 'keys' as Tab, label: 'CLÉS API', icon: Key },
            { id: 'create' as Tab, label: 'NOUVELLE CLÉ', icon: Plus },
            { id: 'email-ai' as Tab, label: 'EMAIL AI', icon: Mail },
          ]).map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded font-orbitron text-xs tracking-wider transition-all
                ${activeTab === tab.id
                  ? 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30'
                  : 'text-gray-500 hover:text-gray-300'}`}>
              <tab.icon size={14} /> {tab.label}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === 'overview' && summary && (
          <div className="space-y-6 animate-fade-in">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <KpiCard label="CLÉS ACTIVES" value={String(keys.filter(k => k.active).length)} icon={Key} color="cyan" />
              <KpiCard label="ANALYSES CE MOIS" value={String(summary.total_analyses)} icon={BarChart3} color="green" />
              <KpiCard label="REQUÊTES CE MOIS" value={String(summary.total_requests)} icon={ChevronUp} color="purple" />
              <KpiCard label="UTILISATEURS ACTIFS" value={String(summary.active_keys)} icon={Users} color="yellow" />
            </div>

            {/* Plans summary */}
            <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6">
              <h3 className="font-orbitron text-sm text-gray-400 tracking-wider mb-4">PLANS TARIFAIRES</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {(Object.entries(plans) as [string, PlanInfo][]).map(([key, plan]) => (
                  <div key={key} className={`border rounded-lg p-4 ${planBadge(key)}`}>
                    <div className="font-orbitron font-bold text-lg">{plan.label}</div>
                    <div className="text-sm mt-2 opacity-80">
                      {plan.max_analyses_per_month === -1 ? 'Illimité' : `${plan.max_analyses_per_month} analyses/mois`}
                    </div>
                    <div className="text-sm opacity-60">{plan.max_requests_per_minute} req/min</div>
                    <div className="font-bold mt-2 text-lg">
                      {plan.price_eur === 0 ? 'Gratuit' : `€${plan.price_eur}/mois`}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top users */}
            {summary.top_users.length > 0 && (
              <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6">
                <h3 className="font-orbitron text-sm text-gray-400 tracking-wider mb-4">TOP UTILISATEURS — {summary.month}</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-gray-500 border-b border-gray-800 font-mono text-xs">
                        <th className="text-left py-2 px-3">#</th>
                        <th className="text-left py-2 px-3">CLIENT</th>
                        <th className="text-left py-2 px-3">PLAN</th>
                        <th className="text-right py-2 px-3">ANALYSES</th>
                        <th className="text-right py-2 px-3">REQUÊTES</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.top_users.map((u, i) => (
                        <tr key={u.key_id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                          <td className="py-2 px-3 text-gray-500">{i + 1}</td>
                          <td className="py-2 px-3 text-white">{u.owner}</td>
                          <td className="py-2 px-3"><span className={`px-2 py-0.5 rounded text-xs ${planBadge(u.plan)}`}>{u.plan}</span></td>
                          <td className="py-2 px-3 text-right text-neon-green font-mono">{u.analyses_count}</td>
                          <td className="py-2 px-3 text-right text-gray-400 font-mono">{u.requests_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── KEYS TAB ── */}
        {activeTab === 'keys' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showInactive}
                  onChange={e => setShowInactive(e.target.checked)}
                  className="accent-neon-cyan"
                />
                Afficher les clés révoquées
              </label>
              <span className="text-xs text-gray-500 font-mono">{keys.length} clé(s)</span>
            </div>

            <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700 font-mono text-xs bg-[#050505]">
                      <th className="text-left py-3 px-4">ID</th>
                      <th className="text-left py-3 px-4">PRÉFIXE</th>
                      <th className="text-left py-3 px-4">CLIENT</th>
                      <th className="text-left py-3 px-4">EMAIL</th>
                      <th className="text-left py-3 px-4">PLAN</th>
                      <th className="text-right py-3 px-4">ANALYSES</th>
                      <th className="text-right py-3 px-4">QUOTA</th>
                      <th className="text-left py-3 px-4">STATUT</th>
                      <th className="text-right py-3 px-4">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {keys.map(k => {
                      const limit = k.plan_info?.max_analyses_per_month ?? 0;
                      const used = k.usage_this_month?.analyses ?? 0;
                      const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : (limit === -1 ? 0 : 0);
                      const quotaText = limit === -1 ? '∞' : `${used}/${limit}`;
                      const isActive = k.active === 1;

                      return (
                        <tr key={k.id} className={`border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors
                          ${!isActive ? 'opacity-50' : ''}`}>
                          <td className="py-3 px-4 text-gray-500 font-mono">{k.id}</td>
                          <td className="py-3 px-4 font-mono text-xs text-gray-300">{k.key_prefix}</td>
                          <td className="py-3 px-4 text-white font-medium">{k.owner}</td>
                          <td className="py-3 px-4 text-gray-400 text-xs">{k.email || '—'}</td>
                          <td className="py-3 px-4">
                            {isActive ? (
                              <select
                                value={k.plan}
                                onChange={e => handlePlanChange(k.id, e.target.value)}
                                className={`bg-transparent border border-gray-700 rounded px-2 py-1 text-xs font-mono cursor-pointer
                                  focus:border-neon-cyan focus:outline-none ${planColor(k.plan)}`}>
                                {Object.keys(plans).map(p => (
                                  <option key={p} value={p} className="bg-[#0a0a0a]">{p}</option>
                                ))}
                              </select>
                            ) : (
                              <span className={`text-xs ${planColor(k.plan)}`}>{k.plan}</span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-neon-green">{used}</td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all ${pct > 80 ? 'bg-neon-red' : pct > 50 ? 'bg-yellow-500' : 'bg-neon-green'}`}
                                  style={{ width: limit === -1 ? '0%' : `${pct}%` }} />
                              </div>
                              <span className="text-xs font-mono text-gray-400 w-12 text-right">{quotaText}</span>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-0.5 rounded text-xs font-mono
                              ${isActive ? 'bg-green-900/30 text-neon-green border border-green-700/30' : 'bg-red-900/30 text-neon-red border border-red-700/30'}`}>
                              {isActive ? 'ACTIF' : 'RÉVOQUÉ'}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              {isActive ? (
                                <button onClick={() => handleRevoke(k.id)} title="Révoquer"
                                  className="p-1.5 text-gray-500 hover:text-yellow-400 transition-colors">
                                  <Ban size={14} />
                                </button>
                              ) : (
                                <button onClick={() => handleReactivate(k.id)} title="Réactiver"
                                  className="p-1.5 text-gray-500 hover:text-neon-green transition-colors">
                                  <RefreshCw size={14} />
                                </button>
                              )}
                              <button onClick={() => handleDelete(k.id)} title="Supprimer"
                                className="p-1.5 text-gray-500 hover:text-neon-red transition-colors">
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {keys.length === 0 && (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-gray-500 font-mono text-sm">
                          Aucune clé API — créez-en une depuis l'onglet "NOUVELLE CLÉ"
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── CREATE TAB ── */}
        {activeTab === 'create' && (
          <div className="max-w-lg space-y-6 animate-fade-in">
            <div className="bg-[#0a0a0a] border border-gray-800 rounded-xl p-6 space-y-4">
              <h3 className="font-orbitron text-sm text-gray-400 tracking-wider mb-2">GÉNÉRER UNE CLÉ API</h3>

              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">NOM DU CLIENT *</label>
                <input
                  type="text"
                  value={newOwner}
                  onChange={e => setNewOwner(e.target.value)}
                  placeholder="Dr. Martin — Clinique Neurosciences"
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-cyan focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">EMAIL</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={e => setNewEmail(e.target.value)}
                  placeholder="contact@clinique.fr"
                  className="w-full bg-[#050505] border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono text-sm
                             focus:border-neon-cyan focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-500 font-mono mb-1">PLAN</label>
                <div className="grid grid-cols-2 gap-2">
                  {(Object.entries(plans) as [string, PlanInfo][]).map(([key, plan]) => (
                    <button key={key} onClick={() => setNewPlan(key)}
                      className={`p-3 rounded-lg border text-left transition-all text-sm
                        ${newPlan === key
                          ? `${planBadge(key)} ring-1 ring-offset-1 ring-offset-black`
                          : 'border-gray-700 text-gray-500 hover:border-gray-500'}`}>
                      <div className="font-bold">{plan.label}</div>
                      <div className="text-xs opacity-70 mt-1">
                        {plan.price_eur === 0 ? 'Gratuit' : `€${plan.price_eur}/mois`}
                        {' — '}
                        {plan.max_analyses_per_month === -1 ? '∞' : plan.max_analyses_per_month} analyses
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <button onClick={handleCreate} disabled={!newOwner.trim()}
                className="w-full bg-gradient-to-r from-neon-cyan to-blue-500 text-black font-orbitron font-bold
                           py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed mt-2">
                <Plus size={16} className="inline mr-2" /> GÉNÉRER LA CLÉ
              </button>
            </div>

            {/* Created key display */}
            {createdKey && (
              <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-6 space-y-3">
                <div className="flex items-center gap-2 text-neon-green font-orbitron text-sm">
                  <Check size={16} /> CLÉ GÉNÉRÉE AVEC SUCCÈS
                </div>
                <p className="text-xs text-gray-400">
                  Copiez cette clé maintenant — elle ne sera plus affichée.
                </p>
                <div className="flex items-center gap-2 bg-[#050505] rounded-lg px-4 py-3">
                  <code className="flex-1 text-neon-cyan font-mono text-sm break-all">
                    {createdKey.raw_key}
                  </code>
                  <button onClick={() => copyToClipboard(createdKey.raw_key)}
                    className="p-2 text-gray-400 hover:text-white transition-colors flex-shrink-0">
                    {copied ? <Check size={16} className="text-neon-green" /> : <Copy size={16} />}
                  </button>
                </div>
                <div className="text-xs text-gray-500 font-mono space-y-1">
                  <div>Client: {createdKey.owner}</div>
                  <div>Plan: {createdKey.plan}</div>
                  <div>ID: {createdKey.id}</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── EMAIL AI TAB ── */}
        {activeTab === 'email-ai' && (
          <EmailAIDashboard apiUrl={apiUrl} token={token} />
        )}
      </div>
    </div>
  );
};

// ── KPI Card sub-component ──
const KpiCard: React.FC<{ label: string; value: string; icon: React.FC<any>; color: string }> = ({
  label, value, icon: Icon, color
}) => {
  const colorMap: Record<string, string> = {
    cyan: 'text-neon-cyan border-neon-cyan/20 bg-cyan-950/20',
    green: 'text-neon-green border-green-700/20 bg-green-950/20',
    purple: 'text-neon-purple border-purple-700/20 bg-purple-950/20',
    yellow: 'text-yellow-400 border-yellow-700/20 bg-yellow-950/20',
  };

  return (
    <div className={`rounded-xl border p-5 ${colorMap[color] || colorMap.cyan}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-mono text-gray-500 tracking-wider">{label}</span>
        <Icon size={18} className="opacity-50" />
      </div>
      <div className="text-3xl font-orbitron font-black">{value}</div>
    </div>
  );
};
