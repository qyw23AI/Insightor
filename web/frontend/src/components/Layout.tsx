/* App shell — collapsible sidebar + content area */

import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/* ---- Icons ---- */
const LogoMark = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2C8 4.5 5.5 8.5 5.5 12C5.5 15.5 8 19.5 12 22C16 19.5 18.5 15.5 18.5 12C18.5 8.5 16 4.5 12 2Z" />
    <circle cx="12" cy="12" r="2.5" />
  </svg>
);

const DashboardIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="9" rx="1.5" />
    <rect x="14" y="3" width="7" height="5" rx="1.5" />
    <rect x="14" y="12" width="7" height="9" rx="1.5" />
    <rect x="3" y="16" width="7" height="5" rx="1.5" />
  </svg>
);

const SettingsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

const AdminIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

const LogoutIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </svg>
);

const ChevronLeftIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

/* ---- Nav items ---- */
const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', Icon: DashboardIcon },
  { path: '/settings',  label: 'Settings',  Icon: SettingsIcon },
];

const SIDEBAR_W   = 212;
const SIDEBAR_COL = 50;

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => { logout(); navigate('/login'); };

  const navItems = [
    ...NAV_ITEMS,
    ...(user?.is_admin ? [{ path: '/admin', label: 'Admin', Icon: AdminIcon }] : []),
  ];

  const initial = user?.username?.charAt(0).toUpperCase() ?? '?';

  return (
    <div className="flex h-screen bg-app-bg">
      {/* ---- Sidebar ---- */}
      <aside
        className="flex-shrink-0 border-r border-border flex flex-col overflow-hidden"
        style={{
          width: collapsed ? SIDEBAR_COL : SIDEBAR_W,
          transition: 'width 200ms cubic-bezier(0.16, 1, 0.3, 1)',
          background: 'oklch(0.155 0.004 268)',
        }}
      >
        {/* Header: logo + toggle */}
        <div
          className="flex items-center border-b border-border flex-shrink-0"
          style={{ height: 48, padding: collapsed ? '0 9px' : '0 10px', gap: 8 }}
        >
          <Link
            to="/dashboard"
            className="w-7 h-7 rounded-md bg-primary flex items-center justify-center flex-shrink-0 no-underline"
            title="Dashboard"
          >
            <LogoMark />
          </Link>

          {!collapsed && (
            <>
              <span className="flex-1 text-sm font-semibold text-ink whitespace-nowrap overflow-hidden leading-none">
                Insightor
              </span>
              <button
                onClick={() => setCollapsed(true)}
                className="icon-btn flex-shrink-0"
                title="Collapse sidebar"
                style={{ marginRight: -2 }}
              >
                <ChevronLeftIcon />
              </button>
            </>
          )}
        </div>

        {/* Nav links */}
        <nav className="flex-1 overflow-hidden" style={{ padding: '8px 6px' }}>
          {navItems.map(({ path, label, Icon }) => {
            const active = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                title={collapsed ? label : undefined}
                className={`flex items-center no-underline rounded-md transition-colors duration-100 ${
                  active
                    ? 'bg-app-surface-elevated text-ink font-medium'
                    : 'text-muted hover:text-ink hover:bg-app-surface-elevated'
                }`}
                style={{
                  gap: collapsed ? 0 : 8,
                  padding: collapsed ? '9px 0' : '8px 10px',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  fontSize: '0.875rem',
                  marginBottom: 2,
                }}
              >
                <span className="flex-shrink-0"><Icon /></span>
                {!collapsed && (
                  <span className="whitespace-nowrap overflow-hidden">{label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer: user info + logout */}
        <div className="flex-shrink-0 border-t border-border" style={{ padding: '6px' }}>
          {collapsed ? (
            /* Collapsed: avatar + expand button */
            <div className="flex flex-col items-center gap-1.5 py-0.5">
              <div
                className="w-7 h-7 rounded-md bg-primary flex items-center justify-center text-xs font-semibold text-white cursor-default"
                title={user?.username}
              >
                {initial}
              </div>
              <button
                onClick={() => setCollapsed(false)}
                className="icon-btn"
                title="Expand sidebar"
              >
                <ChevronRightIcon />
              </button>
            </div>
          ) : (
            /* Expanded: avatar + name + logout */
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-md">
              <div className="w-6 h-6 rounded bg-primary flex items-center justify-center text-xs font-semibold text-white flex-shrink-0">
                {initial}
              </div>
              <div className="flex-1 min-w-0 overflow-hidden">
                <p className="text-xs font-medium text-ink whitespace-nowrap overflow-hidden text-ellipsis leading-snug">
                  {user?.username}
                </p>
                <p className="text-[11px] text-faint leading-snug">
                  {user?.is_admin ? 'Admin' : 'Member'}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="icon-btn danger flex-shrink-0"
                title="Sign out"
              >
                <LogoutIcon />
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
