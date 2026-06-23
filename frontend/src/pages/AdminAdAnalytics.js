import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import axios from 'axios';
import TopNav from '../components/TopNav';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { ChartBar, Download, CaretLeft } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Admin Ads Analytics — 7-day window by default with selectable 1/7/30 day windows.
// CSV export hits the backend with the same window query string.
export default function AdminAdAnalytics() {
  const { user } = useAuth();
  const [days, setDays] = useState(7);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const canAccess = user && (user.role === 'admin' || user.can_manage_ads === true);

  const load = async (windowDays = days) => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/ads/analytics`, { params: { days: windowDays }, withCredentials: true });
      setData(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load analytics');
    } finally { setLoading(false); }
  };

  useEffect(() => { if (canAccess) load(days); }, [canAccess, days]); // eslint-disable-line

  if (!user) return null;
  if (!canAccess) return <Navigate to="/dashboard" replace />;

  const downloadCsv = () => {
    const url = `${API}/admin/ads/analytics/export?days=${days}`;
    // Open in new tab so the browser handles the download via the cookie session
    window.open(url, '_blank');
  };

  const fmt = (n) => (n ?? 0).toLocaleString();
  const fmtPct = (n) => `${(n ?? 0).toFixed(2)}%`;

  return (
    <div className="min-h-screen bg-[#0A0A0A]/60 text-white">
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-10" data-testid="admin-ad-analytics-page">
        <Link to="/admin/ads" className="text-xs text-[#A3A3A3] hover:text-white flex items-center gap-1 mb-4" data-testid="back-to-ads">
          <CaretLeft weight="bold" /> BACK TO ADS
        </Link>
        <div className="flex items-center justify-between mb-2 flex-wrap gap-3">
          <div>
            <p className="text-xs font-bold tracking-[0.3em] text-[#FF3B30]">ADMIN</p>
            <h1 className="text-4xl font-black mt-1 flex items-center gap-3"><ChartBar weight="bold" /> ADS ANALYTICS</h1>
          </div>
          <div className="flex items-center gap-2">
            {[1, 7, 30].map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                data-testid={`window-${d}d`}
                className={`px-3 py-1.5 text-xs font-bold border transition-colors ${
                  days === d ? 'bg-[#FF3B30] text-white border-[#FF3B30]' : 'border-[#262626] text-[#A3A3A3] hover:border-white hover:text-white'
                }`}
              >
                {d}D
              </button>
            ))}
            <button
              onClick={downloadCsv}
              data-testid="export-csv"
              className="ml-2 px-3 py-1.5 text-xs font-bold border border-[#22C55E] text-[#22C55E] hover:bg-[#22C55E] hover:text-black flex items-center gap-1"
            >
              <Download weight="bold" /> CSV
            </button>
          </div>
        </div>
        <p className="text-sm text-[#A3A3A3] mt-2 mb-8">
          Track impressions, clicks and CTR per ad. CSV export is invoice-ready for sponsors paying CPM.
        </p>

        {loading || !data ? (
          <div className="text-[#A3A3A3] text-sm">Loading…</div>
        ) : (
          <>
            {/* Totals row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="border border-[#262626] bg-[#141414] p-4">
                <p className="text-[10px] font-bold tracking-[0.25em] text-[#A3A3A3]">IMPRESSIONS ({days}D)</p>
                <p className="text-3xl font-black mt-1" data-testid="total-impressions">{fmt(data.totals?.impressions)}</p>
              </div>
              <div className="border border-[#262626] bg-[#141414] p-4">
                <p className="text-[10px] font-bold tracking-[0.25em] text-[#A3A3A3]">CLICKS ({days}D)</p>
                <p className="text-3xl font-black mt-1" data-testid="total-clicks">{fmt(data.totals?.clicks)}</p>
              </div>
              <div className="border border-[#262626] bg-[#141414] p-4">
                <p className="text-[10px] font-bold tracking-[0.25em] text-[#A3A3A3]">CTR ({days}D)</p>
                <p className="text-3xl font-black mt-1 text-[#22C55E]" data-testid="total-ctr">{fmtPct(data.totals?.ctr)}</p>
              </div>
              <div className="border border-[#262626] bg-[#141414] p-4">
                <p className="text-[10px] font-bold tracking-[0.25em] text-[#A3A3A3]">ACTIVE ADS</p>
                <p className="text-3xl font-black mt-1">{data.rows?.filter(r => r.active).length || 0}</p>
              </div>
            </div>

            {/* Per-ad table */}
            <div className="border border-[#262626] bg-[#141414] overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] font-bold tracking-[0.2em] text-[#A3A3A3] border-b border-[#262626]">
                    <th className="text-left px-4 py-3">AD</th>
                    <th className="text-right px-3 py-3">IMPR ({days}D)</th>
                    <th className="text-right px-3 py-3">CLICKS ({days}D)</th>
                    <th className="text-right px-3 py-3">CTR ({days}D)</th>
                    <th className="text-right px-3 py-3">IMPR (TOTAL)</th>
                    <th className="text-right px-3 py-3">CLICKS (TOTAL)</th>
                    <th className="text-right px-4 py-3">STATUS</th>
                  </tr>
                </thead>
                <tbody data-testid="analytics-table">
                  {(data.rows || []).map(r => (
                    <tr key={r.id} className="border-b border-[#262626] hover:bg-[#0A0A0A]" data-testid={`row-${r.id}`}>
                      <td className="px-4 py-3 truncate max-w-xs"><strong>{r.name}</strong></td>
                      <td className="px-3 py-3 text-right tabular-nums">{fmt(r.window_impressions)}</td>
                      <td className="px-3 py-3 text-right tabular-nums">{fmt(r.window_clicks)}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-[#22C55E]">{fmtPct(r.window_ctr)}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-[#A3A3A3]">{fmt(r.total_impressions)}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-[#A3A3A3]">{fmt(r.total_clicks)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`text-[10px] font-bold tracking-wider px-2 py-1 ${r.active ? 'text-[#22C55E] border border-[#22C55E]/40' : 'text-[#525252] border border-[#525252]/40'}`}>
                          {r.active ? 'ACTIVE' : 'PAUSED'}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {(data.rows || []).length === 0 && (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-[#A3A3A3]" data-testid="no-rows">No ad activity yet. Create ads at <Link to="/admin/ads" className="text-[#FF3B30] hover:underline">/admin/ads</Link>.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
