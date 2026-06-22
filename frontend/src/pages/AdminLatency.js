import React, { useEffect, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import TopNav from '../components/TopNav';
import LatencyGraph from '../components/LatencyGraph';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { MagnifyingGlass, ChartLine, Clock, Warning } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Admin-only latency analytics dashboard.
// Lists matches (tournament + competition) that have latency samples; clicking one
// loads the spike/dip line graph. Admin can extend retention on samples when a
// dispute is ongoing.
export default function AdminLatency() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [q, setQ] = useState('');
  const [selected, setSelected] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.role === 'admin') refresh();
  }, [user?.role]); // eslint-disable-line

  useEffect(() => {
    // Allow deep-link via /admin/latency?kind=tournament&id=...
    const kind = params.get('kind');
    const id = params.get('id');
    const match_id = params.get('match_id');
    if (kind && id) openGraph({ kind, id, match_id });
  }, []); // eslint-disable-line

  if (!user) return null;
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />;

  const refresh = async (search = '') => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/latency/dashboard`, { params: search ? { q: search } : {}, withCredentials: true });
      setItems(r.data.items || []);
    } catch (e) { toast.error('Failed to load latency dashboard'); }
    finally { setLoading(false); }
  };

  const openGraph = async ({ kind, id, match_id }) => {
    setSelected({ kind, id, match_id });
    setGraphData(null);
    const url = kind === 'tournament'
      ? `${API}/admin/latency/tournament/${id}`
      : `${API}/admin/latency/competition/${id}${match_id ? `?match_id=${match_id}` : ''}`;
    try {
      const r = await axios.get(url, { withCredentials: true });
      setGraphData(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load graph');
    }
  };

  const extendRetention = async () => {
    if (!selected) return;
    const daysStr = window.prompt('Extend retention by how many days? (1-730)', '90');
    if (!daysStr) return;
    const days = parseInt(daysStr, 10);
    if (Number.isNaN(days) || days < 1) return;
    const endpoint = selected.kind === 'tournament'
      ? `${API}/admin/latency/tournament/${selected.id}/extend-retention`
      : `${API}/admin/latency/competition/${selected.id}/extend-retention`;
    try {
      const r = await axios.post(`${endpoint}?days=${days}`, {}, { withCredentials: true });
      toast.success(`Retention extended — ${r.data.updated_samples} samples now expire ${new Date(r.data.new_expiry).toLocaleDateString()}`);
      refresh(q);
    } catch (e) { toast.error('Extend failed'); }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]/60 text-white">
      <TopNav />
      <div className="max-w-7xl mx-auto px-6 py-10" data-testid="admin-latency-page">
        <p className="text-xs font-bold tracking-[0.3em] text-[#FF3B30]">ADMIN</p>
        <h1 className="text-4xl font-black mt-1 flex items-center gap-3"><ChartLine weight="bold" /> LATENCY</h1>
        <p className="text-sm text-[#A3A3A3] mt-2 mb-8">Spike/dip analysis to back up dispute decisions. Samples retained 30 days unless extended.</p>

        <form onSubmit={(e) => { e.preventDefault(); refresh(q); }} className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A3A3A3]" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              data-testid="lat-search-input"
              placeholder="Search game / platform / status…"
              className="w-full bg-[#141414] border border-[#262626] pl-10 pr-3 py-2 text-sm"
            />
          </div>
          <button type="submit" className="border border-[#262626] hover:border-white px-5 py-2 text-sm font-bold tracking-wider">SEARCH</button>
        </form>

        <div className="grid lg:grid-cols-[1fr_2fr] gap-6">
          {/* Match list */}
          <div className="border border-[#262626] bg-[#141414]">
            <div className="px-4 py-3 border-b border-[#262626] text-xs font-bold tracking-[0.25em] text-[#A3A3A3]">MATCHES WITH SAMPLES</div>
            <div className="max-h-[60vh] overflow-y-auto" data-testid="lat-items-list">
              {loading ? (
                <div className="p-6 text-sm text-[#A3A3A3]">Loading…</div>
              ) : items.length === 0 ? (
                <div className="p-6 text-sm text-[#A3A3A3]" data-testid="lat-no-items">No matches have latency samples yet.</div>
              ) : items.map((it, idx) => (
                <button key={`${it.kind}-${it.id}-${idx}`} onClick={() => openGraph(it)}
                  className={`w-full text-left px-4 py-3 border-b border-[#262626] hover:bg-[#0A0A0A] ${selected?.id === it.id ? 'bg-[#0A0A0A]' : ''}`}
                  data-testid={`lat-item-${it.id}`}>
                  <div className="flex items-center justify-between">
                    <div className="font-bold text-sm">{it.game_name}</div>
                    {it.is_disputed && <span className="text-[10px] bg-[#FF3B30] text-white font-bold px-2 py-0.5 flex items-center gap-1"><Warning weight="fill" />DISPUTED</span>}
                  </div>
                  <div className="text-[11px] text-[#A3A3A3] mt-1">
                    {it.kind} · {it.platform || '—'} · {it.status} · {it.sample_count} samples
                  </div>
                  {it.retention_extended && (
                    <div className="text-[10px] text-[#22C55E] mt-1 flex items-center gap-1"><Clock />Retention extended</div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Graph */}
          <div>
            {!selected ? (
              <div className="border border-[#262626] bg-[#141414] p-8 text-center text-sm text-[#A3A3A3]">
                ← Choose a match to see its latency graph
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-bold tracking-[0.25em] text-[#A3A3A3]">
                    {selected.kind.toUpperCase()} · {selected.id.slice(0, 8)}…
                  </div>
                  <button onClick={extendRetention} className="text-xs border border-[#262626] hover:border-[#22C55E] hover:text-[#22C55E] px-3 py-1.5 font-bold" data-testid="lat-extend-retention">
                    EXTEND RETENTION
                  </button>
                </div>
                <LatencyGraph data={graphData} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
