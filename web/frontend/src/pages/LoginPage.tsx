/* Login / register */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { login, register } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [tab, setTab]       = useState<'login' | 'register'>('login');
  const [username, setUser] = useState('');
  const [password, setPass] = useState('');
  const [error, setError]   = useState('');
  const [loading, setLoad]  = useState(false);
  const auth = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoad(true);
    try {
      const fn = tab === 'login' ? login : register;
      const res = await fn(username, password);
      auth.login(res.token, res.user);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    }
    setLoad(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-app-bg px-4">
      <div className="w-full max-w-sm space-y-7 animate-fade-in">

        {/* Brand */}
        <div className="text-center">
          <div className="w-11 h-11 rounded-xl bg-primary flex items-center justify-center mx-auto mb-4">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2C8 4.5 5.5 8.5 5.5 12C5.5 15.5 8 19.5 12 22C16 19.5 18.5 15.5 18.5 12C18.5 8.5 16 4.5 12 2Z" />
              <circle cx="12" cy="12" r="2.5" />
            </svg>
          </div>
          <h1 className="text-lg font-semibold text-ink tracking-tight">Insightor</h1>
          <p className="mt-1 text-sm text-muted">AI-powered PR review console</p>
        </div>

        {/* Card */}
        <div className="card space-y-4">
          {/* Tab switcher */}
          <div className="flex bg-app-surface rounded-md p-1 gap-1">
            {(['login', 'register'] as const).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`flex-1 py-1.5 text-sm font-medium rounded transition-all duration-150 ${
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
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label htmlFor="username" className="block text-xs font-medium text-muted mb-1.5">
                Username
              </label>
              <input
                id="username" type="text" placeholder="Enter your username"
                value={username} onChange={e => setUser(e.target.value)}
                className="input" required autoComplete="username"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-muted mb-1.5">
                Password
              </label>
              <input
                id="password" type="password" placeholder="Enter your password"
                value={password} onChange={e => setPass(e.target.value)}
                className="input" required
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <div className="text-xs text-error bg-error/8 border border-error/15 rounded px-3 py-2">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full mt-1">
              {loading ? 'Please wait...' : tab === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>

          <p className="text-xs text-center text-muted pt-0.5">
            {tab === 'login' ? (
              <>Default: <span className="text-ink font-mono">admin / admin123</span></>
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
