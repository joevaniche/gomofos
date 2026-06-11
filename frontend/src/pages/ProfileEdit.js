import React, { useEffect, useState } from 'react';
import Logo from '../components/Logo';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, User, MapPin, GameController, Check } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PLATFORM_LABELS = {
  ps5: 'PS5', ps4: 'PS4', xbox_series: 'Xbox Series X/S', xbox_one: 'Xbox One',
  pc: 'PC', switch: 'Switch', mobile: 'Mobile',
};

const GAMERTAG_LABELS = {
  psn: 'PSN ID', xbox: 'Xbox Gamertag', steam: 'Steam', epic: 'Epic Games',
  battle_net: 'Battle.net', switch: 'Nintendo Switch', riot: 'Riot ID', activision: 'Activision ID',
};

function ProfileEdit() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [countries, setCountries] = useState([]);
  const [platformsList, setPlatformsList] = useState([]);
  const [games, setGames] = useState([]);
  const [profile, setProfile] = useState({
    bio: '', country: '', city: '', timezone: '',
    platforms: [], gamertags: {}, preferred_game_ids: [],
    stake_min: '', stake_max: '',
  });

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [p, c, pl, g] = await Promise.all([
        axios.get(`${API}/users/me/profile`, { withCredentials: true }),
        axios.get(`${API}/countries`, { withCredentials: true }),
        axios.get(`${API}/platforms-list`, { withCredentials: true }),
        axios.get(`${API}/games`, { withCredentials: true }),
      ]);
      setProfile({
        bio: p.data.bio || '',
        country: p.data.country || '',
        city: p.data.city || '',
        timezone: p.data.timezone || '',
        platforms: p.data.platforms || [],
        gamertags: p.data.gamertags || {},
        preferred_game_ids: p.data.preferred_game_ids || [],
        stake_min: p.data.stake_min ?? '',
        stake_max: p.data.stake_max ?? '',
      });
      setCountries(c.data);
      setPlatformsList(pl.data);
      setGames(g.data);
    } catch (e) {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const togglePlatform = (code) => {
    setProfile(prev => ({
      ...prev,
      platforms: prev.platforms.includes(code) ? prev.platforms.filter(p => p !== code) : [...prev.platforms, code]
    }));
  };

  const toggleGame = (id) => {
    setProfile(prev => ({
      ...prev,
      preferred_game_ids: prev.preferred_game_ids.includes(id) ? prev.preferred_game_ids.filter(x => x !== id) : [...prev.preferred_game_ids, id]
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...profile,
        stake_min: profile.stake_min === '' ? null : parseFloat(profile.stake_min),
        stake_max: profile.stake_max === '' ? null : parseFloat(profile.stake_max),
      };
      await axios.put(`${API}/users/profile`, payload, { withCredentials: true });
      toast.success('Profile saved');
      await checkAuth();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><p className="text-white">Loading...</p></div>;

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
            <Link to="/players" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-players">PLAYERS</Link>
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

      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>YOUR PROFILE</h2>
          <p className="text-sm text-[#A3A3A3]">Complete your profile to be discovered by other players</p>
        </div>

        <div className="space-y-6">
          {/* Basic Info */}
          <section className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="section-basic">
            <div className="flex items-center gap-2 mb-4">
              <User size={24} weight="duotone" className="text-[#FF3B30]" />
              <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>BASIC INFO</h3>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">BIO</label>
                <textarea data-testid="bio-input" value={profile.bio} onChange={(e) => setProfile({...profile, bio: e.target.value})} maxLength={300} rows={3}
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="Tell other players about yourself..." />
                <p className="text-xs text-[#A3A3A3] mt-1">{profile.bio.length}/300</p>
              </div>
            </div>
          </section>

          {/* Location */}
          <section className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="section-location">
            <div className="flex items-center gap-2 mb-4">
              <MapPin size={24} weight="duotone" className="text-[#007AFF]" />
              <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>LOCATION & TIMEZONE</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">COUNTRY</label>
                <select data-testid="country-select" value={profile.country} onChange={(e) => setProfile({...profile, country: e.target.value})}
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]">
                  <option value="">Select country...</option>
                  {countries.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">CITY</label>
                <input data-testid="city-input" type="text" value={profile.city} onChange={(e) => setProfile({...profile, city: e.target.value})}
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="Sydney" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">TIMEZONE</label>
                <input data-testid="timezone-input" type="text" value={profile.timezone} onChange={(e) => setProfile({...profile, timezone: e.target.value})}
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="Australia/Sydney" />
              </div>
            </div>
          </section>

          {/* Platforms */}
          <section className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="section-platforms">
            <div className="flex items-center gap-2 mb-4">
              <GameController size={24} weight="duotone" className="text-[#22C55E]" />
              <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>PLATFORMS</h3>
            </div>
            <p className="text-xs text-[#A3A3A3] mb-3">Select all platforms you play on</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {platformsList.map(p => {
                const active = profile.platforms.includes(p.code);
                return (
                  <button key={p.code} data-testid={`platform-${p.code}`} type="button" onClick={() => togglePlatform(p.code)}
                    className={`px-4 py-3 border font-bold text-sm transition-all flex items-center justify-center gap-2 ${active ? 'bg-[#FF3B30] border-[#FF3B30] text-white' : 'bg-[#0A0A0A] border-[#262626] text-[#A3A3A3] hover:border-[#3F3F3F]'}`}>
                    {active && <Check size={16} weight="bold" />}
                    {p.name}
                  </button>
                );
              })}
            </div>
          </section>

          {/* Gamertags */}
          <section className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="section-gamertags">
            <div className="flex items-center gap-2 mb-4">
              <User size={24} weight="duotone" className="text-[#F59E0B]" />
              <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>GAMERTAGS</h3>
            </div>
            <p className="text-xs text-[#A3A3A3] mb-3">Your IDs so opponents can find you in-game</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(GAMERTAG_LABELS).map(([key, label]) => (
                <div key={key}>
                  <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">{label}</label>
                  <input data-testid={`gamertag-${key}`} type="text" value={profile.gamertags[key] || ''}
                    onChange={(e) => setProfile({...profile, gamertags: {...profile.gamertags, [key]: e.target.value}})}
                    className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                    placeholder={`Your ${label}`} />
                </div>
              ))}
            </div>
          </section>

          {/* Preferred Games */}
          <section className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="section-games">
            <div className="flex items-center gap-2 mb-4">
              <GameController size={24} weight="duotone" className="text-[#FF3B30]" />
              <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>GAMES YOU PLAY</h3>
            </div>
            <p className="text-xs text-[#A3A3A3] mb-3">Select games you want to compete in</p>
            {games.length === 0 ? (
              <p className="text-sm text-[#A3A3A3]">No games available. <Link to="/games" className="text-[#FF3B30] hover:underline">Add a game</Link> first.</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-80 overflow-y-auto">
                {games.map(g => {
                  const active = profile.preferred_game_ids.includes(g.id);
                  return (
                    <button key={g.id} data-testid={`game-${g.id}`} type="button" onClick={() => toggleGame(g.id)}
                      className={`px-4 py-3 border text-left transition-all ${active ? 'bg-[#FF3B30] border-[#FF3B30]' : 'bg-[#0A0A0A] border-[#262626] hover:border-[#3F3F3F]'}`}>
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className={`text-sm font-bold ${active ? 'text-white' : 'text-white'}`}>{g.name}</p>
                          <p className={`text-xs ${active ? 'text-white/80' : 'text-[#A3A3A3]'}`}>{g.platform}</p>
                        </div>
                        {active && <Check size={16} weight="bold" className="text-white shrink-0" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </section>

          {/* Stake Range */}
          <section className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="section-stake">
            <div className="flex items-center gap-2 mb-4">
              <Coins size={24} weight="duotone" className="text-[#F59E0B]" />
              <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>STAKE RANGE</h3>
            </div>
            <p className="text-xs text-[#A3A3A3] mb-3">Credit amounts you're willing to play for</p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">MIN STAKE (CR)</label>
                <input data-testid="stake-min-input" type="number" min="0" step="1" value={profile.stake_min}
                  onChange={(e) => setProfile({...profile, stake_min: e.target.value})}
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="100" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">MAX STAKE (CR)</label>
                <input data-testid="stake-max-input" type="number" min="0" step="1" value={profile.stake_max}
                  onChange={(e) => setProfile({...profile, stake_max: e.target.value})}
                  className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  placeholder="1000" />
              </div>
            </div>
          </section>

          <div className="flex gap-4">
            <button data-testid="save-profile-btn" onClick={handleSave} disabled={saving}
              className="px-8 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50">
              {saving ? 'SAVING...' : 'SAVE PROFILE'}
            </button>
            <button onClick={() => navigate('/dashboard')}
              className="px-8 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">
              CANCEL
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfileEdit;
