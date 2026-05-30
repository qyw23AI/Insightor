/* Login page */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { login, register } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const auth = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const fn = tab === 'login' ? login : register;
      const result = await fn(username, password);
      auth.login(result.token, result.user);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Auth failed');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-950 px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <span className="text-5xl">🪄</span>
          <h1 className="mt-4 text-3xl font-bold text-white">Insightor</h1>
          <p className="mt-2 text-surface-200/60">AI-Powered PR Review Console</p>
        </div>

        <div className="card space-y-6">
          <div className="flex border-b border-surface-700">
            {(['login', 'register'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`tab flex-1 ${tab === t ? 'active' : ''}`}
              >
                {t === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text" placeholder="Username" value={username}
              onChange={e => setUsername(e.target.value)} className="input" required
            />
            <input
              type="password" placeholder="Password" value={password}
              onChange={e => setPassword(e.target.value)} className="input" required
            />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Please wait...' : tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <p className="text-xs text-center text-surface-200/40">
            {tab === 'login' ? (
              <>Default: admin / admin123</>
            ) : (
              <>Already have an account? <Link to="/login" onClick={() => setTab('login')} className="text-blue-400 hover:underline">Sign in</Link></>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
