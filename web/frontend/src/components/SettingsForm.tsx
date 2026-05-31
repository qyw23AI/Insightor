/* Settings form for user configuration */

import { useEffect, useState } from 'react';
import { getConfig, getConfigMasked, saveConfig } from '../api/client';
import { useAuth } from '../context/AuthContext';

const CONFIG_FIELDS = [
  { key: 'GITHUB_TOKEN', label: 'GitHub Token', placeholder: 'ghp_...', mask: true },
  { key: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', placeholder: 'sk-ant-...', mask: true },
  { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', placeholder: 'sk-...', mask: true },
  { key: 'DEEPSEEK_API_KEY', label: 'DeepSeek API Key', placeholder: 'sk-...', mask: true },
  { key: 'ANTHROPIC_BASE_URL', label: 'Anthropic Base URL', placeholder: 'https://api.anthropic.com', mask: false },
  { key: 'OPENAI_API_BASE', label: 'OpenAI API Base', placeholder: 'https://api.openai.com', mask: false },
  { key: 'DEEPSEEK_API_BASE', label: 'DeepSeek API Base', placeholder: 'https://api.deepseek.com', mask: false },
];

const MODEL_FIELDS = [
  { key: 'INSIGHTOR_MODELS_PRIMARY', label: 'Primary model (standard)', placeholder: 'deepseek-v4-pro' },
  { key: 'INSIGHTOR_MODELS_WEAK', label: 'Weak model (quick)', placeholder: 'deepseek-v4-flash' },
  { key: 'INSIGHTOR_MODELS_REASONING', label: 'Reasoning model (deep)', placeholder: 'deepseek-v4-pro' },
];

export default function SettingsForm() {
  const { token } = useAuth();
  const [configs, setConfigs] = useState<Record<string, string>>({});
  const [masked, setMasked] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) return;
    Promise.all([getConfig(token), getConfigMasked(token)]).then(([cfg, msk]) => {
      setConfigs(cfg);
      setMasked(msk);
    });
  }, [token]);

  const handleChange = (key: string, value: string) => {
    setConfigs(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    try {
      await saveConfig(token, configs);
      const msk = await getConfigMasked(token);
      setMasked(msk);
      setMessage('Saved');
      setTimeout(() => setMessage(''), 3000);
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
    setSaving(false);
  };

  return (
    <div className="space-y-6">
      {/* API Keys */}
      <div className="card space-y-4">
        <div className="mb-1">
          <h2 className="text-base font-semibold text-ink">API keys &amp; tokens</h2>
          <p className="text-sm text-muted mt-0.5">Credentials are encrypted before storage.</p>
        </div>
        {CONFIG_FIELDS.map(field => (
          <div key={field.key}>
            <label className="block text-sm font-medium text-muted mb-1.5">{field.label}</label>
            <input
              type="password"
              placeholder={masked[field.key] || field.placeholder}
              value={configs[field.key] || ''}
              onChange={e => handleChange(field.key, e.target.value)}
              className="input font-mono text-sm"
            />
            {masked[field.key] && !configs[field.key] && (
              <p className="text-xs text-faint mt-1 font-mono">Set: {masked[field.key]}</p>
            )}
          </div>
        ))}
      </div>

      {/* Model config */}
      <div className="card space-y-4">
        <h2 className="text-base font-semibold text-ink mb-1">Model configuration</h2>
        {MODEL_FIELDS.map(field => (
          <div key={field.key}>
            <label className="block text-sm font-medium text-muted mb-1.5">{field.label}</label>
            <input
              type="text"
              placeholder={field.placeholder}
              value={configs[field.key] || ''}
              onChange={e => handleChange(field.key, e.target.value)}
              className="input font-mono text-sm"
            />
          </div>
        ))}
      </div>

      <div className="flex items-center gap-4">
        <button onClick={handleSave} disabled={saving} className="btn-primary">
          {saving ? 'Saving...' : 'Save configuration'}
        </button>
        {message && (
          <span className={`text-sm ${message.startsWith('Error') ? 'text-error' : 'text-success'}`}>
            {message}
          </span>
        )}
      </div>
    </div>
  );
}
