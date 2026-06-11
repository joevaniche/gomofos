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
  const [profile, setProfile] = useState(null);
  const [showAllGames, setShowAllGames] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    game_id: '',
    platform: '',
    stake_amount: '',
    max_players: 2,
    start_time: ''
  });

  useEffect(() => {
    loadProfileAndGames();
    // Set default start time to 1 hour from now
    const now = new Date();
    now.setHours(now.getHours() + 1);
    setFormData(prev => ({ ...prev, start_time: now.toISOString().slice(0, 16) }));
  }, []);

  const loadProfileAndGames = async () => {
    try {
      const [profRes, gamesRes] = await Promise.all([
        axios.get(`${API}/users/me/profile`, { withCredentials: true }),
        axios.get(`${API}/games`, { withCredentials: true }),
      ]);
      setProfile(profRes.data);
      const allGames = gamesRes.data;
      const preferredIds = profRes.data?.preferred_game_ids || [];
      // Filter unless user has none, or they've toggled to show all
      const filteredGames = preferredIds.length > 0
        ? allGames.filter(g => preferredIds.includes(g.id))
        : allGames;
      setGames(filteredGames);
      if (filteredGames.length > 0) {
        const firstPlatforms = (filteredGames[0].platform || '').split(',').map(p => p.trim()).filter(Boolean);
        setFormData(prev => ({ ...prev, game_id: filteredGames[0].id, platform: firstPlatforms[0] || '' }));
      }
    } catch (e) {
      toast.error('Failed to load games');
    }
  };

  const toggleShowAll = async () => {
    try {
      const { data } = await axios.get(`${API}/games`, { withCredentials: true });
      const newShow = !showAllGames;
      setShowAllGames(newShow);
      const preferredIds = profile?.preferred_game_ids || [];
      const filtered = newShow || preferredIds.length === 0 ? data : data.filter(g => preferredIds.includes(g.id));
      setGames(filtered);
      if (filtered.length > 0) {
        const platforms = (filtered[0].platform || '').split(',').map(p => p.trim()).filter(Boolean);
        setFormData(prev => ({ ...prev, game_id: filtered[0].id, platform: platforms[0] || '' }));
      }
    } catch {}
  };

  const selectedGame = games.find(g => g.id === formData.game_id);
  const platformOptions = selectedGame ? (selectedGame.platform || '').split(',').map(p => p.trim()).filter(Boolean) : [];

  const handleGameChange = (gameId) => {
    const game = games.find(g => g.id === gameId);
    const platforms = game ? (game.platform || '').split(',').map(p => p.trim()).filter(Boolean) : [];
    setFormData({ ...formData, game_id: gameId, platform: platforms[0] || '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const stakeAmount = parseFloat(formData.stake_amount);
    if (stakeAmount <= 0) {
      toast.error('Stake amount must be greater than 0');
      return;
    }
    if (!formData.platform) {
      toast.error('Please select a platform');
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
        platform: formData.platform,
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
            <Link to="/tournaments" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-tournaments">TOURNAMENTS</Link>
            <Link to="/competitions" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-competitions">COMPETITIONS</Link>
            <Link to="/prizes" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-prizes">PRIZES</Link>
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
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">SELECT GAME</label>
                  {profile && (profile.preferred_game_ids?.length || 0) > 0 && (
                    <button type="button" onClick={toggleShowAll} data-testid="toggle-show-all-games"
                      className="text-xs font-bold text-[#A3A3A3] hover:text-[#FF3B30] transition-colors">
                      {showAllGames ? '◀ SHOW ONLY MY PREFERRED GAMES' : 'SHOW ALL GAMES ▶'}
                    </button>
                  )}
                </div>
                {profile && (profile.preferred_game_ids?.length || 0) === 0 && (
                  <div className="mb-2 p-3 bg-[#1A1A1A] border border-[#262626] text-xs text-[#A3A3A3]">
                    Tip: pick your <Link to="/profile/edit" className="text-[#FF3B30] font-bold hover:underline">preferred games on your profile</Link> to filter this list to just the games you actually play.
                  </div>
                )}
                <select
                  data-testid="tournament-game-select"
                  value={formData.game_id}
                  onChange={(e) => handleGameChange(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                >
                  {games.map(game => (
                    <option key={game.id} value={game.id}>{game.name} - {game.platform}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">PLATFORM</label>
                {platformOptions.length > 1 ? (
                  <select
                    data-testid="tournament-platform-select"
                    value={formData.platform}
                    onChange={(e) => setFormData({...formData, platform: e.target.value})}
                    required
                    className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  >
                    {platformOptions.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                ) : (
                  <input
                    data-testid="tournament-platform-input"
                    type="text"
                    value={formData.platform}
                    onChange={(e) => setFormData({...formData, platform: e.target.value})}
                    required
                    placeholder="e.g. PC, PS5, Xbox Series"
                    className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  />
                )}
                {platformOptions.length > 1 && (
                  <p className="text-xs text-[#A3A3A3] mt-2">All players must compete on this platform</p>
                )}
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
