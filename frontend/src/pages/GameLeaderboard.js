import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import TopNav from '../components/TopNav';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, Trophy } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function GameLeaderboard() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/games/${id}/leaderboard`, { withCredentials: true })
      .then(r => setData(r.data))
      .catch(() => { toast.error('Failed to load leaderboard'); navigate('/games'); })
      .finally(() => setLoading(false));
  }, [id, navigate]);

  return (
    <div className="min-h-screen">
      <TopNav />
      <div className="max-w-5xl mx-auto p-6">
        <Link to="/games" className="text-sm text-[#A3A3A3] hover:text-white flex items-center gap-1 mb-6" data-testid="back-to-games">
          <ArrowLeft size={16} weight="bold" /> All games
        </Link>
        {loading || !data ? (
          <p className="text-[#A3A3A3]">Loading...</p>
        ) : (
          <>
            <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">{data.category || 'GAME'} · {data.platform}</p>
                <h2 className="text-3xl font-black tracking-tighter" style={{fontFamily:'Chivo'}}>{data.game_name} — LEADERBOARD</h2>
              </div>
              <Trophy size={42} weight="duotone" className="text-[#F59E0B]" />
            </div>
            {data.rows.length === 0 ? (
              <div className="border border-[#262626] p-12 text-center bg-[#141414]" data-testid="no-game-results">
                <p className="text-[#A3A3A3]">No completed matches on this game yet.</p>
              </div>
            ) : (
              <div className="border border-[#262626] bg-[#141414]/85 overflow-x-auto" data-testid="game-leaderboard-table">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#262626] text-left text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">
                      <th className="px-4 py-3 w-12">#</th>
                      <th className="px-4 py-3">Player</th>
                      <th className="px-4 py-3 text-center">Wins</th>
                      <th className="px-4 py-3 text-center">Losses</th>
                      <th className="px-4 py-3 text-center">Win %</th>
                      <th className="px-4 py-3 text-right">Net CR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((r, i) => {
                      const wr = r.total_matches > 0 ? Math.round((r.wins / r.total_matches) * 100) : 0;
                      const net = r.net_credits;
                      const netClass = net > 0 ? 'text-[#22C55E]' : net < 0 ? 'text-[#EF4444]' : 'text-[#A3A3A3]';
                      const isMe = r.user_id === user?.id;
                      return (
                        <tr key={r.user_id} data-testid={`row-${r.user_id}`} className={`border-b border-[#262626] hover:bg-[#1A1A1A]/60 ${isMe ? 'bg-[#FF3B30]/10' : ''}`}>
                          <td className="px-4 py-3 text-white font-black tracking-tighter" style={{fontFamily:'Chivo'}}>{i + 1}</td>
                          <td className="px-4 py-3">
                            <Link to={`/profile/${r.user_id}`} className="flex items-center gap-2 text-white font-bold hover:text-[#FF3B30]">
                              {(r.equipped_thumbs || []).map((t, k) => (
                                <img key={k} src={t.thumb_url} alt={t.name} title={t.name} className="w-5 h-5 object-cover border border-[#262626]" />
                              ))}
                              {r.username}{isMe && <span className="ml-1 text-xs text-[#FF3B30]">(YOU)</span>}
                            </Link>
                          </td>
                          <td className="px-4 py-3 text-center text-[#22C55E] font-bold">{r.wins}</td>
                          <td className="px-4 py-3 text-center text-[#EF4444] font-bold">{r.losses}</td>
                          <td className="px-4 py-3 text-center text-white">{wr}%</td>
                          <td className={`px-4 py-3 text-right font-black tracking-tighter ${netClass}`} style={{fontFamily:'Chivo'}}>
                            {net > 0 ? '+' : ''}{net} CR
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default GameLeaderboard;
