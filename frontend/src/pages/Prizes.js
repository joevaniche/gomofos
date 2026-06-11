import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import Logo from '../components/Logo';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, Trophy, Medal, Crown, Fire, CoinVertical, Check, X, Plus, Pencil } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Icon name -> phosphor component mapping for badges
export const BADGE_ICONS = {
  trophy: Trophy, medal: Medal, crown: Crown, fire: Fire, 'coin-vertical': CoinVertical,
};

const RARITY_COLORS = {
  common: 'border-[#A3A3A3] text-[#A3A3A3]',
  rare: 'border-[#007AFF] text-[#007AFF]',
  epic: 'border-[#A855F7] text-[#A855F7]',
  legendary: 'border-[#F59E0B] text-[#F59E0B]',
};

function PrizeIcon({ kind, asset, size = 32 }) {
  if (kind === 'badge') {
    const Icon = BADGE_ICONS[asset] || Trophy;
    return <Icon size={size} weight="duotone" />;
  }
  if (kind === 'frame') {
    return <div className="rounded-full border-4" style={{ width: size, height: size, borderColor: asset || '#FF3B30' }} />;
  }
  // title
  return <span className="text-sm font-black tracking-tighter" style={{ fontFamily: 'Chivo' }}>{asset || '✦'}</span>;
}

