/* Admin page — user management */

import { useEffect, useState } from 'react';
import { deleteUser, listUsers } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { UserInfo } from '../types/urf';

export default function AdminPage() {
  const { token } = useAuth();
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!token) return;
    const data = await listUsers(token);
    setUsers(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [token]);

  const handleDelete = async (userId: string) => {
    if (!token || !confirm('Delete this user? This cannot be undone.')) return;
    await deleteUser(token, userId);
    load();
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink tracking-tight">Admin panel</h1>
        <p className="text-base text-muted mt-0.5">User management</p>
      </div>

      <div className="card !p-0 overflow-hidden">
        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex gap-4 px-4">
                <div className="skeleton h-10 flex-1" />
                <div className="skeleton h-10 w-16" />
                <div className="skeleton h-10 w-24" />
                <div className="skeleton h-10 w-24" />
                <div className="skeleton h-10 w-16" />
              </div>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-base">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-faint font-medium text-xs">Username</th>
                  <th className="text-left py-3 px-4 text-faint font-medium text-xs">Role</th>
                  <th className="text-left py-3 px-4 text-faint font-medium text-xs">Created</th>
                  <th className="text-left py-3 px-4 text-faint font-medium text-xs">Last login</th>
                  <th className="text-right py-3 px-4 text-faint font-medium text-xs">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-16 text-muted">
                      <p className="text-base">No users found</p>
                    </td>
                  </tr>
                ) : (
                  users.map(u => (
                    <tr key={u.id} className="border-b border-border hover:bg-app-surface transition-colors">
                      <td className="py-3 px-4 text-ink font-medium">{u.username}</td>
                      <td className="py-3 px-4">
                        <span className={`badge ${u.is_admin ? 'badge-info' : 'badge-low'}`}>
                          {u.is_admin ? 'Admin' : 'User'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-muted tabular-nums text-sm">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-3 px-4 text-muted text-sm">
                        {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {!u.is_admin && (
                          <button onClick={() => handleDelete(u.id)} className="btn-danger btn-sm">
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
