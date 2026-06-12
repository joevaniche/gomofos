import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import TopNav from '../components/TopNav';
import axios from 'axios';
import Logo from '../components/Logo';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, Warning, CheckCircle, XCircle, Gauge, Trophy, Crosshair as Swords } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function AdminDisputes() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(null);   // {disputeKey, winnerId, note} during submit
  const [winnerChoice, setWinnerChoice] = useState({});   // {disputeKey: winner_user_id | 'void'}
  const [notes, setNotes] = useState({});             // {disputeKey: text}

  useEffect(() => {
    if (user && user.role !== 'admin') {
      toast.error('Admin access only');
      navigate('/dashboard');
      return;
    }
    if (user) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/admin/disputes`, { withCredentials: true });
      setDisputes(data);
    } catch (e) {
      toast.error('Failed to load disputes');
    } finally { setLoading(false); }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const disputeKey = (d) => `${d.kind}:${d.id}`;

  const resolve = async (d) => {
    const key = disputeKey(d);
    const choice = winnerChoice[key];
    if (!choice) { toast.error('Choose a winner or VOID'); return; }
    setResolving(key);
    try {
      await axios.post(`${API}/admin/disputes/resolve`, {
        kind: d.kind,
        id: d.id,
        competition_id: d.competition_id,
        winner_user_id: choice === 'void' ? null : choice,
        note: notes[key]?.trim() || null,
      }, { withCredentials: true });
      toast.success(choice === 'void' ? 'Voided — stakes refunded' : 'Pot transferred to winner');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to resolve');
    } finally { setResolving(null); }
  };

  return (
    <div className="min-h-screen">
      <TopNav />

      <div className="max-w-6xl mx-auto p-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-black tracking-tighter mb-1 flex items-center gap-3" style={{fontFamily:'Chivo'}}>
              <Warning size={32} weight="duotone" className="text-[#F59E0B]" /> DISPUTE QUEUE
            </h2>
            <p className="text-sm text-[#A3A3A3]">Active escalations — tournaments and head-to-head matches awaiting your judgment</p>
          </div>
          <button onClick={load} className="text-xs font-bold text-[#A3A3A3] hover:text-white" data-testid="refresh-disputes">⟳ REFRESH</button>
        </div>

        {loading ? (
          <p className="text-[#A3A3A3]">Loading disputes...</p>
        ) : disputes.length === 0 ? (
          <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-disputes">
            <CheckCircle size={64} weight="duotone" className="text-[#22C55E] mx-auto mb-4" />
            <p className="text-white font-bold mb-1">All clear.</p>
            <p className="text-sm text-[#A3A3A3]">No open disputes right now.</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="disputes-list">
            {disputes.map(d => {
              const key = disputeKey(d);
              const adv = d.latency_advantage;
              const advantageUser = adv?.advantage_user_id ? d.participants.find(p => p.user_id === adv.advantage_user_id) : null;
              const kindLabel = d.kind === 'tournament' ? 'TOURNAMENT' : 'HEAD-TO-HEAD MATCH';
              const KindIcon = d.kind === 'tournament' ? Trophy : Swords;
              return (
                <div key={key} className="border border-[#F59E0B] bg-[#141414] p-6" data-testid={`dispute-${key}`}>
                  <div className="flex flex-wrap items-start gap-4 mb-4">
                    <div className="flex-1 min-w-[280px]">
                      <div className="flex items-center gap-2 mb-1">
                        <KindIcon size={18} weight="duotone" className="text-[#F59E0B]" />
                        <span className="text-xs font-bold uppercase tracking-[0.1em] text-[#F59E0B]">{kindLabel}</span>
                      </div>
                      <p className="text-lg font-bold text-white">{d.game_name} <span className="text-[#007AFF] text-sm ml-1">{d.platform}</span></p>
                      <p className="text-xs text-[#A3A3A3]">Ref: {d.id}{d.competition_id ? ` (comp ${d.competition_id})` : ''}</p>
                      <p className="text-xs text-[#A3A3A3]">{(d.disputed_at || d.resolved_at || d.created_at || '').slice(0, 19).replace('T', ' ')} UTC</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">POT</p>
                      <p className="text-3xl font-black tracking-tighter text-white" style={{fontFamily:'Chivo'}}>{d.stake_amount} CR</p>
                    </div>
                  </div>

                  {/* Participants and their claims */}
                  <div className="border border-[#262626] bg-[#0A0A0A] p-4 mb-4">
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-3">PARTICIPANTS &amp; CLAIMS</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {d.participants.map(p => {
                        const claimsWinner = d.kind === 'tournament' ? p.claimed_winner_id : null;
                        const claimedName = claimsWinner === p.user_id ? 'themselves' : (
                          d.participants.find(x => x.user_id === claimsWinner)?.username || null
                        );
                        return (
                          <div key={p.user_id} className="border border-[#262626] bg-[#141414] p-3">
                            <p className="text-sm font-bold text-white">{p.username}</p>
                            <p className="text-xs text-[#A3A3A3] truncate">{p.email || 'no email'}</p>
                            {d.kind === 'tournament' ? (
                              <p className="text-xs mt-1 text-[#A3A3A3]">
                                Claim: {claimsWinner ? <span className="text-white font-bold">{claimedName} won</span> : <span className="text-[#A3A3A3]">no claim submitted</span>}
                              </p>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                    {d.kind === 'competition_match' && (
                      <p className="text-sm text-[#A3A3A3] mt-3">
                        <span className="text-white font-bold">{d.logged_by_username}</span> claimed{' '}
                        <span className="text-white font-bold">{d.claimed_winner_username}</span> won.
                        The opponent rejected the claim. {d.notes ? <em className="text-[#A3A3A3]">"{d.notes}"</em> : ''}
                      </p>
                    )}
                  </div>

                  {/* Latency tie-breaker */}
                  {adv && adv.breakdown && adv.breakdown.length > 0 && (
                    <div className="border border-[#262626] bg-[#0A0A0A] p-4 mb-4" data-testid={`latency-${key}`}>
                      <div className="flex items-center gap-2 mb-3">
                        <Gauge size={16} weight="duotone" className="text-[#007AFF]" />
                        <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">LATENCY TIE-BREAKER</p>
                      </div>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-xs font-bold uppercase tracking-[0.05em] text-[#A3A3A3]">
                            <th className="text-left pb-2">Player</th>
                            <th className="text-right pb-2">Avg</th>
                            <th className="text-right pb-2">Max</th>
                            <th className="text-right pb-2">Samples</th>
                            <th className="text-right pb-2">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {adv.breakdown.map(b => (
                            <tr key={b.user_id} className="border-t border-[#262626]">
                              <td className="py-2 text-white font-bold">
                                {b.username}{b.user_id === adv.advantage_user_id && <span className="ml-2 text-[10px] text-[#22C55E] font-bold">✓ ADVANTAGE</span>}
                              </td>
                              <td className="py-2 text-right text-white">{b.avg_ms} ms</td>
                              <td className="py-2 text-right text-[#A3A3A3]">{b.max_ms} ms</td>
                              <td className="py-2 text-right text-[#A3A3A3]">{b.sample_count}</td>
                              <td className="py-2 text-right">
                                <span className={`text-xs font-bold ${b.status==='ok'?'text-[#22C55E]':b.status==='warn'?'text-[#F59E0B]':'text-[#EF4444]'}`}>
                                  {b.status.toUpperCase()}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {advantageUser && (
                        <p className="text-xs text-[#22C55E] mt-3">
                          Latency suggests <strong>{advantageUser.username}</strong> deserves the tie-break (lower-latency connection).
                        </p>
                      )}
                    </div>
                  )}

                  {/* Resolution form */}
                  <div className="border border-[#262626] bg-[#0A0A0A] p-4">
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-3">RESOLUTION</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 mb-3">
                      {d.participants.map(p => (
                        <button
                          key={p.user_id}
                          data-testid={`pick-winner-${key}-${p.user_id}`}
                          onClick={() => setWinnerChoice({ ...winnerChoice, [key]: p.user_id })}
                          className={`px-3 py-2 text-sm font-bold border transition-colors ${winnerChoice[key] === p.user_id ? 'bg-[#22C55E] border-[#22C55E] text-white' : 'bg-transparent border-[#3F3F3F] text-[#A3A3A3] hover:text-white'}`}
                        >
                          AWARD TO {p.username.toUpperCase()}
                        </button>
                      ))}
                      <button
                        data-testid={`pick-void-${key}`}
                        onClick={() => setWinnerChoice({ ...winnerChoice, [key]: 'void' })}
                        className={`px-3 py-2 text-sm font-bold border transition-colors ${winnerChoice[key] === 'void' ? 'bg-[#EF4444] border-[#EF4444] text-white' : 'bg-transparent border-[#3F3F3F] text-[#A3A3A3] hover:text-white'}`}
                      >
                        VOID (refund all)
                      </button>
                    </div>
                    <input
                      data-testid={`admin-note-${key}`}
                      type="text"
                      placeholder="Optional resolution note (visible in audit log only)"
                      maxLength={500}
                      value={notes[key] || ''}
                      onChange={(e) => setNotes({ ...notes, [key]: e.target.value })}
                      className="w-full px-3 py-2 bg-[#141414] border border-[#262626] text-white text-sm focus:outline-none focus:border-[#FF3B30] mb-3"
                    />
                    <button
                      data-testid={`resolve-${key}`}
                      disabled={resolving === key || !winnerChoice[key]}
                      onClick={() => resolve(d)}
                      className="w-full px-4 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50"
                    >
                      {resolving === key ? 'RESOLVING...' : winnerChoice[key] === 'void' ? 'CONFIRM VOID & REFUND' : 'CONFIRM RESOLUTION'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminDisputes;
