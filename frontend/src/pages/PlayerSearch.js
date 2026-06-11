import React, { useEffect, useState, useCallback } from 'react';
import Logo from '../components/Logo';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, MagnifyingGlass, User, MapPin, Trophy, CircleDashed, Circle } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PLATFORM_LABELS = {
  ps5: 'PS5', ps4: 'PS4', xbox_series: 'Xbox Series X/S', xbox_one: 'Xbox One',
  pc: 'PC', switch: 'Switch', mobile: 'Mobile',
};

function PlayerSearch() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [players, setPlayers] = useState([]);
  const [countries, setCountries] = useState([]);
  const [platformsList, setPlatformsList] = useState([]);
  const [games, setGames] = useState([]);
  const [filters, setFilters] = useState({
    q: '', game_id: '', country: '', platform: '',
    stake_min: '', stake_max: '', min_wins: '', online_only: false,
  });

  useEffect(() => {
    loadFilters();
    runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadFilters = async () => {
    try {
      const [c, p, g] = await Promise.all([
        axios.get(`${API}/countries`, { withCredentials: true }),
        axios.get(`${API}/platforms-list`, { withCredentials: true }),
        axios.get(`${API}/games`, { withCredentials: true }),
      ]);
      setCountries(c.data);
      setPlatformsList(p.data);
      setGames(g.data);
    } catch (e) { /* ignore */ }
  };

  const runSearch = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== '' && v !== false && v !== null) params[k] = v;
      });
      const { data } = await axios.get(`${API}/users/search`, { params, withCredentials: true });
      setPlayers(data);
    } catch (e) {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const handleSubmit = (e) => { e.preventDefault(); runSearch(); };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const flagEmoji = (code) => {
    if (!code || code === 'OTHER' || code.length !== 2) return '🌐';
    return code.toUpperCase().replace(/./g, c => String.fromCodePoint(127397 + c.charCodeAt()));
  };

  return (
    <div className="min-h-screen">
      <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/tournaments" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-tournaments">TOURNAMENTS</Link>
            <Link to="/competitions" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-competitions">COMPETITIONS</Link>
            <Link to="/prizes" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-prizes">PRIZES</Link>
            <Link to="/players" className="text-sm font-bold text-[#FF3B30]" data-testid="nav-players">PLAYERS</Link>
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-leaderboard">LEADERBOARD</Link>
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
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>FIND PLAYERS</h2>
          <p className="text-sm text-[#A3A3A3]">Browse and challenge competitors from around the world</p>
        </div>

        {/* Filters */}
        <form onSubmit={handleSubmit} className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6" data-testid="search-filters">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-4">
            <div className="lg:col-span-2">
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">SEARCH</label>
              <input data-testid="q-input" type="text" value={filters.q} onChange={(e) => setFilters({...filters, q: e.target.value})}
                placeholder="Username or bio..."
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">GAME</label>
              <select data-testid="game-filter" value={filters.game_id} onChange={(e) => setFilters({...filters, game_id: e.target.value})}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]">
                <option value="">All games</option>
                {games.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">COUNTRY</label>
              <select data-testid="country-filter" value={filters.country} onChange={(e) => setFilters({...filters, country: e.target.value})}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]">
                <option value="">All countries</option>
                {countries.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">PLATFORM</label>
              <select data-testid="platform-filter" value={filters.platform} onChange={(e) => setFilters({...filters, platform: e.target.value})}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]">
                <option value="">All platforms</option>
                {platformsList.map(p => <option key={p.code} value={p.code}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">STAKE MIN (CR)</label>
              <input data-testid="stake-min-filter" type="number" min="0" value={filters.stake_min} onChange={(e) => setFilters({...filters, stake_min: e.target.value})}
                placeholder="0"
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">STAKE MAX (CR)</label>
              <input data-testid="stake-max-filter" type="number" min="0" value={filters.stake_max} onChange={(e) => setFilters({...filters, stake_max: e.target.value})}
                placeholder="∞"
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">MIN WINS</label>
              <input data-testid="min-wins-filter" type="number" min="0" value={filters.min_wins} onChange={(e) => setFilters({...filters, min_wins: e.target.value})}
                placeholder="0"
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer" data-testid="online-filter">
              <input type="checkbox" checked={filters.online_only} onChange={(e) => setFilters({...filters, online_only: e.target.checked})}
                className="w-4 h-4 accent-[#FF3B30]" />
              <span className="text-sm text-white font-bold">ONLINE NOW (last 10 mins)</span>
            </label>
            <div className="ml-auto flex gap-2">
              <button type="button" onClick={() => setFilters({q: '', game_id: '', country: '', platform: '', stake_min: '', stake_max: '', min_wins: '', online_only: false})}
                className="px-4 py-2 bg-transparent border border-[#3F3F3F] text-[#A3A3A3] hover:text-white text-sm font-bold transition-all">
                RESET
              </button>
              <button data-testid="search-btn" type="submit" disabled={loading}
                className="px-6 py-2 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50 flex items-center gap-2">
                <MagnifyingGlass size={18} weight="bold" />
                {loading ? 'SEARCHING...' : 'SEARCH'}
              </button>
            </div>
          </div>
        </form>

        {/* Results */}
        <div data-testid="search-results">
          <p className="text-sm text-[#A3A3A3] mb-4">{players.length} player{players.length !== 1 ? 's' : ''} found</p>
          {players.length === 0 ? (
            <div className="border border-[#262626] p-12 text-center bg-[#141414]">
              <User size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
              <p className="text-[#A3A3A3]">No players match your filters. Try broadening your search.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {players.map(p => (
                <div key={p.id} onClick={() => navigate(`/profile/${p.id}`)}
                  className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-5 hover:border-[#3F3F3F] transition-all cursor-pointer"
                  data-testid={`player-card-${p.id}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-[#0A0A0A] border border-[#262626] flex items-center justify-center">
                        <User size={24} weight="duotone" className="text-[#FF3B30]" />
                      </div>
                      <div>
                        <h4 className="font-bold text-white" style={{fontFamily: 'Chivo'}}>{p.username}</h4>
                        <p className="text-xs text-[#A3A3A3] flex items-center gap-1">
                          {p.is_online ? <Circle size={8} weight="fill" className="text-[#22C55E]" /> : <CircleDashed size={8} weight="bold" className="text-[#525252]" />}
                          {p.is_online ? 'Online' : 'Offline'}
                        </p>
                      </div>
                    </div>
                    {p.country && (
                      <div className="text-right">
                        <p className="text-lg">{flagEmoji(p.country)}</p>
                        <p className="text-xs text-[#A3A3A3]">{p.city || p.country}</p>
                      </div>
                    )}
                  </div>

                  {p.bio && <p className="text-xs text-[#A3A3A3] mb-3 line-clamp-2">{p.bio}</p>}

                  <div className="grid grid-cols-3 gap-2 text-center mb-3 pb-3 border-b border-[#262626]">
                    <div>
                      <p className="text-xs text-[#A3A3A3]">WINS</p>
                      <p className="text-sm font-bold text-[#22C55E]">{p.total_wins}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#A3A3A3]">LOSSES</p>
                      <p className="text-sm font-bold text-[#EF4444]">{p.total_losses}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#A3A3A3]">W/L</p>
                      <p className="text-sm font-bold text-white">
                        {(p.total_wins + p.total_losses) > 0 ? Math.round(p.total_wins / (p.total_wins + p.total_losses) * 100) : 0}%
                      </p>
                    </div>
                  </div>

                  {p.platforms?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {p.platforms.slice(0, 4).map(pl => (
                        <span key={pl} className="text-xs px-2 py-1 bg-[#0A0A0A] border border-[#262626] text-[#A3A3A3]">{PLATFORM_LABELS[pl] || pl}</span>
                      ))}
                    </div>
                  )}

                  {(p.stake_min || p.stake_max) && (
                    <p className="text-xs text-[#A3A3A3]">
                      <Coins size={12} weight="bold" className="inline mr-1 text-[#F59E0B]" />
                      Stakes {p.stake_min || 0}-{p.stake_max || '∞'} CR
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlayerSearch;
