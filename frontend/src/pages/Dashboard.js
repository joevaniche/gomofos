import React, { useEffect, useState } from 'react';
import Logo from '../components/Logo';
import { useNavigate, Link } from 'react-router-dom';
import TopNav from '../components/TopNav';
import ReferAMofo from '../components/ReferAMofo';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Trophy, GameController, Users, SignOut, Plus, Coins, Sword, User } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Dashboard() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [tournaments, setTournaments] = useState([]);
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ activeTournaments: 0, totalPlayers: 0, totalStakes: 0 });

  useEffect(() => {
    loadTournaments();
    loadChallenges();
  }, []);

  const loadTournaments = async () => {
    try {
      const { data } = await axios.get(`${API}/tournaments/mine`, { withCredentials: true });
      setTournaments(data);
      
      // Stats: my active tournaments only
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

  const loadChallenges = async () => {
    try {
      const { data } = await axios.get(`${API}/challenges/incoming`, { withCredentials: true });
      setChallenges(data);
    } catch (e) { /* ignore */ }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <TopNav />

      <div className="max-w-7xl mx-auto p-6">
        {user?.status === 'on_hold' && (
          <div className="border border-[#EF4444] bg-[#EF4444]/10 p-4 mb-6" data-testid="account-on-hold-banner">
            <p className="text-sm font-bold text-[#EF4444] mb-1">⚠ ACCOUNT ON HOLD</p>
            <p className="text-sm text-white">{user.on_hold_reason || 'Your account is paused pending admin review.'}</p>
            <p className="text-xs text-[#A3A3A3] mt-2">Contact <a href="mailto:david@gomofos.com" className="text-[#FF3B30] underline">david@gomofos.com</a> to request a review.</p>
          </div>
        )}

        <ReferAMofo />
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
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">MY ACTIVE TOURNAMENTS</p>
              <GameController size={24} weight="duotone" className="text-[#FF3B30]" />
            </div>
            <p className="text-4xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{stats.activeTournaments}</p>
          </div>

          <div className="border border-[#262626] p-6 bg-[#141414]" data-testid="stat-total-players">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">OPPONENTS IN PLAY</p>
              <Users size={24} weight="duotone" className="text-[#007AFF]" />
            </div>
            <p className="text-4xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{stats.totalPlayers}</p>
          </div>

          <div className="border border-[#262626] p-6 bg-[#141414]" data-testid="stat-total-stakes">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">MY ACTIVE STAKES</p>
              <Trophy size={24} weight="duotone" className="text-[#22C55E]" />
            </div>
            <p className="text-4xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{stats.totalStakes.toFixed(0)} CR</p>
          </div>
        </div>

        {/* Incoming Challenges */}
        {challenges.length > 0 && (
          <div className="mb-8" data-testid="incoming-challenges">
            <h3 className="text-2xl font-bold tracking-tight mb-4 flex items-center gap-2" style={{fontFamily: 'Chivo'}}>
              <Sword size={24} weight="duotone" className="text-[#FF3B30]" />
              INCOMING CHALLENGES
              <span className="text-sm px-2 py-1 bg-[#FF3B30] text-white">{challenges.length}</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {challenges.map(c => (
                <div key={c.tournament_id}
                  className="border border-[#FF3B30] bg-[#FF3B30]/5 p-4 hover:bg-[#FF3B30]/10 transition-all"
                  data-testid={`challenge-${c.tournament_id}`}>
                  <div className="flex items-start justify-between gap-3 cursor-pointer" onClick={() => navigate(`/tournament/${c.tournament_id}`)}>
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">{c.game_name} • {c.game_platform}</p>
                      <h4 className="text-lg font-bold" style={{fontFamily: 'Chivo'}}>{c.challenger_username} CHALLENGED YOU</h4>
                      <p className="text-sm text-[#22C55E] font-bold mt-2">STAKE: {c.stake_amount} CR</p>
                    </div>
                    <Sword size={32} weight="duotone" className="text-[#FF3B30] shrink-0" />
                  </div>
                  <div className="flex gap-2 mt-3 pt-3 border-t border-[#FF3B30]/30">
                    <button
                      data-testid={`accept-challenge-${c.tournament_id}`}
                      onClick={(e) => { e.stopPropagation(); navigate(`/tournament/${c.tournament_id}`); }}
                      className="flex-1 px-3 py-2 bg-[#FF3B30] text-white font-bold text-xs hover:bg-[#D62F26] transition-colors">
                      ACCEPT
                    </button>
                    <button
                      data-testid={`decline-challenge-${c.tournament_id}`}
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (!window.confirm(`Decline ${c.challenger_username}'s challenge? They'll get their ${c.stake_amount} CR stake refunded.`)) return;
                        try {
                          await axios.post(`${API}/challenges/${c.tournament_id}/decline`, {}, { withCredentials: true });
                          toast.success(`Challenge declined — ${c.stake_amount} CR refunded`);
                          setChallenges(challenges.filter(x => x.tournament_id !== c.tournament_id));
                          await checkAuth();
                        } catch (err) {
                          toast.error(err.response?.data?.detail || 'Failed to decline');
                        }
                      }}
                      className="px-3 py-2 bg-transparent border border-[#3F3F3F] text-[#A3A3A3] hover:border-[#EF4444] hover:text-[#EF4444] font-bold text-xs transition-all">
                      DECLINE
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4 mb-8 flex-wrap">
          <button data-testid="create-tournament-btn" onClick={() => navigate('/create-tournament')}
            className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2">
            <Plus size={20} weight="bold" />
            CREATE TOURNAMENT
          </button>
          <button data-testid="find-players-btn" onClick={() => navigate('/players')}
            className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all flex items-center gap-2">
            <User size={20} weight="bold" />
            FIND PLAYERS
          </button>
          <button data-testid="browse-games-btn" onClick={() => navigate('/games')}
            className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">
            BROWSE GAMES
          </button>
        </div>

        {/* Active Tournaments */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-2xl font-bold tracking-tight" style={{fontFamily: 'Chivo'}}>MY ACTIVE TOURNAMENTS</h3>
            <Link to="/tournaments" className="text-sm font-bold text-[#FF3B30] hover:text-[#D62F26]" data-testid="browse-all-tournaments">BROWSE ALL →</Link>
          </div>
          {loading ? (
            <p className="text-[#A3A3A3]">Loading...</p>
          ) : tournaments.length === 0 ? (
            <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-tournaments">
              <GameController size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
              <p className="text-[#A3A3A3] mb-4">You're not in any active tournaments yet</p>
              <div className="flex gap-3 justify-center flex-wrap">
                <button
                  onClick={() => navigate('/tournaments')}
                  className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all"
                >
                  BROWSE TOURNAMENTS
                </button>
                <button
                  onClick={() => navigate('/create-tournament')}
                  className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors"
                >
                  CREATE TOURNAMENT
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tournaments.map((tournament) => {
                const statusColor = {
                  'open': 'text-[#22C55E]',
                  'in_progress': 'text-[#007AFF]',
                  'pending_confirmation': 'text-[#F59E0B]',
                  'disputed': 'text-[#EF4444]',
                }[tournament.status] || 'text-[#A3A3A3]';
                const statusLabel = {
                  'open': 'WAITING',
                  'in_progress': 'IN PLAY',
                  'pending_confirmation': 'AWAITING RESULT',
                  'disputed': 'DISPUTED',
                }[tournament.status] || tournament.status.toUpperCase();
                return (
                  <div
                    key={tournament.id}
                    className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm hover:border-[#3F3F3F] transition-colors cursor-pointer"
                    onClick={() => navigate(`/tournament/${tournament.id}`)}
                    data-testid={`tournament-card-${tournament.id}`}
                  >
                    <div className="p-6">
                      <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">{tournament.game_name}</p>
                      <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#007AFF] mb-3">{tournament.platform}</p>
                      <h4 className="text-xl font-bold mb-4" style={{fontFamily: 'Chivo'}}>STAKE: {tournament.stake_amount} CR</h4>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[#A3A3A3]">{tournament.current_players}/{tournament.max_players} PLAYERS</span>
                        <span className={`${statusColor} font-bold`}>{statusLabel}</span>
                      </div>
                      <div className="mt-4 pt-4 border-t border-[#262626]">
                        <p className="text-xs text-[#A3A3A3]">Host: {tournament.creator_username}</p>
                      </div>
                    </div>
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

export default Dashboard;
