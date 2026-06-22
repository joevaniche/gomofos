import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import axios from 'axios';
import TopNav from '../components/TopNav';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Plus, Trash, ShieldStar } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminAdManagers() {
  const { user } = useAuth();
  const [managers, setManagers] = useState([]);
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);

  const load = async () => {
    try {
      const r = await axios.get(`${API}/admin/ad-managers`, { withCredentials: true });
      setManagers(r.data || []);
    } catch (e) { toast.error('Failed to load'); }
  };

  useEffect(() => { if (user?.role === 'admin') load(); }, [user?.role]);

  if (!user) return null;
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />;

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!q.trim()) return setResults([]);
    try {
      const r = await axios.get(`${API}/users/search`, { params: { q: q.trim() }, withCredentials: true });
      setResults(r.data || []);
    } catch (e) { toast.error('Search failed'); }
  };

  const grant = async (u) => {
    try {
      await axios.post(`${API}/admin/ad-managers`, { user_id: u.id }, { withCredentials: true });
      toast.success(`${u.username} can now manage ads`);
      load();
      setResults(results.filter(r => r.id !== u.id));
    } catch (e) { toast.error(e.response?.data?.detail || 'Grant failed'); }
  };

  const revoke = async (m) => {
    if (m.is_site_admin) { toast.error('Site admins always have access — change role first'); return; }
    if (!window.confirm(`Revoke ad-manager access from ${m.username}?`)) return;
    try {
      await axios.delete(`${API}/admin/ad-managers/${m.id}`, { withCredentials: true });
      toast.success('Revoked');
      load();
    } catch (e) { toast.error('Revoke failed'); }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]/60 text-white">
      <TopNav />
      <div className="max-w-4xl mx-auto px-6 py-10" data-testid="admin-ad-managers-page">
        <p className="text-xs font-bold tracking-[0.3em] text-[#FF3B30]">ADMIN</p>
        <h1 className="text-4xl font-black mt-1">AD MANAGERS</h1>
        <p className="text-sm text-[#A3A3A3] mt-2 mb-8">
          Site admins have ad-manager access by default. Grant additional users access here.
        </p>

        <div className="border border-[#262626] bg-[#141414] p-6 mb-8">
          <h2 className="text-sm font-bold tracking-[0.25em] text-[#A3A3A3] mb-4 flex items-center gap-2">
            <Plus weight="bold" /> GRANT ACCESS
          </h2>
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              data-testid="adm-search-input"
              placeholder="Search by username…"
              className="flex-1 bg-[#0A0A0A] border border-[#262626] px-3 py-2 text-sm"
            />
            <button type="submit" className="border border-[#FF3B30] text-[#FF3B30] hover:bg-[#FF3B30] hover:text-white px-5 py-2 text-sm font-bold">SEARCH</button>
          </form>
          {results.length > 0 && (
            <div className="mt-4 space-y-2" data-testid="adm-search-results">
              {results.slice(0, 10).map(r => (
                <div key={r.id} className="flex items-center justify-between bg-[#0A0A0A] border border-[#262626] px-3 py-2">
                  <div className="text-sm">{r.username}</div>
                  <button onClick={() => grant(r)} className="text-xs font-bold text-[#FF3B30] hover:text-white" data-testid={`adm-grant-${r.id}`}>GRANT ACCESS →</button>
                </div>
              ))}
            </div>
          )}
        </div>

        <h2 className="text-sm font-bold tracking-[0.25em] text-[#A3A3A3] mb-4">CURRENT ACCESS</h2>
        <div className="space-y-2" data-testid="adm-managers-list">
          {managers.map(m => (
            <div key={m.id} className="flex items-center justify-between bg-[#141414] border border-[#262626] px-4 py-3" data-testid={`adm-row-${m.id}`}>
              <div className="flex items-center gap-3">
                <ShieldStar weight={m.is_site_admin ? 'fill' : 'bold'} className={m.is_site_admin ? 'text-[#F59E0B]' : 'text-[#A3A3A3]'} />
                <div>
                  <div className="font-bold">{m.username}</div>
                  <div className="text-xs text-[#A3A3A3]">{m.email}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-[10px] font-bold tracking-wider px-2 py-1 ${m.is_site_admin ? 'text-[#F59E0B] border border-[#F59E0B]/40' : 'text-[#22C55E] border border-[#22C55E]/40'}`}>
                  {m.is_site_admin ? 'SITE ADMIN' : 'AD MANAGER'}
                </span>
                {!m.is_site_admin && (
                  <button onClick={() => revoke(m)} className="text-[#A3A3A3] hover:text-[#FF3B30]" title="Revoke" data-testid={`adm-revoke-${m.id}`}>
                    <Trash weight="bold" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
