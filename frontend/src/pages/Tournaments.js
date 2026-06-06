import React, { useEffect, useState } from 'react';
import Logo from '../components/Logo';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, GameController, Trophy, MagnifyingGlass, Funnel, Plus } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Tournaments() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [tournaments, setTournaments] = useState([]);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [joiningId, setJoiningId] = useState(null);
  const [filters, setFilters] = useState({ game_id: '', platform: '', min_stake: '', max_stake: '' });

  useEffect(() => {
    loadGames();
    loadTournaments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadTournaments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const loadGames = async () => {
    try {
      const { data } = await axios.get(`${API}/games`, { withCredentials: true });
      setGames(data);
    } catch (e) { /* ignore */ }
  };

  const loadTournaments = async () => {
    setLoading(true);
    try {
      const params = { status: 'open' };
      if (filters.game_id) params.game_id = filters.game_id;
      if (filters.platform) params.platform = filters.platform;
      if (filters.min_stake) params.min_stake = parseFloat(filters.min_stake);
      if (filters.max_stake) params.max_stake = parseFloat(filters.max_stake);
      const { data } = await axios.get(`${API}/tournaments`, { params, withCredentials: true });
      setTournaments(data);
    } catch (e) {
      toast.error('Failed to load tournaments');
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async (t) => {
    if (user?.wallet_balance < t.stake_amount) {
      toast.error(`Need ${t.stake_amount} CR to join — you have ${user?.wallet_balance?.toFixed(0) || 0}`);
      return;
    }
    setJoiningId(t.id);
    try {
      await axios.post(`${API}/tournaments/${t.id}/join`, {}, { withCredentials: true });
      toast.success('Joined tournament!');
      navigate(`/tournament/${t.id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to join');
    } finally {
      setJoiningId(null);
    }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  // Build distinct platform options from current catalog (split games' platforms by comma)
  const platformOptions = Array.from(new Set(
    games.flatMap(g => (g.platform || '').split(',').map(p => p.trim()).filter(Boolean))
  )).sort();

  const clearFilters = () => setFilters({ game_id: '', platform: '', min_stake: '', max_stake: '' });
  const anyFilter = filters.game_id || filters.platform || filters.min_stake || filters.max_stake;

  return (
    <div className="min-h-screen">
      <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/tournaments" className="text-sm font-bold text-[#FF3B30]" data-testid="nav-tournaments">TOURNAMENTS</Link>
            <Link to="/competitions" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-competitions">COMPETITIONS</Link>
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
            <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>OPEN TOURNAMENTS</h2>
            <p className="text-sm text-[#A3A3A3]">Find a match and stake your skill</p>
          </div>
          <button data-testid="create-tournament-btn" onClick={() => navigate('/create-tournament')}
            className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2">
            <Plus size={20} weight="bold" />CREATE TOURNAMENT
          </button>
        </div>

        {/* Filters */}
        <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-4 mb-6" data-testid="tournament-filters">
          <div className="flex items-center gap-2 mb-3">
            <Funnel size={16} weight="bold" className="text-[#A3A3A3]" />
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">FILTERS</p>
            {anyFilter && (
              <button onClick={clearFilters} className="text-xs text-[#FF3B30] font-bold ml-auto" data-testid="clear-filters">CLEAR</button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <select data-testid="filter-game" value={filters.game_id} onChange={(e) => setFilters({...filters, game_id: e.target.value})}
              className="px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white text-sm focus:outline-none focus:border-[#FF3B30]">
              <option value="">All games</option>
              {games.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
            <select data-testid="filter-platform" value={filters.platform} onChange={(e) => setFilters({...filters, platform: e.target.value})}
              className="px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white text-sm focus:outline-none focus:border-[#FF3B30]">
              <option value="">All platforms</option>
              {platformOptions.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <input data-testid="filter-min-stake" type="number" min="0" placeholder="Min stake (CR)" value={filters.min_stake}
              onChange={(e) => setFilters({...filters, min_stake: e.target.value})}
              className="px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white text-sm focus:outline-none focus:border-[#FF3B30]" />
            <input data-testid="filter-max-stake" type="number" min="0" placeholder="Max stake (CR)" value={filters.max_stake}
              onChange={(e) => setFilters({...filters, max_stake: e.target.value})}
              className="px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white text-sm focus:outline-none focus:border-[#FF3B30]" />
          </div>
        </div>

        <p className="text-sm text-[#A3A3A3] mb-4">{tournaments.length} open tournament{tournaments.length !== 1 ? 's' : ''}</p>

        {loading ? (
          <p className="text-[#A3A3A3]">Loading tournaments...</p>
        ) : tournaments.length === 0 ? (
          <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-tournaments">
            <Trophy size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
            <p className="text-[#A3A3A3] mb-4">No open tournaments match your filters.</p>
            <button onClick={() => navigate('/create-tournament')} className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors">
              CREATE ONE
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="tournaments-grid">
            {tournaments.map(t => {
              const isCreator = t.creator_id === user?.id;
              const isFull = t.current_players >= t.max_players;
              const canJoin = !isCreator && !isFull;
              return (
                <div key={t.id} className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm hover:border-[#3F3F3F] transition-colors"
                  data-testid={`tournament-card-${t.id}`}>
                  <div className="p-6 cursor-pointer" onClick={() => navigate(`/tournament/${t.id}`)}>
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">{t.game_name}</p>
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#007AFF] mb-3">{t.platform}</p>
                    <h4 className="text-2xl font-black tracking-tighter mb-4" style={{fontFamily: 'Chivo'}}>{t.stake_amount} CR</h4>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-[#A3A3A3] flex items-center gap-1"><GameController size={14} weight="bold" />{t.current_players}/{t.max_players}</span>
                      <span className={`font-bold ${isFull ? 'text-[#A3A3A3]' : 'text-[#22C55E]'}`}>{isFull ? 'FULL' : 'OPEN'}</span>
                    </div>
                    <p className="text-xs text-[#A3A3A3]">Host: {t.creator_username}</p>
                    <p className="text-xs text-[#A3A3A3]">Starts: {new Date(t.start_time).toLocaleString()}</p>
                  </div>
                  <div className="border-t border-[#262626] p-3 flex gap-2">
                    {canJoin ? (
                      <button data-testid={`join-tournament-${t.id}`} disabled={joiningId === t.id} onClick={() => handleJoin(t)}
                        className="flex-1 px-4 py-2 bg-[#FF3B30] text-white font-bold text-sm hover:bg-[#D62F26] transition-colors disabled:opacity-50">
                        {joiningId === t.id ? 'JOINING...' : `JOIN (${t.stake_amount} CR)`}
                      </button>
                    ) : (
                      <button onClick={() => navigate(`/tournament/${t.id}`)}
                        className="flex-1 px-4 py-2 bg-transparent border border-[#3F3F3F] text-white font-bold text-sm hover:border-[#FF3B30] hover:text-[#FF3B30] transition-all">
                        {isCreator ? 'YOUR TOURNAMENT' : 'VIEW'}
                      </button>
                    )}
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

export default Tournaments;
