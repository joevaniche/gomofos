import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Plus, GameController, SignOut, Wallet } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function BrowseGames() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddGame, setShowAddGame] = useState(false);
  const [newGame, setNewGame] = useState({ name: '', platform: '', image_url: '' });

  useEffect(() => {
    loadGames();
  }, []);

  const loadGames = async () => {
    try {
      const { data } = await axios.get(`${API}/games`, { withCredentials: true });
      setGames(data);
    } catch (e) {
      toast.error('Failed to load games');
    } finally {
      setLoading(false);
    }
  };

  const handleAddGame = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/games`, newGame, { withCredentials: true });
      toast.success('Game added successfully');
      setNewGame({ name: '', platform: '', image_url: '' });
      setShowAddGame(false);
      loadGames();
    } catch (e) {
      toast.error('Failed to add game');
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
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/games" className="text-sm font-bold text-[#FF3B30]" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-leaderboard">LEADERBOARD</Link>
            <Link to="/wallet" className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-wallet">
              <Wallet size={18} weight="bold" />
              ${user?.wallet_balance?.toFixed(2) || '0.00'}
            </Link>
            <button onClick={handleLogout} className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-logout">
              <SignOut size={18} weight="bold" />
              LOGOUT
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>GAME CATALOG</h2>
            <p className="text-sm text-[#A3A3A3]">Browse all available games across platforms</p>
          </div>
          <button
            data-testid="add-game-btn"
            onClick={() => setShowAddGame(!showAddGame)}
            className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2"
          >
            <Plus size={20} weight="bold" />
            ADD GAME
          </button>
        </div>

        {/* Add Game Form */}
        {showAddGame && (
          <div className="border border-[#262626] bg-[#141414] p-6 mb-8" data-testid="add-game-form">
            <h3 className="text-xl font-bold mb-4" style={{fontFamily: 'Chivo'}}>ADD NEW GAME</h3>
            <form onSubmit={handleAddGame} className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">GAME NAME</label>
                <input
                  data-testid="game-name-input"
                  type="text"
                  value={newGame.name}
                  onChange={(e) => setNewGame({...newGame, name: e.target.value})}
                  required
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="FIFA 24"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">PLATFORM</label>
                <input
                  data-testid="game-platform-input"
                  type="text"
                  value={newGame.platform}
                  onChange={(e) => setNewGame({...newGame, platform: e.target.value})}
                  required
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="PlayStation 5, Xbox, PC"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">IMAGE URL (OPTIONAL)</label>
                <input
                  data-testid="game-image-input"
                  type="url"
                  value={newGame.image_url}
                  onChange={(e) => setNewGame({...newGame, image_url: e.target.value})}
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="https://..."
                />
              </div>
              <div className="flex gap-4">
                <button
                  data-testid="add-game-submit-btn"
                  type="submit"
                  className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors"
                >
                  ADD GAME
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddGame(false)}
                  className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all"
                >
                  CANCEL
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Games Grid */}
        {loading ? (
          <p className="text-[#A3A3A3]">Loading games...</p>
        ) : games.length === 0 ? (
          <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-games">
            <GameController size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
            <p className="text-[#A3A3A3] mb-4">No games available yet</p>
            <button
              onClick={() => setShowAddGame(true)}
              className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors"
            >
              ADD FIRST GAME
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {games.map((game) => (
              <div
                key={game.id}
                className="border border-[#262626] bg-[#141414] hover:border-[#3F3F3F] transition-colors"
                data-testid={`game-card-${game.id}`}
              >
                {game.image_url ? (
                  <div className="h-48 overflow-hidden">
                    <img src={game.image_url} alt={game.name} className="w-full h-full object-cover" />
                  </div>
                ) : (
                  <div className="h-48 bg-[#1A1A1A] flex items-center justify-center">
                    <GameController size={64} weight="duotone" className="text-[#3F3F3F]" />
                  </div>
                )}
                <div className="p-6">
                  <h4 className="text-xl font-bold mb-2" style={{fontFamily: 'Chivo'}}>{game.name}</h4>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">{game.platform}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default BrowseGames;