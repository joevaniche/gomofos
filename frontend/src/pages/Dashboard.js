import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Trophy, GameController, Users, SignOut, Plus, Coins } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [tournaments, setTournaments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ activeTournaments: 0, totalPlayers: 0, totalStakes: 0 });

  useEffect(() => {
    loadTournaments();
  }, []);

  const loadTournaments = async () => {
    try {
      const { data } = await axios.get(`${API}/tournaments?status=open`, { withCredentials: true });
      setTournaments(data);
      
      // Calculate stats
      const activeTournaments = data.length;
      const totalPlayers = data.reduce((sum, t) => sum + t.current_players, 0);
      const totalStakes = data.reduce((sum, t) => sum + (t.stake_amount * t.current_players), 0);
      setStats({ activeTournaments, totalPlayers, totalStakes });
    } catch (e) {
      toast.error('Failed to load tournaments');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Navigation */}
      <nav className="border-b border-[#262626] bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-black tracking-tighter text-white" style={{fontFamily: 'Chivo'}}>ESPORTS BET</h1>
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#FF3B30]" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-leaderboard">LEADERBOARD</Link>
            <Link to="/wallet" className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-wallet">
              <Coins size={18} weight="bold" />
              {user?.wallet_balance?.toFixed(0) || '0'} CR
            </Link>
            <button onClick={handleLogout} className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-logout">
              <SignOut size={18} weight="bold" />
              LOGOUT
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6">
        {/* User Info */}
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>
            WELCOME, {user?.username?.toUpperCase()}
          </h2>
          <p className="text-sm text-[#A3A3A3]">Your competitive gaming dashboard</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="border border-[#262626] p-6 bg-[#141414]" data-testid="stat-active-tournaments">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">ACTIVE TOURNAMENTS</p>
              <GameController size={24} weight="duotone" className="text-[#FF3B30]" />
            </div>
            <p className="text-4xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{stats.activeTournaments}</p>
          </div>

          <div className="border border-[#262626] p-6 bg-[#141414]" data-testid="stat-total-players">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">TOTAL PLAYERS</p>
              <Users size={24} weight="duotone" className="text-[#007AFF]" />
            </div>
            <p className="text-4xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{stats.totalPlayers}</p>
          </div>

          <div className="border border-[#262626] p-6 bg-[#141414]" data-testid="stat-total-stakes">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">TOTAL STAKES</p>
              <Trophy size={24} weight="duotone" className="text-[#22C55E]" />
            </div>
            <p className="text-4xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{stats.totalStakes.toFixed(0)} CR</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4 mb-8">
          <button
            data-testid="create-tournament-btn"
            onClick={() => navigate('/create-tournament')}
            className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2"
          >
            <Plus size={20} weight="bold" />
            CREATE TOURNAMENT
          </button>
          <button
            data-testid="browse-games-btn"
            onClick={() => navigate('/games')}
            className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all"
          >
            BROWSE GAMES
          </button>
        </div>

        {/* Active Tournaments */}
        <div>
          <h3 className="text-2xl font-bold tracking-tight mb-4" style={{fontFamily: 'Chivo'}}>ACTIVE TOURNAMENTS</h3>
          {loading ? (
            <p className="text-[#A3A3A3]">Loading...</p>
          ) : tournaments.length === 0 ? (
            <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-tournaments">
              <GameController size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
              <p className="text-[#A3A3A3] mb-4">No active tournaments</p>
              <button
                onClick={() => navigate('/create-tournament')}
                className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors"
              >
                CREATE FIRST TOURNAMENT
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tournaments.map((tournament) => (
                <div
                  key={tournament.id}
                  className="border border-[#262626] bg-[#141414] hover:border-[#3F3F3F] transition-colors cursor-pointer"
                  onClick={() => navigate(`/tournament/${tournament.id}`)}
                  data-testid={`tournament-card-${tournament.id}`}
                >
                  <div className="p-6">
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-2">{tournament.game_name}</p>
                    <h4 className="text-xl font-bold mb-4" style={{fontFamily: 'Chivo'}}>STAKE: {tournament.stake_amount} CR</h4>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-[#A3A3A3]">{tournament.current_players}/{tournament.max_players} PLAYERS</span>
                      <span className="text-[#22C55E] font-bold">OPEN</span>
                    </div>
                    <div className="mt-4 pt-4 border-t border-[#262626]">
                      <p className="text-xs text-[#A3A3A3]">Host: {tournament.creator_username}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;