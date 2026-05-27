import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Wallet, Users, Trophy, PaperPlaneRight } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function TournamentDetails() {
  const { id } = useParams();
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [tournament, setTournament] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [selectedWinner, setSelectedWinner] = useState('');

  useEffect(() => {
    loadTournament();
    loadMessages();
    const interval = setInterval(loadMessages, 3000);
    return () => clearInterval(interval);
  }, [id]);

  const loadTournament = async () => {
    try {
      const { data } = await axios.get(`${API}/tournaments/${id}`, { withCredentials: true });
      setTournament(data);
      if (data.participants.length > 0) {
        setSelectedWinner(data.participants[0].user_id);
      }
    } catch (e) {
      toast.error('Failed to load tournament');
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async () => {
    try {
      const { data } = await axios.get(`${API}/chat/${id}`, { withCredentials: true });
      setMessages(data);
    } catch (e) {
      console.error('Failed to load messages');
    }
  };

  const handleJoin = async () => {
    setJoining(true);
    try {
      await axios.post(`${API}/tournaments/${id}/join`, {}, { withCredentials: true });
      toast.success('Joined tournament successfully');
      await checkAuth();
      loadTournament();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to join tournament');
    } finally {
      setJoining(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    try {
      await axios.post(`${API}/chat`, { tournament_id: id, message: newMessage }, { withCredentials: true });
      setNewMessage('');
      loadMessages();
    } catch (e) {
      toast.error('Failed to send message');
    }
  };

  const handleCompleteTournament = async () => {
    if (!selectedWinner) {
      toast.error('Please select a winner');
      return;
    }

    setCompleting(true);
    try {
      const { data } = await axios.post(`${API}/tournaments/${id}/complete?winner_user_id=${selectedWinner}`, {}, { withCredentials: true });
      toast.success(`Tournament completed! Winner receives $${data.winner_amount.toFixed(2)}`);
      await checkAuth();
      loadTournament();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to complete tournament');
    } finally {
      setCompleting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <p className="text-white">Loading...</p>
      </div>
    );
  }

  const isParticipant = tournament?.participants?.some(p => p.user_id === user?.id);
  const isCreator = tournament?.creator_id === user?.id;
  const canJoin = tournament?.status === 'open' && !isParticipant && tournament?.current_players < tournament?.max_players;

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Navigation */}
      <nav className="border-b border-[#262626] bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-black tracking-tighter text-white" style={{fontFamily: 'Chivo'}}>ESPORTS BET</h1>
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tournament Info */}
          <div className="lg:col-span-2 space-y-6">
            <div className="border border-[#262626] bg-[#141414] p-6">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-2">{tournament?.game_name}</p>
              <h2 className="text-3xl font-black tracking-tighter text-white mb-4" style={{fontFamily: 'Chivo'}}>STAKE: ${tournament?.stake_amount}</h2>
              
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">STATUS</p>
                  <p className="text-lg font-bold" style={{color: tournament?.status === 'open' ? '#22C55E' : tournament?.status === 'completed' ? '#007AFF' : '#F59E0B'}}>
                    {tournament?.status?.toUpperCase()}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">PLAYERS</p>
                  <p className="text-lg font-bold text-white">{tournament?.current_players}/{tournament?.max_players}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">PRIZE POOL</p>
                  <p className="text-lg font-bold text-[#22C55E]">${(tournament?.stake_amount * tournament?.current_players * 0.95).toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">HOST</p>
                  <p className="text-lg font-bold text-white">{tournament?.creator_username}</p>
                </div>
              </div>

              {canJoin && (
                <button
                  data-testid="join-tournament-btn"
                  onClick={handleJoin}
                  disabled={joining}
                  className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50"
                >
                  {joining ? 'JOINING...' : `JOIN FOR $${tournament?.stake_amount}`}
                </button>
              )}

              {isCreator && tournament?.status === 'open' && tournament?.current_players >= 2 && (
                <div className="mt-4" data-testid="complete-tournament-section">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-2">SELECT WINNER</p>
                  <select
                    data-testid="winner-select"
                    value={selectedWinner}
                    onChange={(e) => setSelectedWinner(e.target.value)}
                    className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30] mb-4"
                  >
                    {tournament?.participants?.map(p => (
                      <option key={p.user_id} value={p.user_id}>{p.username}</option>
                    ))}
                  </select>
                  <button
                    data-testid="complete-tournament-btn"
                    onClick={handleCompleteTournament}
                    disabled={completing}
                    className="w-full px-6 py-3 bg-[#22C55E] text-white font-bold hover:bg-[#16A34A] transition-colors disabled:opacity-50"
                  >
                    {completing ? 'COMPLETING...' : 'COMPLETE TOURNAMENT'}
                  </button>
                </div>
              )}

              {tournament?.status === 'completed' && tournament?.winner_id && (
                <div className="mt-4 p-4 bg-[#22C55E]/10 border border-[#22C55E]" data-testid="winner-announcement">
                  <div className="flex items-center gap-3">
                    <Trophy size={32} weight="duotone" className="text-[#22C55E]" />
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">WINNER</p>
                      <p className="text-lg font-bold text-white">
                        {tournament?.participants?.find(p => p.user_id === tournament?.winner_id)?.username || 'Unknown'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Participants */}
            <div className="border border-[#262626] bg-[#141414] p-6" data-testid="participants-section">
              <div className="flex items-center gap-2 mb-4">
                <Users size={24} weight="duotone" className="text-[#007AFF]" />
                <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>PARTICIPANTS</h3>
              </div>
              <div className="space-y-2">
                {tournament?.participants?.map((participant, idx) => (
                  <div key={participant.user_id} className="flex items-center justify-between p-3 bg-[#0A0A0A] border border-[#262626]" data-testid={`participant-${idx}`}>
                    <span className="font-bold text-white">{participant.username}</span>
                    <span className="text-xs text-[#A3A3A3]">{new Date(participant.joined_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Chat */}
          <div className="border border-[#262626] bg-[#141414] flex flex-col h-[600px]" data-testid="chat-section">
            <div className="p-4 border-b border-[#262626]">
              <h3 className="text-lg font-bold" style={{fontFamily: 'Chivo'}}>CHAT</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg) => (
                <div key={msg.id} className="" data-testid={`chat-message-${msg.id}`}>
                  <p className="text-xs text-[#A3A3A3] mb-1">
                    <span className="font-bold text-white">{msg.username}</span> • {new Date(msg.timestamp).toLocaleTimeString()}
                  </p>
                  <p className="text-sm text-[#A3A3A3]">{msg.message}</p>
                </div>
              ))}
            </div>

            {isParticipant && (
              <form onSubmit={handleSendMessage} className="p-4 border-t border-[#262626]" data-testid="chat-form">
                <div className="flex gap-2">
                  <input
                    data-testid="chat-input"
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 px-4 py-2 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
                  />
                  <button
                    data-testid="chat-send-btn"
                    type="submit"
                    className="px-4 py-2 bg-[#FF3B30] text-white hover:bg-[#D62F26] transition-colors"
                  >
                    <PaperPlaneRight size={20} weight="bold" />
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default TournamentDetails;