import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import TopNav from '../components/TopNav';
import axios from 'axios';
import Logo from '../components/Logo';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, Crosshair as Swords, ArrowLeft, CheckCircle, XCircle } from '@phosphor-icons/react';
import { toast } from 'sonner';
import useLatencyPing from '../hooks/useLatencyPing';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function CompetitionDetails() {
  const { id } = useParams();
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [comp, setComp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [logging, setLogging] = useState(false);
  const [winner, setWinner] = useState('me');
  const [notes, setNotes] = useState('');

  useEffect(() => { load(); }, [id]);

  // Continuous 60-sec latency ping for active head-to-head matches. The hook is
  // safe to call before `comp` loads — it just won't fire until `active=true`.
  const _pendingMatch = comp?.matches?.find(m => m.status === 'pending_confirmation');
  const _isPlayer = comp ? (comp.player_a_id === user?.id || comp.player_b_id === user?.id) : false;
  useLatencyPing({
    competition_id: id,
    match_id: _pendingMatch?.id,
    active: !!(comp && comp.status === 'active' && _isPlayer),
  });

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/competitions/${id}`, { withCredentials: true });
      setComp(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load competition');
      navigate('/competitions');
    } finally { setLoading(false); }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  if (loading || !comp) return <div className="min-h-screen flex items-center justify-center text-[#A3A3A3]">Loading...</div>;

  const isA = comp.player_a_id === user.id;
  const meName = isA ? comp.player_a_username : comp.player_b_username;
  const oppName = isA ? comp.player_b_username : comp.player_a_username;
  const oppId = isA ? comp.player_b_id : comp.player_a_id;
  const myWins = isA ? comp.wins_a : comp.wins_b;
  const oppWins = isA ? comp.wins_b : comp.wins_a;

  const pending = comp.matches.find(m => m.status === 'pending_confirmation');
  const myPending = pending && pending.logged_by_id === user.id;
  const oppPending = pending && pending.logged_by_id !== user.id;

  const submitLog = async () => {
    setLogging(true);
    try {
      await axios.post(`${API}/competitions/${id}/log-match`, {
        winner_user_id: winner === 'me' ? user.id : oppId,
        notes: notes.trim() || undefined,
      }, { withCredentials: true });
      toast.success('Match logged — waiting for opponent to confirm');
      setNotes('');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to log match');
    } finally { setLogging(false); }
  };

  const confirmMatch = async (matchId) => {
    try {
      await axios.post(`${API}/competitions/${id}/matches/${matchId}/confirm`, {}, { withCredentials: true });
      toast.success('Match confirmed — pot transferred');
      await checkAuth();   // refresh wallet balance
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to confirm');
    }
  };

  const disputeMatch = async (matchId) => {
    if (!window.confirm('Reject this match result?\n\nNo money will move and the match will be cancelled. The dispute will be forwarded to admin for review.\n\nIMPORTANT: if you dispute 66% or more of your matches, your account will be auto-suspended for review. Are you sure?')) return;
    try {
      const { data } = await axios.post(`${API}/competitions/${id}/matches/${matchId}/dispute`, {}, { withCredentials: true });
      toast.success('Match cancelled — admin notified');
      if (data?.dispute_threshold_warning) {
        toast.warning(`Reminder: accounts above ${data.hold_threshold_pct || 66}% dispute rate are auto-suspended.`);
      }
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to dispute');
    }
  };

  return (
    <div className="min-h-screen">
      <TopNav />

      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <Link to="/competitions" className="text-sm text-[#A3A3A3] hover:text-white flex items-center gap-1" data-testid="back-to-competitions">
            <ArrowLeft size={16} weight="bold" /> All competitions
          </Link>
          {user?.role === 'admin' && (
            <button data-testid="admin-delete-competition-btn"
              onClick={async () => {
                if (!window.confirm('Hard-delete this competition and ALL its matches? Cannot be undone.')) return;
                try {
                  await axios.delete(`${API}/admin/competitions/${id}`, { withCredentials: true });
                  toast.success('Competition deleted');
                  navigate('/competitions');
                } catch (e) { toast.error(e.response?.data?.detail || 'Delete failed'); }
              }}
              className="px-3 py-1.5 text-xs font-bold border border-[#EF4444] text-[#EF4444] hover:bg-[#EF4444] hover:text-white transition-colors">
              ADMIN: DELETE COMPETITION
            </button>
          )}
        </div>

        {/* Scoreboard */}
        <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-8 mb-6" data-testid="competition-scoreboard">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">{comp.game_name}</p>
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#007AFF]">{comp.platform}</p>
          </div>
          <p className="text-xs text-[#A3A3A3] mb-6">{comp.stake_per_match} CR per match · {comp.total_matches} matches played</p>
          <div className="flex items-center justify-center gap-6 mb-4">
            <div className="text-center flex-1">
              <p className="text-sm font-bold text-white truncate" data-testid="me-name">{meName} (YOU)</p>
              <p className="text-7xl font-black tracking-tighter mt-2" style={{fontFamily:'Chivo'}} data-testid="my-wins">{myWins}</p>
            </div>
            <Swords size={48} weight="duotone" className="text-[#FF3B30]" />
            <div className="text-center flex-1">
              <p className="text-sm font-bold text-white truncate" data-testid="opp-name">{oppName}</p>
              <p className="text-7xl font-black tracking-tighter text-[#A3A3A3] mt-2" style={{fontFamily:'Chivo'}} data-testid="opp-wins">{oppWins}</p>
            </div>
          </div>
        </div>

        {/* Pending match callout */}
        {oppPending && (
          <div className="border border-[#F59E0B] bg-[#F59E0B]/10 p-6 mb-6" data-testid="awaiting-my-confirmation">
            <p className="text-sm font-bold text-[#F59E0B] mb-3">⏳ AWAITING YOUR CONFIRMATION</p>
            <p className="text-white mb-1">{oppName} claims <span className="font-bold">{pending.winner_user_id === user.id ? 'YOU' : oppName}</span> won the last match.</p>
            {pending.notes && <p className="text-sm text-[#A3A3A3] mb-3">"{pending.notes}"</p>}
            <p className="text-xs text-[#A3A3A3] mb-3">Pot: {pending.stake_amount} CR each way</p>
            <div className="flex gap-3">
              <button data-testid="confirm-match-btn" onClick={() => confirmMatch(pending.id)}
                className="px-5 py-2 bg-[#22C55E] text-white font-bold hover:bg-[#16A34A] transition-colors flex items-center gap-2">
                <CheckCircle size={18} weight="bold" /> CONFIRM
              </button>
              <button data-testid="dispute-match-btn" onClick={() => disputeMatch(pending.id)}
                className="px-5 py-2 bg-transparent border border-[#EF4444] text-[#EF4444] font-bold hover:bg-[#EF4444] hover:text-white transition-colors flex items-center gap-2">
                <XCircle size={18} weight="bold" /> REJECT
              </button>
            </div>
          </div>
        )}
        {myPending && (
          <div className="border border-[#262626] bg-[#141414] p-6 mb-6" data-testid="awaiting-opp-confirmation">
            <p className="text-sm font-bold text-[#A3A3A3] mb-2">⏳ WAITING FOR {oppName.toUpperCase()} TO CONFIRM</p>
            <p className="text-white">You claimed <span className="font-bold">{pending.winner_user_id === user.id ? 'YOURSELF' : oppName}</span> won. Pot: {pending.stake_amount} CR.</p>
          </div>
        )}

        {/* Log new match (only if no pending) */}
        {!pending && (
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6" data-testid="log-match-form">
            <h3 className="text-xl font-bold mb-4" style={{fontFamily:'Chivo'}}>LOG A MATCH RESULT</h3>
            <p className="text-xs text-[#A3A3A3] mb-4">{oppName} will need to confirm before the pot moves and your record updates.</p>
            <div className="flex gap-3 mb-3">
              <button onClick={() => setWinner('me')} data-testid="winner-me-btn"
                className={`flex-1 px-4 py-3 font-bold border ${winner==='me' ? 'bg-[#22C55E] border-[#22C55E] text-white' : 'bg-transparent border-[#3F3F3F] text-[#A3A3A3] hover:text-white'}`}>
                I WON
              </button>
              <button onClick={() => setWinner('opp')} data-testid="winner-opp-btn"
                className={`flex-1 px-4 py-3 font-bold border ${winner==='opp' ? 'bg-[#EF4444] border-[#EF4444] text-white' : 'bg-transparent border-[#3F3F3F] text-[#A3A3A3] hover:text-white'}`}>
                {oppName.toUpperCase()} WON
              </button>
            </div>
            <input data-testid="match-notes-input" type="text" value={notes} onChange={e=>setNotes(e.target.value)}
              placeholder="Optional notes (final score, lobby code, etc.)"
              maxLength={500}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30] mb-3" />
            <button data-testid="log-match-submit" disabled={logging} onClick={submitLog}
              className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50">
              {logging ? 'LOGGING...' : 'LOG MATCH'}
            </button>
          </div>
        )}

        {/* History */}
        <div>
          <h3 className="text-xl font-bold mb-4" style={{fontFamily:'Chivo'}}>MATCH HISTORY</h3>
          {comp.matches.length === 0 ? (
            <p className="text-sm text-[#A3A3A3]">No matches logged yet.</p>
          ) : (
            <div className="space-y-2" data-testid="match-history">
              {comp.matches.map(m => {
                const winnerName = m.winner_user_id === user.id ? meName : oppName;
                const isWin = m.winner_user_id === user.id;
                const statusColor = m.status === 'confirmed' ? 'text-[#22C55E]' : m.status === 'cancelled' ? 'text-[#A3A3A3]' : 'text-[#F59E0B]';
                return (
                  <div key={m.id} className="border border-[#262626] bg-[#141414] p-4 flex items-center justify-between" data-testid={`match-row-${m.id}`}>
                    <div>
                      <p className={`text-sm font-bold ${isWin ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>
                        {isWin ? 'WIN' : 'LOSS'} · {winnerName} won
                      </p>
                      <p className="text-xs text-[#A3A3A3]">{new Date(m.created_at).toLocaleString()}{m.notes ? ` · ${m.notes}` : ''}</p>
                    </div>
                    <span className={`text-xs font-bold ${statusColor}`}>
                      {m.status === 'pending_confirmation' ? 'PENDING' : m.status.toUpperCase()}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CompetitionDetails;
