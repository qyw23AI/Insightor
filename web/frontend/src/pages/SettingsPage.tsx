/* Settings page */

import SettingsForm from '../components/SettingsForm';

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-ink tracking-tight">Settings</h1>
        <p className="text-sm text-muted mt-0.5">Configure API keys and model preferences</p>
      </div>
      <SettingsForm />
    </div>
  );
}
