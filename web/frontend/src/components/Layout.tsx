/* Layout: sidebar navigation + content area */

import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-surface-950">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-surface-700/50 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-6 border-b border-surface-700/50">
          <Link to="/dashboard" className="flex items-center gap-2.5">
            <span className="text-2xl">🪄</span>
            <div>
              <h1 className="text-lg font-bold text-white">Insightor</h1>
              <p className="text-xs text-surface-200/50">AI-Powered PR Review</p>
            </div>
          </Link>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-link ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
          {user?.is_admin && (
            <Link
              to="/admin"
              className={`sidebar-link ${location.pathname === '/admin' ? 'active' : ''}`}
            >
              <span>👥</span>
              <span>Admin</span>
            </Link>
          )}
        </nav>

        {/* User info */}
        <div className="px-3 py-4 border-t border-surface-700/50">
          <div className="flex items-center gap-3 px-4 py-2">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold">
              {user?.username?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user?.username}</p>
              <p className="text-xs text-surface-200/50">{user?.is_admin ? 'Admin' : 'User'}</p>
            </div>
          </div>
          <button onClick={handleLogout} className="sidebar-link w-full mt-2 text-red-400 hover:text-red-300">
            <span>🚪</span>
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
