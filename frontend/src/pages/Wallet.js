import React, { useEffect, useState } from 'react';
import Logo from '../components/Logo';
import { useNavigate, Link } from 'react-router-dom';
import TopNav from '../components/TopNav';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Wallet as WalletIcon, ArrowUp, ArrowDown, Coins } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Wallet() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);

  useEffect(() => {
    loadTransactions();
  }, []);

  const loadTransactions = async () => {
    try {
      const { data } = await axios.get(`${API}/wallet/transactions`, { withCredentials: true });
      setTransactions(data);
    } catch (e) {
      console.error('Failed to load transactions');
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
    <div className="min-h-screen">
      {/* Navigation */}
      <TopNav />

      <div className="max-w-7xl mx-auto p-6">
        <div className="mb-8">
          <h2 className="text-3xl font-black tracking-tighter text-white mb-2" style={{fontFamily: 'Chivo'}}>YOUR CREDITS</h2>
          <p className="text-sm text-[#A3A3A3]">Play with virtual credits — no real money involved</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Balance + Daily Bonus Card */}
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-8" data-testid="balance-card">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-2">CURRENT BALANCE</p>
            <div className="flex items-baseline gap-2 mb-8">
              <Coins size={48} weight="duotone" className="text-[#F59E0B]" />
              <span className="text-5xl font-black tracking-tighter" style={{fontFamily: 'Chivo'}}>{user?.wallet_balance?.toFixed(0) || '0'}</span>
              <span className="text-lg text-[#A3A3A3] font-bold">CREDITS</span>
            </div>

            <div className="border-t border-[#262626] pt-6">
              <p className="text-sm text-[#A3A3A3] mb-2">
                New players start with <span className="font-bold text-[#22C55E]">1,000 free credits</span>. Need more? Top up below — credits are non-refundable.
              </p>
            </div>

            <div className="mt-6 p-4 bg-[#0A0A0A] border border-[#262626]">
              <p className="text-xs text-[#A3A3A3] leading-relaxed">
                <span className="font-bold text-white">PLAY MONEY MODE:</span> Credits are virtual currency for entertainment only. No real money is involved. New users start with 1,000 free credits.
              </p>
            </div>
          </div>

          {/* Transaction History */}
          <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="transaction-history">
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
