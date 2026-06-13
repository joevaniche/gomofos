import React, { useEffect, useState } from 'react';
import Logo from '../components/Logo';
import { useNavigate, Link } from 'react-router-dom';
import TopNav from '../components/TopNav';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Plus, GameController, SignOut, Coins, MagnifyingGlass, Database } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function BrowseGames() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddGame, setShowAddGame] = useState(false);
  const [newGame, setNewGame] = useState({ name: '', platform: '', image_url: '', category: '' });
  const [q, setQ] = useState('');
  const [activeCategory, setActiveCategory] = useState('');
  const [seeding, setSeeding] = useState(false);

  const isAdmin = user?.role === 'admin';

  useEffect(() => { loadGames(); loadCategories(); /* eslint-disable-next-line */ }, [q, activeCategory]);

  const loadGames = async () => {
    setLoading(true);
    try {
      const params = {};
      if (q.trim()) params.q = q.trim();
      if (activeCategory) params.category = activeCategory;
      const { data } = await axios.get(`${API}/games`, { params, withCredentials: true });
      setGames(data);
    } catch (e) {
      toast.error('Failed to load games');
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const { data } = await axios.get(`${API}/games/categories`, { withCredentials: true });
      setCategories(data);
    } catch (e) { /* ignore */ }
  };

  const handleAddGame = async (e) => {
    e.preventDefault();
    if (!newGame.platform || !newGame.platform.trim()) {
      toast.error('Please select at least one platform');
      return;
    }
    try {
      const payload = { ...newGame };
      if (!payload.category) delete payload.category;
      if (!payload.image_url) delete payload.image_url;
      await axios.post(`${API}/games`, payload, { withCredentials: true });
      toast.success('Game added');
      setNewGame({ name: '', platform: '', image_url: '', category: '' });
      setShowAddGame(false);
      loadGames();
      loadCategories();
    } catch (e) {
      toast.error('Failed to add game');
    }
  };

  const handleSeed = async () => {
    if (!window.confirm('Add the top 100 popular online games to the catalog? Existing games will not be duplicated.')) return;
    setSeeding(true);
    try {
      const { data } = await axios.post(`${API}/admin/seed-games`, {}, { withCredentials: true });
      toast.success(data.message);
      loadGames();
      loadCategories();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to seed games');
    } finally {
      setSeeding(false);
    }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  return (
    <div className="min-h-screen">
      <TopNav />

      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
          <div>
            <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>GAME CATALOG</h2>
            <p className="text-sm text-[#A3A3A3]">Browse all available games across platforms</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            {isAdmin && (
              <button data-testid="seed-games-btn" onClick={handleSeed} disabled={seeding}
                className="px-6 py-3 bg-[#007AFF] text-white font-bold hover:bg-[#0064D2] transition-colors flex items-center gap-2 disabled:opacity-50">
                <Database size={20} weight="bold" />{seeding ? 'SEEDING...' : 'SEED TOP 100 GAMES'}
              </button>
            )}
            <button data-testid="add-game-btn" onClick={() => setShowAddGame(!showAddGame)}
              className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2">
              <Plus size={20} weight="bold" />ADD GAME
            </button>
          </div>
        </div>

        {/* Search + Category filter */}
        <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-4 mb-6" data-testid="game-filters">
          <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
            <div className="flex-1 relative">
              <MagnifyingGlass size={18} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A3A3A3]" />
              <input data-testid="game-search-input" type="text" value={q} onChange={(e) => setQ(e.target.value)}
                placeholder="Search games by name..."
                className="w-full pl-10 pr-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
            </div>
            <div className="flex gap-2 overflow-x-auto">
              <button onClick={() => setActiveCategory('')} data-testid="cat-all"
                className={`px-4 py-2 text-xs font-bold uppercase tracking-[0.1em] border whitespace-nowrap transition-all ${activeCategory === '' ? 'bg-[#FF3B30] border-[#FF3B30] text-white' : 'bg-[#0A0A0A] border-[#262626] text-[#A3A3A3] hover:border-[#3F3F3F]'}`}>
                ALL
              </button>
              {categories.map(cat => (
                <button key={cat} onClick={() => setActiveCategory(activeCategory === cat ? '' : cat)} data-testid={`cat-${cat.toLowerCase()}`}
                  className={`px-4 py-2 text-xs font-bold uppercase tracking-[0.1em] border whitespace-nowrap transition-all ${activeCategory === cat ? 'bg-[#FF3B30] border-[#FF3B30] text-white' : 'bg-[#0A0A0A] border-[#262626] text-[#A3A3A3] hover:border-[#3F3F3F]'}`}>
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Add Game Form */}
        {showAddGame && (
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6" data-testid="add-game-form">
            <h3 className="text-xl font-bold mb-4" style={{fontFamily: 'Chivo'}}>ADD NEW GAME</h3>
            <form onSubmit={handleAddGame} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">NAME</label>
                  <input data-testid="game-name-input" type="text" value={newGame.name} onChange={(e) => setNewGame({...newGame, name: e.target.value})} required
                    className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" placeholder="FIFA 25" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">PLATFORM(S)</label>
                  <div className="px-3 py-3 bg-[#0A0A0A] border border-[#262626] grid grid-cols-2 gap-2 max-h-48 overflow-y-auto" data-testid="game-platform-multiselect">
                    {[
                      'PC',
                      'PlayStation 5',
                      'PlayStation 4',
                      'Xbox Series X|S',
                      'Xbox One',
                      'Nintendo Switch',
                      'Nintendo Switch 2',
                      'Steam Deck',
                      'iOS',
                      'Android',
                      'Meta Quest',
                      'Mac',
                    ].map(p => {
                      const selected = newGame.platform.split(',').map(s => s.trim()).includes(p);
                      return (
                        <label key={p} className={`flex items-center gap-2 px-2 py-1 text-sm cursor-pointer ${selected ? 'text-white' : 'text-[#A3A3A3]'} hover:text-white`}>
                          <input
                            data-testid={`platform-option-${p.replace(/[^a-zA-Z0-9]/g,'-').toLowerCase()}`}
                            type="checkbox"
                            checked={selected}
                            onChange={() => {
                              const current = newGame.platform.split(',').map(s => s.trim()).filter(Boolean);
                              const next = selected ? current.filter(x => x !== p) : [...current, p];
                              setNewGame({ ...newGame, platform: next.join(', ') });
                            }}
                            className="accent-[#FF3B30]"
                          />
                          {p}
                        </label>
                      );
                    })}
                  </div>
                  <p className="text-xs text-[#A3A3A3] mt-1">{newGame.platform || 'Select at least one platform'}</p>
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">CATEGORY</label>
                  <input data-testid="game-category-input" type="text" value={newGame.category} onChange={(e) => setNewGame({...newGame, category: e.target.value})}
                    className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" placeholder="FPS, MOBA, Sports..." />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">COVER IMAGE URL (OPTIONAL)</label>
                  <input data-testid="game-image-input" type="url" value={newGame.image_url} onChange={(e) => setNewGame({...newGame, image_url: e.target.value})}
                    className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" placeholder="https://..." />
                </div>
              </div>
              <div className="flex gap-3">
                <button data-testid="add-game-submit-btn" type="submit" className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors">ADD GAME</button>
                <button type="button" onClick={() => setShowAddGame(false)} className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">CANCEL</button>
              </div>
            </form>
          </div>
        )}

        {/* Games Grid */}
        <p className="text-sm text-[#A3A3A3] mb-4">{games.length} game{games.length !== 1 ? 's' : ''}{activeCategory && ` in ${activeCategory}`}</p>
        {loading ? (
          <p className="text-[#A3A3A3]">Loading games...</p>
        ) : games.length === 0 ? (
          <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-games">
            <GameController size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
            <p className="text-[#A3A3A3] mb-4">No games found matching your filters.</p>
            {isAdmin && games.length === 0 && !q && !activeCategory && (
              <button onClick={handleSeed} className="px-6 py-3 bg-[#007AFF] text-white font-bold hover:bg-[#0064D2] transition-colors flex items-center gap-2 mx-auto">
                <Database size={20} weight="bold" />SEED TOP 100 GAMES
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4" data-testid="games-grid">
            {games.map((game) => (
              <div key={game.id} onClick={() => navigate(`/games/${game.id}/leaderboard`)}
                className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm hover:border-[#FF3B30] cursor-pointer transition-colors group" data-testid={`game-card-${game.id}`}>
                <div className="h-32 overflow-hidden bg-[#1A1A1A] flex items-center justify-center relative">
                  {game.image_url ? (
                    <img src={game.image_url} alt={game.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
                  ) : null}
                  <div className={`w-full h-full ${game.image_url ? 'hidden' : 'flex'} items-center justify-center absolute inset-0 bg-[#1A1A1A]`}>
                    <GameController size={48} weight="duotone" className="text-[#3F3F3F]" />
                  </div>
                </div>
                <div className="p-4">
                  <h4 className="text-sm font-bold mb-1 truncate" style={{fontFamily: 'Chivo'}} title={game.name}>{game.name}</h4>
                  <p className="text-xs text-[#A3A3A3] truncate" title={game.platform}>{game.platform}</p>
                  {game.category && (
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#FF3B30] mt-2">{game.category}</p>
                  )}
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
