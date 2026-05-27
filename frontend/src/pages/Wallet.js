import React, { useEffect, useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Wallet as WalletIcon, ArrowUp, ArrowDown } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Wallet() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [transactions, setTransactions] = useState([]);
  const [depositAmount, setDepositAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(false);

  useEffect(() => {
    loadTransactions();
    
    // Check for Stripe return
    const params = new URLSearchParams(location.search);
    const sessionId = params.get('session_id');
    if (sessionId) {
      checkPaymentStatus(sessionId);
    }
  }, [location]);

  const loadTransactions = async () => {
    try {
      const { data } = await axios.get(`${API}/wallet/transactions`, { withCredentials: true });
      setTransactions(data);
    } catch (e) {
      console.error('Failed to load transactions');
    }
  };

  const checkPaymentStatus = async (sessionId) => {
    setCheckingStatus(true);
    let attempts = 0;
    const maxAttempts = 5;
    const pollInterval = 2000;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setCheckingStatus(false);
        toast.error('Payment status check timed out');
        return;
      }

      try {
        const { data } = await axios.get(`${API}/wallet/deposit/status/${sessionId}`, { withCredentials: true });
        
        if (data.status === 'completed') {
          toast.success(`Deposit successful! $${data.amount} added to your wallet`);
          await checkAuth();
          loadTransactions();
          setCheckingStatus(false);
          window.history.replaceState({}, '', '/wallet');
          return;
        } else if (data.status === 'expired') {
          toast.error('Payment session expired');
          setCheckingStatus(false);
          return;
        }

        attempts++;
        setTimeout(poll, pollInterval);
      } catch (e) {
        setCheckingStatus(false);
        toast.error('Failed to check payment status');
      }
    };

    poll();
  };

  const handleDeposit = async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(depositAmount);
    if (amount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    setLoading(true);
    try {
      const originUrl = window.location.origin;
      const { data } = await axios.post(`${API}/wallet/deposit`, { amount, origin_url: originUrl }, { withCredentials: true });
      window.location.href = data.checkout_url;
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create deposit');
      setLoading(false);
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
            <Link to="/games" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-games">GAMES</Link>
            <Link to="/leaderboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-leaderboard">LEADERBOARD</Link>
            <Link to="/wallet" className="text-sm font-bold text-[#FF3B30] flex items-center gap-2" data-testid="nav-wallet">
              <WalletIcon size={18} weight="bold" />
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
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>WALLET</h2>
          <p className="text-sm text-[#A3A3A3]">Manage your funds</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Balance Card */}
          <div className="border border-[#262626] bg-[#141414] p-8" data-testid="balance-card">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-2">CURRENT BALANCE</p>
            <div className="flex items-baseline gap-2 mb-6">
              <span className="text-5xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>${user?.wallet_balance?.toFixed(2) || '0.00'}</span>
            </div>
            
            {checkingStatus && (
              <div className="mb-4 p-4 bg-[#007AFF]/10 border border-[#007AFF]">
                <p className="text-sm text-white">Checking payment status...</p>
              </div>
            )}

            <form onSubmit={handleDeposit} data-testid="deposit-form">
              <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">DEPOSIT AMOUNT (USD)</label>
              <input
                data-testid="deposit-amount-input"
                type="number"
                step="0.01"
                min="1"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
                required
                disabled={loading || checkingStatus}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30] mb-4"
                placeholder="10.00"
              />
              <button
                data-testid="deposit-submit-btn"
                type="submit"
                disabled={loading || checkingStatus}
                className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <ArrowUp size={20} weight="bold" />
                {loading ? 'PROCESSING...' : 'DEPOSIT FUNDS'}
              </button>
            </form>
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
                        <p className="text-sm font-bold text-white">{tx.reference_type.toUpperCase()}</p>
                        <p className="text-xs text-[#A3A3A3]">{new Date(tx.timestamp).toLocaleString()}</p>
                      </div>
                    </div>
                    <p className="text-lg font-bold" style={{color: tx.type === 'credit' ? '#22C55E' : '#EF4444'}}>
                      {tx.type === 'credit' ? '+' : '-'}${tx.amount.toFixed(2)}
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