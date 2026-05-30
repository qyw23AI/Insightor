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
        <h1 className="text-2xl font-bold text-white">Admin Panel</h1>
        <p className="text-sm text-surface-200/60">User management</p>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700">
                <th className="text-left py-3 px-4 text-surface-200/50 font-medium">Username</th>
                <th className="text-left py-3 px-4 text-surface-200/50 font-medium">Role</th>
                <th className="text-left py-3 px-4 text-surface-200/50 font-medium">Created</th>
                <th className="text-left py-3 px-4 text-surface-200/50 font-medium">Last Login</th>
                <th className="text-right py-3 px-4 text-surface-200/50 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-b border-surface-700/50 hover:bg-surface-700/30">
                  <td className="py-3 px-4 text-white font-medium">{u.username}</td>
                  <td className="py-3 px-4">
                    <span className={`text-xs px-2 py-0.5 rounded ${u.is_admin ? 'bg-purple-500/20 text-purple-400' : 'bg-surface-700 text-surface-200/70'}`}>
                      {u.is_admin ? 'Admin' : 'User'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-surface-200/60">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="py-3 px-4 text-surface-200/60">
                    {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {!u.is_admin && (
                      <button onClick={() => handleDelete(u.id)} className="btn-danger text-xs py-1 px-3">
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading && <p className="text-center py-8 text-surface-200/40">Loading...</p>}
      </div>
    </div>
  );
}
