import React, { useState } from 'react';
import { Shield, Zap, Building2, GraduationCap, Check, ArrowRight, X, Sparkles } from 'lucide-react';

interface PricingPageProps {
  apiUrl: string;
  onClose: () => void;
}

interface Plan {
  id: string;
  name: string;
  price: string;
  period: string;
  description: string;
  icon: React.ReactNode;
  features: string[];
  cta: string;
  popular?: boolean;
  color: string;
}

const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Recherche',
    price: 'Gratuit',
    period: '',
    description: 'Pour la recherche académique et l\'exploration.',
    icon: <GraduationCap className="w-6 h-6" />,
    features: [
      '5 analyses / mois',
      'Tous formats EEG',
      'Rapport clinique',
      'Watermark "Recherche"',
      'Communauté Discord',
    ],
    cta: 'Commencer gratuitement',
    color: 'neon-green',
  },
  {
    id: 'starter',
    name: 'Starter',
    price: '50€',
    period: '/mois',
    description: 'Pour les praticiens indépendants.',
    icon: <Zap className="w-6 h-6" />,
    features: [
      '100 analyses / mois',
      '1 utilisateur',
      'API REST complète',
      'Rapport PDF',
      'Support email',
    ],
    cta: 'Choisir Starter',
    color: 'neon-cyan',
  },
  {
    id: 'clinique',
    name: 'Clinique',
    price: '250€',
    period: '/mois',
    description: 'Pour les cliniques et cabinets.',
    icon: <Shield className="w-6 h-6" />,
    features: [
      '500 analyses / mois',
      '5 utilisateurs',
      'API REST complète',
      'Rapport PDF personnalisé',
      'Support prioritaire',
    ],
    cta: 'Choisir Clinique',
    popular: true,
    color: 'neon-cyan',
  },
  {
    id: 'institution',
    name: 'Institution',
    price: '1000€',
    period: '/mois',
    description: 'Pour les hôpitaux et réseaux de santé.',
    icon: <Building2 className="w-6 h-6" />,
    features: [
      'Analyses illimitées',
      'Multi-sites',
      'Intégration DPI (FHIR R4)',
      'SLA 99.9%',
      'Support dédié 24/7',
    ],
    cta: 'Demander un devis',
    color: 'neon-purple',
  },
];

