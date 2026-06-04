import React, { useEffect, useState } from 'react';
import Logo from '../components/Logo';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function CreateTournament() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    game_id: '',
    stake_amount: '',
    max_players: 2,
    start_time: ''
  });

  useEffect(() => {
    loadGames();
    // Set default start time to 1 hour from now
    const now = new Date();
    now.setHours(now.getHours() + 1);
    setFormData(prev => ({ ...prev, start_time: now.toISOString().slice(0, 16) }));
  }, []);

  const loadGames = async () => {
    try {
      const { data } = await axios.get(`${API}/games`, { withCredentials: true });
      setGames(data);
      if (data.length > 0) {
        setFormData(prev => ({ ...prev, game_id: data[0].id }));
      }
    } catch (e) {
      toast.error('Failed to load games');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const stakeAmount = parseFloat(formData.stake_amount);
    if (stakeAmount <= 0) {
      toast.error('Stake amount must be greater than 0');
      return;
    }
    
    if (user.wallet_balance < stakeAmount) {
      toast.error('Insufficient wallet balance');
      return;
    }

    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/tournaments`, {
        game_id: formData.game_id,
        stake_amount: stakeAmount,
        max_players: parseInt(formData.max_players),
        start_time: new Date(formData.start_time).toISOString()
      }, { withCredentials: true });
      
      toast.success('Tournament created successfully');
      navigate(`/tournament/${data.id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create tournament');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (games.length === 0) {
    return (
      <div className="min-h-screen">
        <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <Logo />
          </div>
        </nav>
        <div className="max-w-3xl mx-auto p-6 text-center">
          <p className="text-[#A3A3A3] mb-4">No games available. Please add games first.</p>
          <button onClick={() => navigate('/games')} className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors">
            GO TO GAMES
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/players" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-players">PLAYERS</Link>
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-leaderboard">LEADERBOARD</Link>
            <Link to="/profile" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-profile">PROFILE</Link>
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

      <div className="max-w-3xl mx-auto p-6">
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>CREATE TOURNAMENT</h2>
          <p className="text-sm text-[#A3A3A3]">Set up a new competitive match</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6" data-testid="create-tournament-form">
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6">
            <div className="space-y-6">
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">SELECT GAME</label>
                <select
                  data-testid="tournament-game-select"
                  value={formData.game_id}
                  onChange={(e) => setFormData({...formData, game_id: e.target.value})}
                  required
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                >
                  {games.map(game => (
                    <option key={game.id} value={game.id}>{game.name} - {game.platform}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">STAKE AMOUNT (CREDITS)</label>
                <input
                  data-testid="tournament-stake-input"
                  type="number"
                  step="1"
                  min="1"
                  value={formData.stake_amount}
                  onChange={(e) => setFormData({...formData, stake_amount: e.target.value})}
                  required
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="100"
                />
                <p className="text-xs text-[#A3A3A3] mt-2">Your balance: {user?.wallet_balance?.toFixed(0) || '0'} CR</p>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">MAX PLAYERS</label>
                <select
                  data-testid="tournament-max-players-select"
                  value={formData.max_players}
                  onChange={(e) => setFormData({...formData, max_players: e.target.value})}
                  required
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                >
                  <option value="2">2 Players</option>
                  <option value="4">4 Players</option>
                  <option value="8">8 Players</option>
                  <option value="16">16 Players</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">START TIME</label>
                <input
                  data-testid="tournament-start-time-input"
                  type="datetime-local"
                  value={formData.start_time}
                  onChange={(e) => setFormData({...formData, start_time: e.target.value})}
                  required
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-4">
            <button
              data-testid="create-tournament-submit-btn"
              type="submit"
              disabled={loading}
              className="px-8 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50"
            >
              {loading ? 'CREATING...' : 'CREATE TOURNAMENT'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="px-8 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all"
            >
              CANCEL
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateTournament;
