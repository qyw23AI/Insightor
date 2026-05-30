/* Settings page */

import SettingsForm from '../components/SettingsForm';

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-surface-200/60">Configure your API keys and model preferences</p>
      </div>
      <SettingsForm />
    </div>
  );
}
