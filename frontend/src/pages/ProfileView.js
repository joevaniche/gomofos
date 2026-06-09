import React, { useEffect, useState } from 'react';
import Logo from '../components/Logo';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, User, MapPin, Trophy, X, Sword, Circle, CircleDashed } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { HighlightReels } from '../components/HighlightReels';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PLATFORM_LABELS = {
  ps5: 'PlayStation 5', ps4: 'PlayStation 4', xbox_series: 'Xbox Series X/S',
  xbox_one: 'Xbox One', pc: 'PC', switch: 'Nintendo Switch', mobile: 'Mobile',
};
const GAMERTAG_LABELS = {
  psn: 'PSN ID', xbox: 'Xbox Gamertag', steam: 'Steam', epic: 'Epic Games',
  battle_net: 'Battle.net', switch: 'Nintendo Switch', riot: 'Riot ID', activision: 'Activision ID',
};

function ChallengeModal({ opponent, currentUserGames, onClose }) {
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [form, setForm] = useState({ game_id: '', stake_amount: '', start_time: '' });
  const [sending, setSending] = useState(false);

  useEffect(() => {
    // Intersection of opponent's games + your games (best match)
    const ids = new Set(currentUserGames.map(g => g.id));
    const matching = (opponent.preferred_games || []).filter(g => ids.has(g.id));
    setGames(matching.length > 0 ? matching : opponent.preferred_games || []);
    
    const now = new Date();
    now.setHours(now.getHours() + 1);
    setForm(f => ({ ...f, start_time: now.toISOString().slice(0, 16) }));
  }, [opponent, currentUserGames]);

  const handleSend = async () => {
    if (!form.game_id || !form.stake_amount) {
      toast.error('Pick a game and stake amount');
      return;
    }
    setSending(true);
    try {
      const { data } = await axios.post(`${API}/challenges`, {
        opponent_user_id: opponent.id,
        game_id: form.game_id,
        stake_amount: parseFloat(form.stake_amount),
        start_time: new Date(form.start_time).toISOString(),
      }, { withCredentials: true });
      toast.success(data.message);
      onClose();
      navigate(`/tournament/${data.tournament_id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to send challenge');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[#141414] border border-[#262626] max-w-lg w-full" onClick={(e) => e.stopPropagation()} data-testid="challenge-modal">
        <div className="flex items-center justify-between p-6 border-b border-[#262626]">
          <div className="flex items-center gap-2">
            <Sword size={24} weight="duotone" className="text-[#FF3B30]" />
            <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>CHALLENGE {opponent.username.toUpperCase()}</h3>
          </div>
          <button onClick={onClose} className="text-[#A3A3A3] hover:text-white">
            <X size={24} weight="bold" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {games.length === 0 ? (
            <div className="p-4 bg-[#EF4444]/10 border border-[#EF4444]">
              <p className="text-sm text-white">No common games. Update your profile or pick from any game below.</p>
            </div>
          ) : (
            <p className="text-xs text-[#22C55E] font-bold">✓ {games.length} game{games.length !== 1 ? 's' : ''} in common</p>
          )}
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">GAME</label>
            <select data-testid="challenge-game" value={form.game_id} onChange={(e) => setForm({...form, game_id: e.target.value})}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]">
              <option value="">Select a game...</option>
              {(games.length > 0 ? games : opponent.preferred_games).map(g => (
                <option key={g.id} value={g.id}>{g.name} — {g.platform}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">STAKE (CR)</label>
            <input data-testid="challenge-stake" type="number" min="1" step="1" value={form.stake_amount} onChange={(e) => setForm({...form, stake_amount: e.target.value})}
              placeholder="100"
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
            {(opponent.stake_min || opponent.stake_max) && (
              <p className="text-xs text-[#A3A3A3] mt-1">Opponent plays for {opponent.stake_min || 0}-{opponent.stake_max || '∞'} CR</p>
            )}
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">PROPOSED START</label>
            <input data-testid="challenge-time" type="datetime-local" value={form.start_time} onChange={(e) => setForm({...form, start_time: e.target.value})}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
          </div>
          <div className="flex gap-3 pt-2">
            <button data-testid="send-challenge-btn" onClick={handleSend} disabled={sending}
              className="flex-1 px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
              <Sword size={18} weight="bold" />
              {sending ? 'SENDING...' : 'SEND CHALLENGE'}
            </button>
            <button onClick={onClose} className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">CANCEL</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileView() {
  const { id: paramId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  // If no :id is in the URL (visited from the PROFILE nav link), show the current user's profile
  const id = paramId || user?.id;
  const [profile, setProfile] = useState(null);
  const [myProfile, setMyProfile] = useState(null);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showChallenge, setShowChallenge] = useState(false);

  useEffect(() => { loadAll(); /* eslint-disable-next-line */ }, [id]);

  const loadAll = async () => {
    try {
      const [p, mine, g] = await Promise.all([
        axios.get(`${API}/users/${id}`, { withCredentials: true }),
        axios.get(`${API}/users/me/profile`, { withCredentials: true }),
        axios.get(`${API}/games`, { withCredentials: true }),
      ]);
      setProfile(p.data);
      setMyProfile(mine.data);
      setGames(g.data);
    } catch (e) {
      toast.error('Profile not found');
      navigate('/players');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const flagEmoji = (code) => {
    if (!code || code === 'OTHER' || code.length !== 2) return '🌐';
    return code.toUpperCase().replace(/./g, c => String.fromCodePoint(127397 + c.charCodeAt()));
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><p className="text-white">Loading...</p></div>;

  const isOwnProfile = profile.id === user.id;
  const winRate = (profile.total_wins + profile.total_losses) > 0 ? Math.round(profile.total_wins / (profile.total_wins + profile.total_losses) * 100) : 0;
  const lastActiveDate = profile.last_active_at ? new Date(profile.last_active_at) : null;
  const isOnline = lastActiveDate && (Date.now() - lastActiveDate.getTime() < 10 * 60 * 1000);
  const hasGamertags = profile.gamertags && Object.values(profile.gamertags).some(v => v);

  return (
    <div className="min-h-screen">
      <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/tournaments" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-tournaments">TOURNAMENTS</Link>
            <Link to="/competitions" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-competitions">COMPETITIONS</Link>
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

      <div className="max-w-5xl mx-auto p-6">
        {/* Header */}
        <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 bg-[#0A0A0A] border border-[#262626] flex items-center justify-center">
                <User size={40} weight="duotone" className="text-[#FF3B30]" />
              </div>
              <div>
                <h2 className="text-3xl font-black tracking-tighter text-white" style={{fontFamily: 'Chivo'}} data-testid="profile-username">{profile.username}</h2>
                <p className="text-sm text-[#A3A3A3] flex items-center gap-2 mt-1">
                  {isOnline ? <Circle size={10} weight="fill" className="text-[#22C55E]" /> : <CircleDashed size={10} weight="bold" className="text-[#525252]" />}
                  {isOnline ? 'Online now' : (lastActiveDate ? `Last seen ${lastActiveDate.toLocaleString()}` : 'Never active')}
                </p>
                {(profile.country || profile.city) && (
                  <p className="text-sm text-[#A3A3A3] flex items-center gap-2 mt-1">
                    <MapPin size={14} weight="bold" />
                    <span>{flagEmoji(profile.country)}</span>
                    {profile.city ? `${profile.city}, ` : ''}{profile.country}
                    {profile.timezone && ` (${profile.timezone})`}
                  </p>
                )}
              </div>
            </div>
            {isOwnProfile ? (
              <button data-testid="edit-profile-btn" onClick={() => navigate('/profile/edit')}
                className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">
                EDIT PROFILE
              </button>
            ) : (
              <button data-testid="challenge-btn" onClick={() => setShowChallenge(true)}
                className="px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2">
                <Sword size={18} weight="bold" />CHALLENGE
              </button>
            )}
          </div>
          {profile.bio && (
            <p className="text-sm text-[#A3A3A3] mt-4 leading-relaxed border-l-2 border-[#FF3B30] pl-4" data-testid="profile-bio">{profile.bio}</p>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 text-center" data-testid="stat-wins">
            <Trophy size={28} weight="duotone" className="text-[#22C55E] mx-auto mb-2" />
            <p className="text-3xl font-black" style={{fontFamily: 'Chivo'}}>{profile.total_wins}</p>
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mt-1">WINS</p>
          </div>
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 text-center" data-testid="stat-losses">
            <p className="text-3xl font-black mt-2" style={{fontFamily: 'Chivo'}}>{profile.total_losses}</p>
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mt-1">LOSSES</p>
          </div>
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 text-center" data-testid="stat-winrate">
            <p className="text-3xl font-black mt-2" style={{fontFamily: 'Chivo'}}>{winRate}%</p>
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mt-1">WIN RATE</p>
          </div>
        </div>

        {/* Stake range */}
        {(profile.stake_min || profile.stake_max) && (
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6" data-testid="stake-range">
            <div className="flex items-center gap-2 mb-2">
              <Coins size={20} weight="duotone" className="text-[#F59E0B]" />
              <h3 className="text-sm font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">PREFERRED STAKE RANGE</h3>
            </div>
            <p className="text-2xl font-bold text-white">{profile.stake_min || 0} – {profile.stake_max || '∞'} CR</p>
          </div>
        )}

        {/* Platforms */}
        {profile.platforms.length > 0 && (
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6" data-testid="platforms-section">
            <h3 className="text-sm font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-3">PLATFORMS</h3>
            <div className="flex flex-wrap gap-2">
              {profile.platforms.map(p => (
                <span key={p} className="px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-sm font-bold text-white">{PLATFORM_LABELS[p] || p}</span>
              ))}
            </div>
          </div>
        )}

        {/* Gamertags */}
        {hasGamertags && (
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6" data-testid="gamertags-section">
            <h3 className="text-sm font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-3">GAMERTAGS</h3>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(profile.gamertags).filter(([_, v]) => v).map(([k, v]) => (
                <div key={k} className="p-3 bg-[#0A0A0A] border border-[#262626]">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">{GAMERTAG_LABELS[k] || k}</p>
                  <p className="text-sm font-bold text-white mt-1">{v}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Games */}
        {profile.preferred_games.length > 0 && (
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6 mb-6" data-testid="games-section">
            <h3 className="text-sm font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-3">GAMES PLAYED</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {profile.preferred_games.map(g => (
                <div key={g.id} className="p-3 bg-[#0A0A0A] border border-[#262626]">
                  <p className="text-sm font-bold text-white">{g.name}</p>
                  <p className="text-xs text-[#A3A3A3]">{g.platform}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Highlight Reels */}
        <HighlightReels userId={profile.id} isOwner={isOwnProfile} games={games} />
      </div>

      {showChallenge && <ChallengeModal opponent={profile} currentUserGames={myProfile?.preferred_games || []} onClose={() => setShowChallenge(false)} />}
    </div>
  );
}

export default ProfileView;
