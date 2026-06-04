import React, { useEffect, useState, useRef } from 'react';
import Logo from '../components/Logo';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, Users, Trophy, PaperPlaneRight, Upload, Image as ImageIcon, WifiHigh, WifiLow, WifiMedium, ShieldWarning, CheckCircle, XLogo, VideoCamera } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const WS_URL = process.env.REACT_APP_BACKEND_URL.replace(/^http/, 'ws');

function TournamentDetails() {
  const { id } = useParams();
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [tournament, setTournament] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);
  const [submittingResult, setSubmittingResult] = useState(false);
  const [adminResolving, setAdminResolving] = useState(false);
  const [selectedWinner, setSelectedWinner] = useState('');
  const [evidence, setEvidence] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [showShareX, setShowShareX] = useState(false);
  const [latencyData, setLatencyData] = useState([]);
  const [currentLatency, setCurrentLatency] = useState(null);

  const wsRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const fileInputRef = useRef(null);

  // === LOAD DATA ===
  useEffect(() => {
    loadTournament();
    loadMessages();
    loadEvidence();
    loadLatencyData();
    const interval = setInterval(() => {
      loadMessages();
      loadTournament();
    }, 4000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // === LATENCY WEBSOCKET (only when in_progress) ===
  useEffect(() => {
    if (!tournament || tournament.status !== 'in_progress') return;
    if (!isParticipant) return;

    // Get JWT token from cookie - we can't read httpOnly cookie, so we use a separate /api/auth/ws-token
    // Easier: send credentials via cookie-based WebSocket (some servers support it). Here we use a query-token approach:
    // For simplicity, we request a short-lived token from a helper endpoint OR rely on cookie passing.
    // We'll do HTTP-based latency measurement as the simpler fallback that always works through Cloudflare.

    let active = true;
    const measureAndReport = async () => {
      if (!active) return;
      const start = performance.now();
      try {
        await axios.get(`${API}/leaderboard`, { withCredentials: true, timeout: 5000 });
        const rtt = Math.round(performance.now() - start);
        setCurrentLatency(rtt);
        try {
          await axios.post(`${API}/tournaments/${id}/latency?latency_ms=${rtt}`, {}, { withCredentials: true });
        } catch (e) { /* ignore */ }
      } catch (e) {
        setCurrentLatency(null);
      }
    };

    // Measure every 5 seconds
    measureAndReport();
    pingIntervalRef.current = setInterval(measureAndReport, 5000);

    return () => {
      active = false;
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tournament?.status, id]);

  const loadTournament = async () => {
    try {
      const { data } = await axios.get(`${API}/tournaments/${id}`, { withCredentials: true });
      setTournament(data);
      if (data.participants.length > 0 && !selectedWinner) {
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
    } catch (e) { /* ignore */ }
  };

  const loadEvidence = async () => {
    try {
      const { data } = await axios.get(`${API}/tournaments/${id}/evidence`, { withCredentials: true });
      setEvidence(data);
    } catch (e) { /* ignore */ }
  };

  const loadLatencyData = async () => {
    try {
      const { data } = await axios.get(`${API}/tournaments/${id}/latency`, { withCredentials: true });
      setLatencyData(data);
    } catch (e) { /* ignore */ }
  };

  // === ACTIONS ===
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

  const handleSubmitResult = async () => {
    if (!selectedWinner) {
      toast.error('Please select who won');
      return;
    }
    setSubmittingResult(true);
    try {
      const { data } = await axios.post(`${API}/tournaments/${id}/submit-result?claimed_winner_id=${selectedWinner}`, {}, { withCredentials: true });
      if (data.status === 'completed') {
        toast.success('Both players agreed! Tournament completed.');
        await checkAuth();
      } else if (data.status === 'disputed') {
        toast.error('Players disagreed — dispute opened. Upload evidence below.');
      } else {
        toast.success('Result submitted. Waiting for other player.');
      }
      loadTournament();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to submit result');
    } finally {
      setSubmittingResult(false);
    }
  };

  const handleAdminResolve = async () => {
    if (!selectedWinner) {
      toast.error('Please select a winner');
      return;
    }
    setAdminResolving(true);
    try {
      const { data } = await axios.post(`${API}/tournaments/${id}/complete?winner_user_id=${selectedWinner}`, {}, { withCredentials: true });
      toast.success(`Dispute resolved! Winner receives ${data.winner_amount.toFixed(0)} CR`);
      loadTournament();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to resolve dispute');
    } finally {
      setAdminResolving(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large (max 10MB)');
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      await axios.post(`${API}/tournaments/${id}/evidence`, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Evidence uploaded');
      loadEvidence();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to upload');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><p className="text-white">Loading...</p></div>;
  }

  const isParticipant = tournament?.participants?.some(p => p.user_id === user?.id);
  const isCreator = tournament?.creator_id === user?.id;
  const isAdmin = user?.role === 'admin';
  const canJoin = tournament?.status === 'open' && !isParticipant && tournament?.current_players < tournament?.max_players;
  const mySubmission = tournament?.participants?.find(p => p.user_id === user?.id)?.claimed_winner_id;
  const canSubmitResult = isParticipant && (tournament?.status === 'in_progress' || (tournament?.status === 'pending_confirmation' && !mySubmission));

  const latencyColor = (ms) => ms == null ? '#525252' : ms < 60 ? '#22C55E' : ms < 150 ? '#F59E0B' : '#EF4444';
  const LatencyIcon = currentLatency == null ? WifiLow : currentLatency < 60 ? WifiHigh : currentLatency < 150 ? WifiMedium : WifiLow;

  const statusBadge = {
    open: { label: 'OPEN', color: '#22C55E' },
    in_progress: { label: 'IN PROGRESS', color: '#F59E0B' },
    pending_confirmation: { label: 'AWAITING CONFIRMATION', color: '#007AFF' },
    disputed: { label: 'DISPUTED', color: '#EF4444' },
    completed: { label: 'COMPLETED', color: '#22C55E' },
  }[tournament?.status] || { label: tournament?.status?.toUpperCase(), color: '#A3A3A3' };

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
              <SignOut size={18} weight="bold" />LOGOUT
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* LEFT COLUMN */}
          <div className="lg:col-span-2 space-y-6">
            {/* Tournament Info */}
            <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6">
              <div className="flex items-start justify-between mb-2">
                <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">{tournament?.game_name}</p>
                <span className="text-xs font-bold uppercase tracking-[0.1em] px-3 py-1 border" style={{color: statusBadge.color, borderColor: statusBadge.color}} data-testid="tournament-status">
                  {statusBadge.label}
                </span>
              </div>
              <h2 className="text-3xl font-black tracking-tighter text-white mb-4" style={{fontFamily: 'Chivo'}}>STAKE: {tournament?.stake_amount} CR</h2>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">PLAYERS</p>
                  <p className="text-lg font-bold text-white">{tournament?.current_players}/{tournament?.max_players}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">PRIZE POOL</p>
                  <p className="text-lg font-bold text-[#22C55E]">{(tournament?.stake_amount * tournament?.current_players * 0.95).toFixed(0)} CR</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">HOST</p>
                  <p className="text-lg font-bold text-white">{tournament?.creator_username}</p>
                </div>
                {tournament?.status === 'in_progress' && isParticipant && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">YOUR LATENCY</p>
                    <div className="flex items-center gap-2">
                      <LatencyIcon size={20} weight="duotone" style={{color: latencyColor(currentLatency)}} />
                      <p className="text-lg font-bold" style={{color: latencyColor(currentLatency)}}>
                        {currentLatency != null ? `${currentLatency}ms` : '— ms'}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {canJoin && (
                <button data-testid="join-tournament-btn" onClick={handleJoin} disabled={joining} className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50">
                  {joining ? 'JOINING...' : `JOIN FOR ${tournament?.stake_amount} CR`}
                </button>
              )}

              {tournament?.status === 'in_progress' && !isParticipant && (
                <div className="p-4 bg-[#F59E0B]/10 border border-[#F59E0B]">
                  <p className="text-sm text-white">This tournament is full and in progress.</p>
                </div>
              )}

              {/* Result Submission */}
              {canSubmitResult && (
                <div className="mt-2 p-4 bg-[#0A0A0A] border border-[#262626]" data-testid="result-submission">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-2">WHO WON?</p>
                  <p className="text-sm text-[#A3A3A3] mb-3">Both players must agree. If you disagree, a dispute opens and screenshots can be uploaded as evidence.</p>
                  <select data-testid="winner-select" value={selectedWinner} onChange={(e) => setSelectedWinner(e.target.value)} className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30] mb-3">
                    {tournament?.participants?.map(p => (
                      <option key={p.user_id} value={p.user_id}>{p.username}{p.user_id === user?.id ? ' (You)' : ''}</option>
                    ))}
                  </select>
                  <button data-testid="submit-result-btn" onClick={handleSubmitResult} disabled={submittingResult} className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50">
                    {submittingResult ? 'SUBMITTING...' : 'SUBMIT RESULT'}
                  </button>
                </div>
              )}

              {mySubmission && tournament?.status === 'pending_confirmation' && (
                <div className="mt-2 p-4 bg-[#007AFF]/10 border border-[#007AFF]" data-testid="awaiting-confirmation">
                  <div className="flex items-center gap-2">
                    <CheckCircle size={24} weight="duotone" className="text-[#007AFF]" />
                    <div>
                      <p className="text-sm font-bold text-white">Your result submitted</p>
                      <p className="text-xs text-[#A3A3A3]">Waiting for other player(s) to confirm...</p>
                    </div>
                  </div>
                </div>
              )}

              {tournament?.status === 'disputed' && (
                <div className="mt-2 p-4 bg-[#EF4444]/10 border border-[#EF4444]" data-testid="dispute-banner">
                  <div className="flex items-center gap-2 mb-2">
                    <ShieldWarning size={24} weight="duotone" className="text-[#EF4444]" />
                    <p className="text-sm font-bold text-white">DISPUTE OPEN</p>
                  </div>
                  <p className="text-xs text-[#A3A3A3]">Players disagreed on the winner. Upload screenshot evidence below. An admin will review and resolve.</p>
                </div>
              )}

              {tournament?.status === 'completed' && tournament?.winner_id && (
                <div className="mt-2 p-4 bg-[#22C55E]/10 border border-[#22C55E]" data-testid="winner-announcement">
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-3">
                      <Trophy size={32} weight="duotone" className="text-[#22C55E]" />
                      <div>
                        <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">WINNER ({tournament?.resolution?.replace('_', ' ')})</p>
                        <p className="text-lg font-bold text-white">
                          {tournament?.participants?.find(p => p.user_id === tournament?.winner_id)?.username || 'Unknown'}
                        </p>
                      </div>
                    </div>
                    {tournament?.winner_id === user?.id && (
                      <button data-testid="share-on-x-btn" onClick={() => setShowShareX(true)}
                        className="px-4 py-2 bg-black text-white font-bold hover:bg-[#1A1A1A] border border-[#3F3F3F] transition-colors flex items-center gap-2 text-sm">
                        <XLogo size={16} weight="bold" /> FLEX ON X
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Admin Dispute Resolution */}
              {isAdmin && tournament?.status === 'disputed' && (
                <div className="mt-4 p-4 bg-[#FF3B30]/10 border border-[#FF3B30]" data-testid="admin-resolution">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#FF3B30] mb-2">ADMIN: RESOLVE DISPUTE</p>
                  <p className="text-xs text-[#A3A3A3] mb-3">Review evidence and latency data, then pick the winner.</p>
                  <select value={selectedWinner} onChange={(e) => setSelectedWinner(e.target.value)} className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30] mb-3">
                    {tournament?.participants?.map(p => (
                      <option key={p.user_id} value={p.user_id}>{p.username} (claimed: {tournament?.participants?.find(x => x.user_id === p.claimed_winner_id)?.username || 'none'})</option>
                    ))}
                  </select>
                  <button data-testid="admin-resolve-btn" onClick={handleAdminResolve} disabled={adminResolving} className="w-full px-6 py-3 bg-[#22C55E] text-white font-bold hover:bg-[#16A34A] transition-colors disabled:opacity-50">
                    {adminResolving ? 'RESOLVING...' : 'RESOLVE DISPUTE'}
                  </button>
                </div>
              )}
            </div>

            {/* Evidence Section (only when in_progress, pending, disputed, or completed) */}
            {tournament?.status !== 'open' && (
              <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="evidence-section">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <ImageIcon size={24} weight="duotone" className="text-[#FF3B30]" />
                    <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>EVIDENCE</h3>
                  </div>
                  {isParticipant && tournament?.status !== 'completed' && (
                    <>
                      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleUpload} className="hidden" data-testid="evidence-file-input" />
                      <button onClick={() => fileInputRef.current?.click()} disabled={uploading} data-testid="upload-evidence-btn" className="px-4 py-2 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50 flex items-center gap-2 text-xs">
                        <Upload size={16} weight="bold" />
                        {uploading ? 'UPLOADING...' : 'UPLOAD SCREENSHOT'}
                      </button>
                    </>
                  )}
                </div>
                {evidence.length === 0 ? (
                  <p className="text-sm text-[#A3A3A3] text-center py-4">No evidence uploaded yet.</p>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {evidence.map(item => (
                      <a key={item.id} href={`${API}/evidence/${item.id}/download`} target="_blank" rel="noreferrer" className="block border border-[#262626] hover:border-[#FF3B30] transition-colors" data-testid={`evidence-${item.id}`}>
                        <img src={`${API}/evidence/${item.id}/download`} alt="Evidence" className="w-full h-32 object-cover" />
                        <p className="text-xs text-[#A3A3A3] p-2">{item.username} • {new Date(item.uploaded_at).toLocaleString()}</p>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Latency Report (visible during/after match) */}
            {tournament?.status !== 'open' && latencyData.length > 0 && (
              <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="latency-section">
                <div className="flex items-center gap-2 mb-4">
                  <WifiHigh size={24} weight="duotone" className="text-[#007AFF]" />
                  <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>LATENCY REPORT</h3>
                </div>
                <div className="space-y-3">
                  {latencyData.map(player => (
                    <div key={player.user_id} className="p-3 bg-[#0A0A0A] border border-[#262626]" data-testid={`latency-${player.user_id}`}>
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-bold text-white">{player.username}</p>
                        <p className="text-xs text-[#A3A3A3]">{player.sample_count} samples</p>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div><span className="text-[#A3A3A3]">AVG: </span><span className="font-bold" style={{color: latencyColor(player.avg_ms)}}>{player.avg_ms}ms</span></div>
                        <div><span className="text-[#A3A3A3]">MIN: </span><span className="font-bold text-[#22C55E]">{player.min_ms}ms</span></div>
                        <div><span className="text-[#A3A3A3]">MAX: </span><span className="font-bold" style={{color: latencyColor(player.max_ms)}}>{player.max_ms}ms</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Participants */}
            <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="participants-section">
              <div className="flex items-center gap-2 mb-4">
                <Users size={24} weight="duotone" className="text-[#007AFF]" />
                <h3 className="text-xl font-bold" style={{fontFamily: 'Chivo'}}>PARTICIPANTS</h3>
              </div>
              <div className="space-y-2">
                {tournament?.participants?.map((p, idx) => (
                  <div key={p.user_id} className="flex items-center justify-between p-3 bg-[#0A0A0A] border border-[#262626]" data-testid={`participant-${idx}`}>
                    <div>
                      <span className="font-bold text-white">{p.username}</span>
                      {p.user_id === user?.id && <span className="ml-2 text-xs text-[#FF3B30]">(YOU)</span>}
                      {p.claimed_winner_id && (
                        <span className="ml-2 text-xs text-[#22C55E]">
                          ✓ submitted: {tournament?.participants?.find(x => x.user_id === p.claimed_winner_id)?.username}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-[#A3A3A3]">{new Date(p.joined_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* CHAT */}
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm flex flex-col h-[600px]" data-testid="chat-section">
            <div className="p-4 border-b border-[#262626]">
              <h3 className="text-lg font-bold" style={{fontFamily: 'Chivo'}}>CHAT</h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg) => (
                <div key={msg.id} data-testid={`chat-message-${msg.id}`}>
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
                  <input data-testid="chat-input" type="text" value={newMessage} onChange={(e) => setNewMessage(e.target.value)} placeholder="Type a message..." className="flex-1 px-4 py-2 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]" />
                  <button data-testid="chat-send-btn" type="submit" className="px-4 py-2 bg-[#FF3B30] text-white hover:bg-[#D62F26] transition-colors">
                    <PaperPlaneRight size={20} weight="bold" />
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
      {showShareX && (
        <ShareOnXModal
          tournament={tournament}
          user={user}
          onClose={() => setShowShareX(false)}
        />
      )}
    </div>
  );
}

function ShareOnXModal({ tournament, user, onClose }) {
  const [reels, setReels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReelId, setSelectedReelId] = useState('');

  useEffect(() => {
    axios.get(`${API}/highlights/user/${user.id}`)
      .then(r => {
        const list = r.data || [];
        setReels(list);
        // Auto-pick a matching-game reel if any
        if (tournament?.game_id) {
          const match = list.find(x => x.game_id === tournament.game_id);
          if (match) setSelectedReelId(match.id);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user.id, tournament?.game_id]);

  const winnerName = user.username;
  const opponentName = tournament?.participants?.find(p => p.user_id !== user.id)?.username || 'a Mofo';
  const gameName = tournament?.game_name || 'an online match';
  const pot = (tournament?.stake_amount || 0) * (tournament?.participants?.length || 2);

  const base = process.env.REACT_APP_BACKEND_URL;
  const shareUrl = `${base}/api/share/tournament/${tournament.id}` + (selectedReelId ? `?reel=${selectedReelId}` : '');
  const text = `Just took down @${opponentName} for ${pot.toFixed(0)} CR on @gomofos playing ${gameName}! 🏆`;
  const twitterIntent = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;

  const handleShare = () => {
    window.open(twitterIntent, '_blank', 'noopener,width=600,height=600');
    onClose();
  };

  const handleCopy = () => {
    navigator.clipboard?.writeText(`${text} ${shareUrl}`);
    toast.success('Copied to clipboard');
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="share-x-modal">
      <div className="bg-[#141414] border border-[#262626] max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-6 border-b border-[#262626]">
          <div className="flex items-center gap-2">
            <XLogo size={24} weight="bold" className="text-white" />
            <h3 className="text-xl font-bold" style={{ fontFamily: 'Chivo' }}>FLEX YOUR WIN</h3>
          </div>
          <button onClick={onClose} className="text-[#A3A3A3] hover:text-white text-2xl leading-none">×</button>
        </div>
        <div className="p-6 space-y-4">
          <div className="p-4 bg-[#0A0A0A] border border-[#262626]">
            <p className="text-sm text-white whitespace-pre-wrap">{text}</p>
            <p className="text-xs text-[#A3A3A3] mt-2 break-all">{shareUrl}</p>
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2 flex items-center gap-2">
              <VideoCamera size={14} weight="duotone" className="text-[#FF3B30]" /> ATTACH A HIGHLIGHT REEL (OPTIONAL)
            </label>
            {loading ? (
              <p className="text-sm text-[#A3A3A3]">Loading your reels...</p>
            ) : reels.length === 0 ? (
              <p className="text-xs text-[#A3A3A3]">You don't have any reels yet. Upload one from your profile to attach to future shares.</p>
            ) : (
              <select data-testid="share-reel-select" value={selectedReelId} onChange={(e) => setSelectedReelId(e.target.value)}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]">
                <option value="">No reel — text only</option>
                {reels.map(r => (
                  <option key={r.id} value={r.id}>{r.title} {r.game_name ? `· ${r.game_name}` : ''} · {Math.round(r.duration_sec || 0)}s</option>
                ))}
              </select>
            )}
            <p className="text-xs text-[#A3A3A3] mt-2">X embeds the linked card with your reel as a video preview.</p>
          </div>

          <div className="flex gap-3 pt-2">
            <button data-testid="post-to-x-btn" onClick={handleShare}
              className="flex-1 px-6 py-3 bg-black text-white font-bold hover:bg-[#1A1A1A] border border-[#3F3F3F] transition-colors flex items-center justify-center gap-2">
              <XLogo size={18} weight="bold" /> POST TO X
            </button>
            <button data-testid="copy-share-link-btn" onClick={handleCopy}
              className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">
              COPY
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TournamentDetails;
