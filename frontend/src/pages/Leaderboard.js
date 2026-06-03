import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, Trophy, Medal } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Leaderboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLeaderboard();
  }, []);

  const loadLeaderboard = async () => {
    try {
      const { data } = await axios.get(`${API}/leaderboard`, { withCredentials: true });
      setLeaderboard(data);
    } catch (e) {
      toast.error('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getRankIcon = (index) => {
    if (index === 0) return <Trophy size={24} weight="fill" className="text-[#F59E0B]" />;
    if (index === 1) return <Medal size={24} weight="fill" className="text-[#A3A3A3]" />;
    if (index === 2) return <Medal size={24} weight="fill" className="text-[#CD7F32]" />;
    return <span className="text-lg font-bold text-[#A3A3A3]">#{index + 1}</span>;
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Navigation */}
      <nav className="border-b border-[#262626] bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-black tracking-tighter text-white" style={{fontFamily: 'Chivo'}}>ESPORTS BET</h1>
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#FF3B30]" data-testid="nav-leaderboard">LEADERBOARD</Link>
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

      <div className="max-w-5xl mx-auto p-6">
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>LEADERBOARD</h2>
          <p className="text-sm text-[#A3A3A3]">Top players ranked by wins</p>
        </div>

        {loading ? (
          <p className="text-[#A3A3A3] text-center py-8">Loading leaderboard...</p>
        ) : leaderboard.length === 0 ? (
          <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-leaderboard">
            <Trophy size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
            <p className="text-[#A3A3A3]">No rankings yet. Be the first to compete!</p>
          </div>
        ) : (
          <div className="border border-[#262626] bg-[#141414]">
            {/* Header */}
            <div className="grid grid-cols-12 gap-4 p-4 border-b border-[#262626] text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">
              <div className="col-span-1">RANK</div>
              <div className="col-span-4">PLAYER</div>
              <div className="col-span-2 text-center">WINS</div>
              <div className="col-span-2 text-center">LOSSES</div>
              <div className="col-span-2 text-center">WIN RATE</div>
              <div className="col-span-1 text-right">BALANCE</div>
            </div>

            {/* Leaderboard Entries */}
            <div>
              {leaderboard.map((player, index) => {
                const totalGames = player.wins + player.losses;
                const winRate = totalGames > 0 ? ((player.wins / totalGames) * 100).toFixed(1) : '0.0';
                const isCurrentUser = player.user_id === user?.id;

                return (
                  <div
                    key={player.user_id}
                    className={`grid grid-cols-12 gap-4 p-4 border-b border-[#262626] hover:bg-[#1A1A1A] transition-colors ${
                      isCurrentUser ? 'bg-[#FF3B30]/5' : ''
                    }`}
                    data-testid={`leaderboard-entry-${index}`}
                  >
                    <div className="col-span-1 flex items-center">
                      {getRankIcon(index)}
                    </div>
                    <div className="col-span-4 flex items-center">
                      <span className="font-bold text-white">
                        {player.username}
                        {isCurrentUser && <span className="ml-2 text-xs text-[#FF3B30]">(YOU)</span>}
                      </span>
                    </div>
                    <div className="col-span-2 flex items-center justify-center">
                      <span className="font-bold text-[#22C55E]">{player.wins}</span>
                    </div>
                    <div className="col-span-2 flex items-center justify-center">
                      <span className="font-bold text-[#EF4444]">{player.losses}</span>
                    </div>
                    <div className="col-span-2 flex items-center justify-center">
                      <span className="font-bold text-white">{winRate}%</span>
                    </div>
                    <div className="col-span-1 flex items-center justify-end">
                      <span className="text-sm text-[#A3A3A3]">{player.balance.toFixed(0)} CR</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Leaderboard;