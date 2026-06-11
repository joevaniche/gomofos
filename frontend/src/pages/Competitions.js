import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import Logo from '../components/Logo';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, Crosshair as Swords, Plus, Trophy, X } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Competitions() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [competitions, setCompetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/competitions`, { withCredentials: true });
      setCompetitions(data);
    } catch { toast.error('Failed to load competitions'); }
    finally { setLoading(false); }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  return (
    <div className="min-h-screen">
      <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/tournaments" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-tournaments">TOURNAMENTS</Link>
            <Link to="/competitions" className="text-sm font-bold text-[#FF3B30]" data-testid="nav-competitions">COMPETITIONS</Link>
            <Link to="/prizes" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-prizes">PRIZES</Link>
            <Link to="/players" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-players">PLAYERS</Link>
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-leaderboard">LEADERBOARD</Link>
            <Link to="/profile" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-profile">PROFILE</Link>
            <Link to="/wallet" className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-wallet">
              <Coins size={18} weight="bold" />{user?.wallet_balance?.toFixed(0) || '0'} CR
            </Link>
            <button onClick={handleLogout} className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-logout">
              <SignOut size={18} weight="bold" />LOGOUT
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
          <div>
            <h2 className="text-3xl font-black tracking-tighter mb-2" style={{fontFamily: 'Chivo'}}>HEAD-TO-HEAD</h2>
            <p className="text-sm text-[#A3A3A3]">Persistent rivalries — track every win vs the same opponent</p>
          </div>
          <button data-testid="new-competition-btn" onClick={() => setShowCreate(true)}
            className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2">
            <Plus size={20} weight="bold" />NEW COMPETITION
          </button>
        </div>

        {loading ? (
          <p className="text-[#A3A3A3]">Loading...</p>
        ) : competitions.length === 0 ? (
          <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-competitions">
            <Swords size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
            <p className="text-[#A3A3A3] mb-4">No competitions yet. Start a rivalry with someone.</p>
            <button onClick={() => setShowCreate(true)} className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors">
              CREATE FIRST COMPETITION
            </button>
          </div>
        ) : (
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm overflow-x-auto" data-testid="competitions-table">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#262626] text-left text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">
                  <th className="px-4 py-3">Opponent</th>
                  <th className="px-4 py-3">Game</th>
                  <th className="px-4 py-3">Platform</th>
                  <th className="px-4 py-3 text-center">W &mdash; L</th>
                  <th className="px-4 py-3 text-right">Credits Won</th>
                </tr>
              </thead>
              <tbody>
                {competitions.map(c => {
                  const isA = c.player_a_id === user.id;
                  const myWins = isA ? c.wins_a : c.wins_b;
                  const oppWins = isA ? c.wins_b : c.wins_a;
                  const oppName = isA ? c.player_b_username : c.player_a_username;
                  // Net credits won = (wins - losses) * stake_per_match (each confirmed match swings the pot)
                  const netCredits = (myWins - oppWins) * c.stake_per_match;
                  const netColor = netCredits > 0 ? 'text-[#22C55E]' : netCredits < 0 ? 'text-[#EF4444]' : 'text-[#A3A3A3]';
                  const netPrefix = netCredits > 0 ? '+' : '';
                  return (
                    <tr key={c.id} data-testid={`competition-row-${c.id}`}
                      className="border-b border-[#262626] hover:bg-[#1A1A1A]/60 transition-colors cursor-pointer"
                      onClick={() => navigate(`/competition/${c.id}`)}>
                      <td className="px-4 py-4 text-white font-bold">{oppName}</td>
                      <td className="px-4 py-4 text-[#A3A3A3]">{c.game_name}</td>
                      <td className="px-4 py-4 text-[#007AFF] font-bold">{c.platform}</td>
                      <td className="px-4 py-4 text-center">
                        <span className="text-xl font-black tracking-tighter text-white" style={{fontFamily:'Chivo'}}>{myWins}</span>
                        <span className="text-[#A3A3A3] mx-2">&mdash;</span>
                        <span className="text-xl font-black tracking-tighter text-[#A3A3A3]" style={{fontFamily:'Chivo'}}>{oppWins}</span>
                      </td>
                      <td className={`px-4 py-4 text-right font-black tracking-tighter ${netColor}`} style={{fontFamily:'Chivo'}}>
                        {netPrefix}{netCredits} CR
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {showCreate && <CreateCompetitionModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />}
      </div>
    </div>
  );
}

function CreateCompetitionModal({ onClose, onCreated }) {
  const [games, setGames] = useState([]);
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState('');
  const [opponentId, setOpponentId] = useState('');
  const [gameId, setGameId] = useState('');
  const [platform, setPlatform] = useState('');
  const [stake, setStake] = useState('10');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    axios.get(`${API}/games`, { withCredentials: true }).then(({ data }) => {
      setGames(data);
      if (data.length > 0) {
        setGameId(data[0].id);
        const ps = (data[0].platform || '').split(',').map(s=>s.trim()).filter(Boolean);
        setPlatform(ps[0] || '');
      }
    });
  }, []);

  useEffect(() => {
    const id = setTimeout(async () => {
      if (search.trim().length < 1) { setPlayers([]); return; }
      try {
        const { data } = await axios.get(`${API}/users/search`, { params: { q: search.trim() }, withCredentials: true });
        setPlayers(data);
      } catch (e) { /* search failed */ }
    }, 250);
    return () => clearTimeout(id);
  }, [search]);

  const selectedGame = games.find(g => g.id === gameId);
  const platformOptions = selectedGame ? (selectedGame.platform || '').split(',').map(p=>p.trim()).filter(Boolean) : [];

  const submit = async () => {
    if (!opponentId) { toast.error('Pick an opponent'); return; }
    if (!gameId) { toast.error('Pick a game'); return; }
    if (!platform) { toast.error('Pick a platform'); return; }
    const s = parseFloat(stake);
    if (!s || s <= 0) { toast.error('Stake must be > 0'); return; }
    setSubmitting(true);
    try {
      await axios.post(`${API}/competitions`, {
        opponent_user_id: opponentId,
        game_id: gameId,
        platform,
        stake_per_match: s,
      }, { withCredentials: true });
      toast.success('Competition created');
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create');
    } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="create-competition-modal">
      <div className="bg-[#141414] border border-[#262626] max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e=>e.stopPropagation()}>
        <div className="flex items-center justify-between p-6 border-b border-[#262626]">
          <h3 className="text-xl font-bold" style={{fontFamily:'Chivo'}}>NEW COMPETITION</h3>
          <button onClick={onClose} className="text-[#A3A3A3] hover:text-white"><X size={24} weight="bold" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">OPPONENT</label>
            <input data-testid="competition-opponent-search" type="text" value={search} onChange={(e)=>setSearch(e.target.value)}
              placeholder="Type a username..."
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
            {players.length > 0 && (
              <div className="mt-2 max-h-40 overflow-y-auto border border-[#262626]">
                {players.map(p => (
                  <button key={p.id} type="button" data-testid={`opponent-option-${p.id}`}
                    onClick={() => { setOpponentId(p.id); setSearch(p.username); setPlayers([]); }}
                    className="block w-full text-left px-3 py-2 text-sm text-white hover:bg-[#1A1A1A]">
                    {p.username}
                  </button>
                ))}
              </div>
            )}
            {opponentId && <p className="text-xs text-[#22C55E] mt-1">✓ Opponent locked in</p>}
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">GAME</label>
            <select data-testid="competition-game-select" value={gameId} onChange={e => {
              setGameId(e.target.value);
              const g = games.find(x => x.id === e.target.value);
              const ps = g ? (g.platform || '').split(',').map(s=>s.trim()).filter(Boolean) : [];
              setPlatform(ps[0] || '');
            }} className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]">
              {games.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">PLATFORM</label>
            {platformOptions.length > 1 ? (
              <select data-testid="competition-platform-select" value={platform} onChange={e=>setPlatform(e.target.value)}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]">
                {platformOptions.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            ) : (
              <input data-testid="competition-platform-input" type="text" value={platform} onChange={e=>setPlatform(e.target.value)}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
            )}
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">STAKE PER MATCH (CR)</label>
            <input data-testid="competition-stake-input" type="number" min="1" value={stake} onChange={e=>setStake(e.target.value)}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
            <p className="text-xs text-[#A3A3A3] mt-1">Both players risk this each match. Money moves only when the loser confirms the result.</p>
          </div>
          <div className="flex gap-3 pt-2">
            <button data-testid="confirm-create-competition" disabled={submitting} onClick={submit}
              className="flex-1 px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50">
              {submitting ? 'CREATING...' : 'CREATE'}
            </button>
            <button onClick={onClose} className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">
              CANCEL
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Competitions;
