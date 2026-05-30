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
  { key: 'INSIGHTOR_MODELS_PRIMARY', label: 'Primary Model (standard)', placeholder: 'deepseek-v4-pro' },
  { key: 'INSIGHTOR_MODELS_WEAK', label: 'Weak Model (quick)', placeholder: 'deepseek-v4-flash' },
  { key: 'INSIGHTOR_MODELS_REASONING', label: 'Reasoning Model (deep)', placeholder: 'deepseek-v4-pro' },
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
      setMessage('Saved successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
    setSaving(false);
  };

  return (
    <div className="space-y-8">
      <div className="card space-y-4">
        <h2 className="text-lg font-bold text-white">🔑 API Keys & Tokens</h2>
        <p className="text-sm text-surface-200/60">Your credentials are encrypted before storage.</p>
        {CONFIG_FIELDS.map(field => (
          <div key={field.key}>
            <label className="block text-sm font-medium text-surface-200/80 mb-1.5">{field.label}</label>
            <div className="relative">
              <input
                type="password"
                placeholder={masked[field.key] || field.placeholder}
                value={configs[field.key] || ''}
                onChange={e => handleChange(field.key, e.target.value)}
                className="input font-mono text-sm"
              />
              {masked[field.key] && !configs[field.key] && (
                <p className="text-xs text-surface-200/50 mt-1">Current: {masked[field.key]}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="card space-y-4">
        <h2 className="text-lg font-bold text-white">🤖 Model Configuration</h2>
        {MODEL_FIELDS.map(field => (
          <div key={field.key}>
            <label className="block text-sm font-medium text-surface-200/80 mb-1.5">{field.label}</label>
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
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
        {message && (
          <span className={`text-sm ${message.startsWith('Error') ? 'text-red-400' : 'text-green-400'}`}>
            {message}
          </span>
        )}
      </div>
    </div>
  );
}
