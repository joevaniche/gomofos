import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { UserPlus, X, EnvelopeSimple, Check, Clock } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ReferAMofo() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [data, setData] = useState({ bonus_per_signup: 500, total_earned: 0, referrals: [] });

  useEffect(() => { if (open) load(); }, [open]);

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/referrals/mine`, { withCredentials: true });
      setData(data);
    } catch {}
  };

  const send = async () => {
    if (!email.trim()) { toast.error('Enter an email'); return; }
    setSending(true);
    try {
      await axios.post(`${API}/referrals/invite`, { email: email.trim() }, { withCredentials: true });
      toast.success(`Invite sent — you'll get 500 CR when they sign up`);
      setEmail('');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to send invite');
    } finally { setSending(false); }
  };

  return (
    <>
      <div className="border border-[#FF3B30]/40 bg-gradient-to-r from-[#FF3B30]/10 to-transparent p-4 mb-6 flex items-center justify-between gap-3 flex-wrap" data-testid="refer-banner">
        <div className="flex items-center gap-3">
          <UserPlus size={28} weight="duotone" className="text-[#FF3B30]" />
          <div>
            <p className="text-sm font-bold text-white">REFER A MOFO — get <span className="text-[#22C55E]">500 CR</span> per friend</p>
            <p className="text-xs text-[#A3A3A3]">When they sign up using your link, the bonus is added automatically.</p>
          </div>
        </div>
        <button onClick={() => setOpen(true)} data-testid="open-refer-modal"
          className="px-5 py-2 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors">
          REFER A MOFO
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setOpen(false)}>
          <div className="bg-[#141414] border border-[#262626] max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e=>e.stopPropagation()} data-testid="refer-modal">
            <div className="flex items-center justify-between p-6 border-b border-[#262626]">
              <h3 className="text-xl font-bold flex items-center gap-2" style={{fontFamily:'Chivo'}}>
                <UserPlus size={22} weight="duotone" className="text-[#FF3B30]" /> REFER A MOFO
              </h3>
              <button onClick={() => setOpen(false)} className="text-[#A3A3A3] hover:text-white" data-testid="close-refer-modal"><X size={24} weight="bold" /></button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-[#A3A3A3]">Drop their email — we'll send an invite. The moment they sign up via the link, <span className="text-[#22C55E] font-bold">+{data.bonus_per_signup} CR</span> lands in your wallet.</p>
              <div className="flex gap-2">
                <input data-testid="refer-email-input" type="email" placeholder="friend@example.com" value={email}
                  onChange={e=>setEmail(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()}
                  className="flex-1 px-3 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
                <button data-testid="refer-send-btn" disabled={sending} onClick={send}
                  className="px-5 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50 flex items-center gap-2">
                  <EnvelopeSimple size={16} weight="bold" /> {sending ? 'SENDING...' : 'SEND INVITE'}
                </button>
              </div>

              <div className="border-t border-[#262626] pt-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3]">YOUR INVITES ({data.referrals.length})</p>
                  <p className="text-xs font-bold text-[#22C55E]">EARNED: {data.total_earned} CR</p>
                </div>
                {data.referrals.length === 0 ? (
                  <p className="text-xs text-[#A3A3A3]">No invites sent yet.</p>
                ) : (
                  <div className="space-y-1 max-h-64 overflow-y-auto" data-testid="refer-list">
                    {data.referrals.map(r => (
                      <div key={r.id} className="flex items-center justify-between text-xs py-2 px-3 bg-[#0A0A0A] border border-[#262626]">
                        <span className="text-white truncate flex-1">{r.invitee_email}</span>
                        {r.status === 'credited' ? (
                          <span className="text-[#22C55E] font-bold flex items-center gap-1 ml-2"><Check size={12} weight="bold" /> SIGNED UP — +500 CR</span>
                        ) : (
                          <span className="text-[#F59E0B] font-bold flex items-center gap-1 ml-2"><Clock size={12} weight="bold" /> PENDING</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