export const PricingPage: React.FC<PricingPageProps> = ({ apiUrl, onClose }) => {
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [formData, setFormData] = useState({ name: '', email: '', organization: '' });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSelectPlan = (planId: string) => {
    setSelectedPlan(planId);
    setSuccess(false);
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlan || !formData.name || !formData.email) return;

    setSubmitting(true);
    setError('');

    try {
      // For free plan: self-service signup via public endpoint
      if (selectedPlan === 'free') {
        const res = await fetch(`${apiUrl}/signup`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            plan: 'free',
            owner: formData.name,
            email: formData.email,
            organization: formData.organization,
          }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `Erreur ${res.status}`);
        }
        setSuccess(true);
      } else {
        // For paid plans: send contact request
        const res = await fetch(`${apiUrl}/contact`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            plan: selectedPlan,
            name: formData.name,
            email: formData.email,
            organization: formData.organization,
          }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `Erreur ${res.status}`);
        }
        setSuccess(true);
      }
    } catch (err: any) {
      // Fallback: open mailto
      const plan = PLANS.find(p => p.id === selectedPlan);
      const subject = encodeURIComponent(`Neuro-Link — ${plan?.name || selectedPlan}`);
      const body = encodeURIComponent(
        `Nom: ${formData.name}\nEmail: ${formData.email}\nOrganisation: ${formData.organization}\nPlan: ${plan?.name}\n\nMessage:\n`
      );
      window.open(`mailto:contact@neuro-link.ai?subject=${subject}&body=${body}`, '_blank');
      setSuccess(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="relative w-full max-w-6xl bg-neon-bg border border-neon-border rounded-2xl shadow-2xl max-h-[95vh] overflow-y-auto">
        
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 p-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/5 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="text-center pt-10 pb-6 px-6">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-neon-cyan" />
            <span className="font-orbitron text-[10px] tracking-[6px] text-neon-cyan uppercase">Plans & Tarifs</span>
            <Sparkles className="w-5 h-5 text-neon-cyan" />
          </div>
          <h2 className="font-orbitron text-2xl md:text-3xl font-bold text-white tracking-wider mb-3">
            Choisissez votre plan
          </h2>
          <p className="text-gray-400 max-w-lg mx-auto text-sm">
            Gratuit pour la recherche. Plans professionnels pour les cliniques et institutions.
          </p>
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 px-6 pb-6">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              onClick={() => handleSelectPlan(plan.id)}
              className={`relative rounded-xl p-5 cursor-pointer transition-all duration-300 border ${
                selectedPlan === plan.id
                  ? 'border-neon-cyan bg-neon-cyan/5 shadow-glow-cyan scale-[1.02]'
                  : 'border-neon-border bg-neon-panel hover:border-neon-border-light hover:bg-neon-panel-alt'
              }`}
            >
              {/* Popular badge */}
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 bg-neon-cyan text-black font-orbitron text-[9px] font-bold rounded-full tracking-wider">
                    POPULAIRE
                  </span>
                </div>
              )}

              {/* Plan header */}
              <div className="flex items-center gap-3 mb-4">
                <div className={`p-2 rounded-lg bg-${plan.color}/10 text-${plan.color}`}>
                  {plan.icon}
                </div>
                <div>
                  <h3 className="font-orbitron text-sm font-bold text-white tracking-wider">{plan.name}</h3>
                  <p className="text-[11px] text-gray-500">{plan.description}</p>
                </div>
              </div>

              {/* Price */}
              <div className="mb-4">
                <span className="font-orbitron text-3xl font-black text-white">{plan.price}</span>
                {plan.period && <span className="text-gray-500 text-sm ml-1">{plan.period}</span>}
              </div>

              {/* Features */}
              <ul className="space-y-2 mb-5">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-400">
                    <Check className="w-3.5 h-3.5 text-neon-cyan flex-shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <button
                onClick={(e) => { e.stopPropagation(); handleSelectPlan(plan.id); }}
                className={`w-full py-2.5 rounded-lg font-orbitron text-xs font-bold tracking-wider transition-all duration-300 flex items-center justify-center gap-2 ${
                  selectedPlan === plan.id
                    ? 'bg-neon-cyan text-black shadow-glow-cyan'
                    : plan.popular
                    ? 'bg-neon-cyan/15 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/25'
                    : 'bg-neon-border/30 text-gray-400 border border-neon-border hover:text-white hover:border-neon-border-light'
                }`}
              >
                {selectedPlan === plan.id ? 'SÉLECTIONNÉ' : plan.cta.toUpperCase()}
                {selectedPlan === plan.id && <Check className="w-3.5 h-3.5" />}
              </button>
            </div>
          ))}
        </div>

        {/* Signup Form */}
        {selectedPlan && !success && (
          <div className="border-t border-neon-border mx-6 pt-6 pb-8">
            <h3 className="font-orbitron text-sm text-white tracking-wider mb-4 text-center">
              {selectedPlan === 'free' ? 'INSCRIPTION GRATUITE' : 'DEMANDE DE SOUSCRIPTION'}
            </h3>
            <form onSubmit={handleSubmit} className="max-w-md mx-auto space-y-3">
              <input
                type="text"
                placeholder="Nom complet *"
                required
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-4 py-2.5 bg-neon-panel border border-neon-border rounded-lg text-white text-sm
                           placeholder:text-gray-600 focus:border-neon-cyan/50 focus:outline-none focus:ring-1 focus:ring-neon-cyan/20 transition-all"
              />
              <input
                type="email"
                placeholder="Email professionnel *"
                required
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-4 py-2.5 bg-neon-panel border border-neon-border rounded-lg text-white text-sm
                           placeholder:text-gray-600 focus:border-neon-cyan/50 focus:outline-none focus:ring-1 focus:ring-neon-cyan/20 transition-all"
              />
              <input
                type="text"
                placeholder="Organisation (optionnel)"
                value={formData.organization}
                onChange={(e) => setFormData(prev => ({ ...prev, organization: e.target.value }))}
                className="w-full px-4 py-2.5 bg-neon-panel border border-neon-border rounded-lg text-white text-sm
                           placeholder:text-gray-600 focus:border-neon-cyan/50 focus:outline-none focus:ring-1 focus:ring-neon-cyan/20 transition-all"
              />
              {error && (
                <p className="text-neon-red text-xs text-center">{error}</p>
              )}
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 bg-neon-cyan text-black font-orbitron text-xs font-bold tracking-wider rounded-lg
                           hover:shadow-glow-cyan-lg transition-all duration-300 flex items-center justify-center gap-2
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'TRAITEMENT...' : selectedPlan === 'free' ? 'CRÉER MON COMPTE' : 'ENVOYER LA DEMANDE'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="border-t border-neon-border mx-6 pt-6 pb-8 text-center">
            <div className="w-12 h-12 rounded-full bg-neon-green/15 flex items-center justify-center mx-auto mb-3">
              <Check className="w-6 h-6 text-neon-green" />
            </div>
            <h3 className="font-orbitron text-sm text-white tracking-wider mb-2">
              {selectedPlan === 'free' ? 'COMPTE CRÉÉ' : 'DEMANDE ENVOYÉE'}
            </h3>
            <p className="text-gray-400 text-sm max-w-md mx-auto">
              {selectedPlan === 'free'
                ? 'Vérifiez votre email pour votre clé API. Vous pouvez commencer à utiliser Neuro-Link immédiatement.'
                : 'Notre équipe vous contactera sous 24h pour finaliser votre souscription.'
              }
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="border-t border-neon-border px-6 py-4 text-center">
          <p className="text-[10px] text-gray-600">
            ⚠️ Neuro-Link est un outil d'aide à la recherche. Les résultats doivent être interprétés par un professionnel de santé qualifié.
          </p>
        </div>
      </div>
    </div>
  );
};