function Prizes() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [prizes, setPrizes] = useState([]);
  const [inventory, setInventory] = useState({ items: [], equipped: {} });
  const [filterKind, setFilterKind] = useState('all');
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState(null);
  const isAdmin = user?.role === 'admin';
  const [adminForm, setAdminForm] = useState({ open: false, editing: null, name: '', kind: 'badge', cost: 100, asset: '', description: '', rarity: 'common' });

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, []);

  const reload = async () => {
    setLoading(true);
    try {
      const [prizesRes, invRes] = await Promise.all([
        axios.get(`${API}/prizes`, { withCredentials: true }),
        user ? axios.get(`${API}/users/${user.id}/inventory`, { withCredentials: true }) : Promise.resolve({ data: { items: [], equipped: {} } }),
      ]);
      setPrizes(prizesRes.data);
      setInventory(invRes.data);
    } catch { toast.error('Failed to load prizes'); }
    finally { setLoading(false); }
  };

  const ownedIds = new Set(inventory.items.map(i => i.prize_id));

  const redeem = async (p) => {
    if ((user?.wallet_balance || 0) < p.cost) {
      toast.error(`Need ${p.cost} CR — you have ${(user?.wallet_balance || 0).toFixed(0)} CR`);
      return;
    }
    if (!window.confirm(`Redeem "${p.name}" for ${p.cost} CR?`)) return;
    setRedeeming(p.id);
    try {
      await axios.post(`${API}/prizes/${p.id}/redeem`, {}, { withCredentials: true });
      toast.success(`${p.name} added to your inventory`);
      await checkAuth();
      reload();
    } catch (e) { toast.error(e.response?.data?.detail || 'Redeem failed'); }
    finally { setRedeeming(null); }
  };

  const equip = async (item) => {
    try {
      await axios.post(`${API}/users/me/equip`, { inventory_id: item.inventory_id }, { withCredentials: true });
      toast.success(`${item.name} equipped`);
      reload();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };
  const unequip = async (kind) => {
    try {
      await axios.post(`${API}/users/me/unequip/${kind}`, {}, { withCredentials: true });
      reload();
    } catch (e) { toast.error('Failed'); }
  };

  // --- Admin create/edit ---
  const submitAdmin = async () => {
    const payload = {
      name: adminForm.name.trim(),
      kind: adminForm.kind,
      cost: parseFloat(adminForm.cost),
      asset: adminForm.asset.trim(),
      description: adminForm.description.trim(),
      rarity: adminForm.rarity,
      active: true,
    };
    if (!payload.name || !payload.cost) { toast.error('Name + cost required'); return; }
    try {
      if (adminForm.editing) {
        await axios.patch(`${API}/admin/prizes/${adminForm.editing}`, payload, { withCredentials: true });
        toast.success('Prize updated');
      } else {
        await axios.post(`${API}/admin/prizes`, payload, { withCredentials: true });
        toast.success('Prize created');
      }
      setAdminForm({ open: false, editing: null, name: '', kind: 'badge', cost: 100, asset: '', description: '', rarity: 'common' });
      reload();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };
  const disablePrize = async (id) => {
    if (!window.confirm('Disable this prize? Users who already own it keep it.')) return;
    try { await axios.delete(`${API}/admin/prizes/${id}`, { withCredentials: true }); toast.success('Disabled'); reload(); }
    catch { toast.error('Failed'); }
  };
  const startEdit = (p) => {
    setAdminForm({ open: true, editing: p.id, name: p.name, kind: p.kind, cost: p.cost, asset: p.asset, description: p.description, rarity: p.rarity });
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const filtered = prizes.filter(p => filterKind === 'all' || p.kind === filterKind);

  return (
    <div className="min-h-screen">
      <nav className="border-b border-[#262626] bg-[#0A0A0A]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-dashboard">DASHBOARD</Link>
            <Link to="/tournaments" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-tournaments">TOURNAMENTS</Link>
            <Link to="/competitions" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-competitions">COMPETITIONS</Link>
            <Link to="/prizes" className="text-sm font-bold text-[#FF3B30]" data-testid="nav-prizes">PRIZES</Link>
            <Link to="/profile" className="text-sm font-bold text-[#A3A3A3] hover:text-white" data-testid="nav-profile">PROFILE</Link>
            <Link to="/wallet" className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-wallet">
              <Coins size={18} weight="bold" />{user?.wallet_balance?.toFixed(0) || '0'} CR
            </Link>
            <button onClick={handleLogout} className="text-sm font-bold text-[#A3A3A3] hover:text-white flex items-center gap-2" data-testid="nav-logout">
              <SignOut size={18} weight="bold" />LOGOUT
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
          <div>
            <h2 className="text-3xl font-black tracking-tighter mb-1" style={{fontFamily:'Chivo'}}>PRIZE STORE</h2>
            <p className="text-sm text-[#A3A3A3]">Burn credits on badges, titles, and avatar frames — let everyone know how much you've grinded.</p>
          </div>
          {isAdmin && (
            <button data-testid="admin-new-prize-btn"
              onClick={() => setAdminForm({ ...adminForm, open: true, editing: null, name:'', kind:'badge', cost:100, asset:'', description:'', rarity:'common' })}
              className="px-5 py-2 bg-transparent border border-[#F59E0B] text-[#F59E0B] font-bold hover:bg-[#F59E0B] hover:text-white transition-colors flex items-center gap-2">
              <Plus size={16} weight="bold" /> NEW PRIZE (ADMIN)
            </button>
          )}
        </div>

        {/* Filter chips */}
        <div className="flex gap-2 mb-6 overflow-x-auto" data-testid="prize-filters">
          {['all', 'badge', 'title', 'frame'].map(k => (
            <button key={k} data-testid={`filter-${k}`}
              onClick={() => setFilterKind(k)}
              className={`px-4 py-2 text-xs font-bold uppercase tracking-[0.1em] border transition-colors ${filterKind === k ? 'bg-[#FF3B30] border-[#FF3B30] text-white' : 'bg-transparent border-[#3F3F3F] text-[#A3A3A3] hover:border-white hover:text-white'}`}>
              {k === 'all' ? 'ALL' : k + 'S'}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="text-[#A3A3A3]">Loading prizes...</p>
        ) : filtered.length === 0 ? (
          <p className="text-[#A3A3A3]">No prizes yet.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4" data-testid="prizes-grid">
            {filtered.map(p => {
              const owned = ownedIds.has(p.id);
              const canAfford = (user?.wallet_balance || 0) >= p.cost;
              const rarity = RARITY_COLORS[p.rarity] || RARITY_COLORS.common;
              return (
                <div key={p.id} data-testid={`prize-${p.id}`} className={`border-2 ${rarity.split(' ')[0]} bg-[#141414] p-4 flex flex-col items-center text-center`}>
                  <span className={`text-[10px] font-bold uppercase tracking-[0.15em] ${rarity.split(' ')[1]} mb-3`}>{p.rarity}</span>
                  <div className="h-16 flex items-center justify-center mb-3 text-white">
                    <PrizeIcon kind={p.kind} asset={p.asset} size={48} />
                  </div>
                  <p className="text-sm font-bold text-white">{p.name}</p>
                  <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mb-1">{p.kind}</p>
                  {p.description && <p className="text-xs text-[#A3A3A3] mb-2 line-clamp-2 min-h-[2.5em]">{p.description}</p>}
                  <p className="text-xl font-black tracking-tighter text-white mt-1 mb-3" style={{fontFamily:'Chivo'}}>{p.cost} CR</p>
                  {owned ? (
                    <span className="w-full text-xs font-bold uppercase tracking-[0.1em] text-[#22C55E] py-2 border border-[#22C55E]/40 flex items-center justify-center gap-1">
                      <Check size={14} weight="bold" /> OWNED
                    </span>
                  ) : (
                    <button data-testid={`redeem-${p.id}`} disabled={!canAfford || redeeming === p.id} onClick={() => redeem(p)}
                      className="w-full px-3 py-2 bg-[#FF3B30] text-white font-bold text-xs hover:bg-[#D62F26] transition-colors disabled:opacity-50">
                      {redeeming === p.id ? 'REDEEMING...' : canAfford ? 'REDEEM' : 'NEED MORE CR'}
                    </button>
                  )}
                  {isAdmin && (
                    <div className="mt-2 w-full flex gap-1">
                      <button onClick={() => startEdit(p)} data-testid={`edit-prize-${p.id}`}
                        className="flex-1 px-2 py-1 text-[10px] font-bold border border-[#3F3F3F] text-[#A3A3A3] hover:border-white hover:text-white">
                        <Pencil size={10} weight="bold" /> EDIT
                      </button>
                      <button onClick={() => disablePrize(p.id)} data-testid={`disable-prize-${p.id}`}
                        className="flex-1 px-2 py-1 text-[10px] font-bold border border-[#3F3F3F] text-[#A3A3A3] hover:border-[#EF4444] hover:text-[#EF4444]">
                        DISABLE
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* My inventory */}
        {user && (
          <div className="mt-12">
            <h3 className="text-2xl font-bold mb-4" style={{fontFamily:'Chivo'}}>MY INVENTORY</h3>
            {inventory.items.length === 0 ? (
              <p className="text-[#A3A3A3] text-sm">No prizes yet — redeem one from the catalog above.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {inventory.items.map(i => (
                  <div key={i.inventory_id} data-testid={`inventory-${i.inventory_id}`}
                    className={`border ${i.is_equipped ? 'border-[#22C55E] bg-[#0A2615]' : 'border-[#262626] bg-[#141414]'} p-4 flex flex-col items-center text-center`}>
                    <div className="h-12 flex items-center justify-center mb-2 text-white">
                      <PrizeIcon kind={i.kind} asset={i.asset} size={36} />
                    </div>
                    <p className="text-sm font-bold text-white">{i.name}</p>
                    <p className="text-[10px] font-bold uppercase text-[#A3A3A3] mb-3">{i.kind}</p>
                    {i.is_equipped ? (
                      <button data-testid={`unequip-${i.inventory_id}`} onClick={() => unequip(i.kind)}
                        className="w-full px-3 py-1.5 text-xs font-bold border border-[#22C55E] text-[#22C55E] hover:bg-[#22C55E] hover:text-white transition-colors">
                        ✓ EQUIPPED — UNEQUIP
                      </button>
                    ) : (
                      <button data-testid={`equip-${i.inventory_id}`} onClick={() => equip(i)}
                        className="w-full px-3 py-1.5 text-xs font-bold bg-[#FF3B30] text-white hover:bg-[#D62F26] transition-colors">
                        EQUIP
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Admin form modal */}
      {adminForm.open && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setAdminForm({ ...adminForm, open: false })}>
          <div className="bg-[#141414] border border-[#262626] max-w-lg w-full p-6 space-y-4" onClick={e=>e.stopPropagation()} data-testid="admin-prize-form">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold" style={{fontFamily:'Chivo'}}>{adminForm.editing ? 'EDIT PRIZE' : 'NEW PRIZE'}</h3>
              <button onClick={() => setAdminForm({ ...adminForm, open: false })} className="text-[#A3A3A3] hover:text-white"><X size={24} weight="bold" /></button>
            </div>
            <input data-testid="admin-prize-name" placeholder="Prize name" value={adminForm.name} onChange={e=>setAdminForm({...adminForm, name:e.target.value})}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
            <div className="grid grid-cols-3 gap-2">
              {['badge', 'title', 'frame'].map(k => (
                <button key={k} type="button" onClick={() => setAdminForm({...adminForm, kind:k})}
                  className={`px-3 py-2 text-xs font-bold uppercase border ${adminForm.kind === k ? 'bg-[#FF3B30] border-[#FF3B30] text-white' : 'bg-transparent border-[#3F3F3F] text-[#A3A3A3]'}`}>{k}</button>
              ))}
            </div>
            <input data-testid="admin-prize-asset" placeholder={adminForm.kind === 'badge' ? 'Icon name (trophy/medal/crown/fire/coin-vertical)' : adminForm.kind === 'frame' ? 'Hex colour e.g. #FF3B30' : 'Title text e.g. CHAMPION'} value={adminForm.asset} onChange={e=>setAdminForm({...adminForm, asset:e.target.value})}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
            <input data-testid="admin-prize-description" placeholder="Description (optional)" value={adminForm.description} onChange={e=>setAdminForm({...adminForm, description:e.target.value})}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
            <div className="grid grid-cols-2 gap-2">
              <input data-testid="admin-prize-cost" type="number" min="1" placeholder="Cost (CR)" value={adminForm.cost} onChange={e=>setAdminForm({...adminForm, cost:e.target.value})}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
              <select data-testid="admin-prize-rarity" value={adminForm.rarity} onChange={e=>setAdminForm({...adminForm, rarity:e.target.value})}
                className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]">
                <option value="common">Common</option><option value="rare">Rare</option><option value="epic">Epic</option><option value="legendary">Legendary</option>
              </select>
            </div>
            <button data-testid="admin-prize-save" onClick={submitAdmin}
              className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors">
              {adminForm.editing ? 'SAVE CHANGES' : 'CREATE PRIZE'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Prizes;
