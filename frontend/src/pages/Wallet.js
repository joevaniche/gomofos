import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Wallet as WalletIcon, ArrowUp, ArrowDown, Coins, Gift } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Wallet() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [bonusStatus, setBonusStatus] = useState({ can_claim: false, hours_remaining: 0 });
  const [claiming, setClaiming] = useState(false);

  useEffect(() => {
    loadTransactions();
    loadBonusStatus();
  }, []);

  const loadTransactions = async () => {
    try {
      const { data } = await axios.get(`${API}/wallet/transactions`, { withCredentials: true });
      setTransactions(data);
    } catch (e) {
      console.error('Failed to load transactions');
    }
  };

  const loadBonusStatus = async () => {
    try {
      const { data } = await axios.get(`${API}/wallet/daily-bonus/status`, { withCredentials: true });
      setBonusStatus(data);
    } catch (e) {
      console.error('Failed to load bonus status');
    }
  };

  const handleClaimBonus = async () => {
    setClaiming(true);
    try {
      const { data } = await axios.post(`${API}/wallet/daily-bonus`, {}, { withCredentials: true });
      toast.success(`+${data.amount} credits added to your wallet!`);
      await checkAuth();
      loadTransactions();
      loadBonusStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to claim bonus');
    } finally {
      setClaiming(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const referenceTypeLabel = (refType) => {
    const labels = {
      welcome_bonus: 'WELCOME BONUS',
      daily_bonus: 'DAILY BONUS',
      deposit: 'DEPOSIT',
      tournament_win: 'TOURNAMENT WIN',
      tournament_stake: 'TOURNAMENT STAKE',
    };
    return labels[refType] || refType.toUpperCase();
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Navigation */}
      <nav className="border-b border-[#262626] bg-[#0A0A0A]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-black tracking-tighter text-white" style={{fontFamily: 'Chivo'}}>ESPORTS BET</h1>
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/players" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-players">PLAYERS</Link>
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-leaderboard">LEADERBOARD</Link>
            <Link to="/profile" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-profile">PROFILE</Link>
            <Link to="/wallet" className="text-sm font-bold text-[#FF3B30] flex items-center gap-2" data-testid="nav-wallet">
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

      <div className="max-w-7xl mx-auto p-6">
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>YOUR CREDITS</h2>
          <p className="text-sm text-[#A3A3A3]">Play with virtual credits — no real money involved</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Balance + Daily Bonus Card */}
          <div className="border border-[#262626] bg-[#141414] p-8" data-testid="balance-card">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-2">CURRENT BALANCE</p>
            <div className="flex items-baseline gap-2 mb-8">
              <Coins size={48} weight="duotone" className="text-[#F59E0B]" />
              <span className="text-5xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{user?.wallet_balance?.toFixed(0) || '0'}</span>
              <span className="text-lg text-[#A3A3A3] font-bold">CREDITS</span>
            </div>

            <div className="border-t border-[#262626] pt-6">
              <div className="flex items-center gap-2 mb-3">
                <Gift size={20} weight="duotone" className="text-[#FF3B30]" />
                <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">DAILY BONUS</p>
              </div>
              {bonusStatus.can_claim ? (
                <>
                  <p className="text-sm text-white mb-4">Claim your free <span className="font-bold text-[#22C55E]">250 credits</span> — refreshes every 24 hours.</p>
                  <button
                    data-testid="claim-bonus-btn"
                    onClick={handleClaimBonus}
                    disabled={claiming}
                    className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    <Gift size={20} weight="bold" />
                    {claiming ? 'CLAIMING...' : 'CLAIM 250 FREE CREDITS'}
                  </button>
                </>
              ) : (
                <>
                  <p className="text-sm text-[#A3A3A3] mb-4">Next bonus available in <span className="font-bold text-white">{Math.floor(bonusStatus.hours_remaining)}h {Math.round((bonusStatus.hours_remaining % 1) * 60)}m</span></p>
                  <button
                    disabled
                    className="w-full px-6 py-3 bg-[#262626] text-[#525252] font-bold cursor-not-allowed"
                  >
                    ALREADY CLAIMED TODAY
                  </button>
                </>
              )}
            </div>

            <div className="mt-6 p-4 bg-[#0A0A0A] border border-[#262626]">
              <p className="text-xs text-[#A3A3A3] leading-relaxed">
                <span className="font-bold text-white">PLAY MONEY MODE:</span> Credits are virtual currency for entertainment only. No real money is involved. New users start with 1,000 free credits.
              </p>
            </div>
          </div>

          {/* Transaction History */}
          <div className="border border-[#262626] bg-[#141414] p-6" data-testid="transaction-history">
            <h3 className="text-xl font-bold mb-4" style={{fontFamily: 'Chivo'}}>TRANSACTION HISTORY</h3>

            {transactions.length === 0 ? (
              <p className="text-[#A3A3A3] text-center py-8">No transactions yet</p>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {transactions.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between p-3 bg-[#0A0A0A] border border-[#262626]" data-testid={`transaction-${tx.id}`}>
                    <div className="flex items-center gap-3">
                      {tx.type === 'credit' ? (
                        <div className="w-8 h-8 bg-[#22C55E]/10 flex items-center justify-center">
                          <ArrowUp size={16} weight="bold" className="text-[#22C55E]" />
                        </div>
                      ) : (
                        <div className="w-8 h-8 bg-[#EF4444]/10 flex items-center justify-center">
                          <ArrowDown size={16} weight="bold" className="text-[#EF4444]" />
                        </div>
                      )}
                      <div>
                        <p className="text-sm font-bold text-white">{referenceTypeLabel(tx.reference_type)}</p>
                        <p className="text-xs text-[#A3A3A3]">{new Date(tx.timestamp).toLocaleString()}</p>
                      </div>
                    </div>
                    <p className="text-lg font-bold" style={{color: tx.type === 'credit' ? '#22C55E' : '#EF4444'}}>
                      {tx.type === 'credit' ? '+' : '-'}{tx.amount.toFixed(0)} CR
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Wallet;
