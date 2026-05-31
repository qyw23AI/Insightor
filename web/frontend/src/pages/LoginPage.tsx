/* Login / register page */

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
    <div className="min-h-screen flex items-center justify-center bg-app-bg px-4">
      <div className="w-full max-w-sm space-y-8 animate-fade-in">
        {/* Brand mark */}
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center mx-auto mb-4">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2C8 4.5 5.5 8.5 5.5 12C5.5 15.5 8 19.5 12 22C16 19.5 18.5 15.5 18.5 12C18.5 8.5 16 4.5 12 2Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-ink tracking-tight">Insightor</h1>
          <p className="mt-1.5 text-sm text-muted">AI-powered PR review</p>
        </div>

        {/* Card */}
        <div className="card p-6 space-y-5">
          {/* Tab switcher */}
          <div className="flex bg-app-surface rounded-md p-1 gap-1">
            {(['login', 'register'] as const).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`flex-1 py-1.5 text-sm font-medium rounded-sm transition-all duration-150 ${
                  tab === t
                    ? 'bg-app-surface-high text-ink'
                    : 'text-muted hover:text-ink'
                }`}
              >
                {t === 'login' ? 'Sign in' : 'Create account'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-xs font-medium text-muted mb-1.5">
                Username
              </label>
              <input
                id="username" type="text" placeholder="Enter your username"
                value={username} onChange={e => setUsername(e.target.value)}
                className="input" required autoComplete="username"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-muted mb-1.5">
                Password
              </label>
              <input
                id="password" type="password" placeholder="Enter your password"
                value={password} onChange={e => setPassword(e.target.value)}
                className="input" required
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <div className="text-sm text-error bg-error/10 border border-error/15 rounded-md px-3 py-2.5">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Please wait...' : tab === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>

          <p className="text-xs text-center text-muted">
            {tab === 'login' ? (
              <>Default credentials: <span className="text-ink font-mono">admin / admin123</span></>
            ) : (
              <>Already have an account?{' '}
                <Link
                  to="/login" onClick={() => setTab('login')}
                  className="text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
                >
                  Sign in
                </Link>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
