import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import Logo from '../components/Logo';
import { useAuth } from '../contexts/AuthContext';
import { SignOut, Coins, Check, X, Plus, Pencil, Lock, Trophy as TrophyIcon, UploadSimple } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FEAT_TYPES = [
  { value: '', label: 'No requirement (anyone can buy)' },
  { value: 'tournament_wins', label: 'Total tournament wins' },
  { value: 'h2h_wins', label: 'Total head-to-head wins' },
  { value: 'wins_in_genre', label: 'Total wins in a game genre' },
  { value: 'streak', label: 'Current win streak (any game)' },
  { value: 'streak_in_genre', label: 'Streak in a specific genre' },
  { value: 'net_credits', label: 'Net credits earned' },
];

const FEAT_NEEDS_GENRE = (t) => t === 'wins_in_genre' || t === 'streak_in_genre';

const featSummary = (feat) => {
  if (!feat || !feat.type) return 'Anyone can buy';
  const c = feat.count;
  const g = feat.genre || '?';
  if (feat.type === 'tournament_wins') return `${c} tournament wins`;
  if (feat.type === 'h2h_wins') return `${c} head-to-head wins`;
  if (feat.type === 'wins_in_genre') return `${c} ${g} wins`;
  if (feat.type === 'streak') return `${c}-win streak`;
  if (feat.type === 'streak_in_genre') return `${c}-win streak in ${g}`;
  if (feat.type === 'net_credits') return `${c} net CR earned`;
  return feat.type;
};

function Prizes() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [prizes, setPrizes] = useState([]);
  const [inventory, setInventory] = useState({ items: [], equipped: {} });
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const isAdmin = user?.role === 'admin';
  const blankForm = { open: false, editing: null, name: '', cost: 100, image_url: '', thumb_url: '', feat_type: '', feat_count: 1, feat_genre: '' };
  const [form, setForm] = useState(blankForm);

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

  const seedCatalog = async () => {
    if (!window.confirm('Seed the default 12-prize catalog? Existing entries with the same name are skipped.')) return;
    setSeeding(true);
    try {
      const { data } = await axios.post(`${API}/admin/prizes/seed`, {}, { withCredentials: true });
      toast.success(`Seeded ${data.created} prizes (total ${data.total})`);
      reload();
    } catch (e) { toast.error(e.response?.data?.detail || 'Seed failed'); }
    finally { setSeeding(false); }
  };

  const redeem = async (p) => {
    if (!p.unlocked) {
      toast.error(`Locked — earn ${p.target} (you have ${Math.floor(p.progress)})`);
      return;
    }
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

  // --- Admin: image upload helpers ---
  const mainFileRef = useRef(null);
  const thumbFileRef = useRef(null);
  const [uploading, setUploading] = useState({ main: false, thumb: false });
  const uploadImage = async (file, kind) => {
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error('Image must be under 8 MB'); return; }
    setUploading({ ...uploading, [kind]: true });
    const fd = new FormData();
    fd.append('file', file);
    try {
      const { data } = await axios.post(`${API}/admin/prize-image?kind=${kind}`, fd, { withCredentials: true, headers: { 'Content-Type': 'multipart/form-data' } });
      const fullUrl = `${process.env.REACT_APP_BACKEND_URL}${data.url}`;
      setForm(f => kind === 'main' ? { ...f, image_url: fullUrl } : { ...f, thumb_url: fullUrl });
      toast.success(`${kind === 'main' ? 'Main' : 'Thumbnail'} image uploaded`);
    } catch (e) { toast.error(e.response?.data?.detail || 'Upload failed'); }
    finally { setUploading(u => ({ ...u, [kind]: false })); }
  };

  const submitForm = async () => {
    if (!form.name.trim()) { toast.error('Name required'); return; }
    if (!form.cost) { toast.error('Cost required'); return; }
    if (!form.image_url) { toast.error('Image required'); return; }
    if (form.feat_type && !form.feat_count) { toast.error('Feat count required'); return; }
    if (FEAT_NEEDS_GENRE(form.feat_type) && !form.feat_genre.trim()) { toast.error('Genre required for this feat'); return; }
    const feat = form.feat_type ? {
      type: form.feat_type,
      count: parseInt(form.feat_count, 10),
      genre: form.feat_genre || null,
    } : null;
    const payload = {
      name: form.name.trim(),
      cost: parseFloat(form.cost),
      image_url: form.image_url,
      thumb_url: form.thumb_url || form.image_url,
      feat,
      active: true,
    };
    try {
      if (form.editing) {
        await axios.patch(`${API}/admin/prizes/${form.editing}`, payload, { withCredentials: true });
        toast.success('Prize updated');
      } else {
        await axios.post(`${API}/admin/prizes`, payload, { withCredentials: true });
        toast.success('Prize created');
      }
      setForm(blankForm);
      reload();
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
  };

  const startEdit = (p) => {
    setForm({
      open: true, editing: p.id, name: p.name, cost: p.cost,
      image_url: p.image_url, thumb_url: p.thumb_url || '',
      feat_type: p.feat?.type || '', feat_count: p.feat?.count || 1, feat_genre: p.feat?.genre || '',
    });
  };
  const disablePrize = async (id) => {
    if (!window.confirm('Disable this prize? Users who already own it keep it.')) return;
    try { await axios.delete(`${API}/admin/prizes/${id}`, { withCredentials: true }); toast.success('Disabled'); reload(); }
    catch { toast.error('Failed'); }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

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
            <p className="text-sm text-[#A3A3A3]">Earn the feat, burn the credits, wear the bling.</p>
          </div>
          {isAdmin && (
            <div className="flex gap-2 flex-wrap">
              <button data-testid="admin-seed-catalog" onClick={seedCatalog} disabled={seeding}
                className="px-5 py-2 bg-transparent border border-[#F59E0B] text-[#F59E0B] font-bold hover:bg-[#F59E0B] hover:text-white transition-colors disabled:opacity-50">
                {seeding ? 'SEEDING...' : '⚡ SEED DEFAULT CATALOG'}
              </button>
              <button data-testid="admin-new-prize-btn" onClick={() => setForm({ ...blankForm, open: true })}
                className="px-5 py-2 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2">
                <Plus size={16} weight="bold" /> NEW PRIZE
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <p className="text-[#A3A3A3]">Loading prizes...</p>
        ) : prizes.length === 0 ? (
          <div className="border border-[#262626] p-12 text-center bg-[#141414]">
            <TrophyIcon size={64} weight="duotone" className="text-[#3F3F3F] mx-auto mb-4" />
            <p className="text-[#A3A3A3] mb-4">No prizes in the catalog yet.</p>
            {isAdmin && <button onClick={seedCatalog} className="px-5 py-2 bg-[#FF3B30] text-white font-bold">SEED DEFAULT CATALOG</button>}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4" data-testid="prizes-grid">
            {prizes.map(p => {
              const owned = ownedIds.has(p.id);
              const canAfford = (user?.wallet_balance || 0) >= p.cost;
              const locked = !p.unlocked;
              return (
                <div key={p.id} data-testid={`prize-${p.id}`} className="border border-[#262626] bg-[#141414] overflow-hidden flex flex-col">
                  <div className="aspect-square bg-[#0A0A0A] relative">
                    {p.image_url ? (
                      <img src={p.image_url} alt={p.name} className={`w-full h-full object-cover ${locked && !owned ? 'opacity-30 grayscale' : ''}`} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#3F3F3F]"><TrophyIcon size={64} weight="duotone" /></div>
                    )}
                    {locked && !owned && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40" data-testid={`locked-${p.id}`}>
                        <Lock size={36} weight="duotone" className="text-white" />
                      </div>
                    )}
                    {owned && (
                      <span className="absolute top-2 right-2 px-2 py-1 bg-[#22C55E] text-white text-[10px] font-bold uppercase">OWNED</span>
                    )}
                  </div>
                  <div className="p-3 flex flex-col flex-1">
                    <p className="text-sm font-bold text-white truncate">{p.name}</p>
                    <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#A3A3A3] mt-0.5 line-clamp-2 min-h-[1.5em]" title={featSummary(p.feat)}>
                      {featSummary(p.feat)}
                    </p>
                    {locked && !owned && p.target > 0 && (
                      <div className="mt-2 mb-1">
                        <div className="h-1.5 bg-[#262626] overflow-hidden">
                          <div className="h-full bg-[#F59E0B]" style={{width: `${Math.min(100, (p.progress / p.target) * 100)}%`}} />
                        </div>
                        <p className="text-[10px] text-[#A3A3A3] mt-1">{Math.floor(p.progress)}/{p.target}</p>
                      </div>
                    )}
                    <p className="text-xl font-black tracking-tighter text-white mt-2 mb-2" style={{fontFamily:'Chivo'}}>{p.cost} CR</p>
                    {owned ? (
                      <span className="w-full text-xs font-bold uppercase tracking-[0.1em] text-[#22C55E] py-2 border border-[#22C55E]/40 flex items-center justify-center gap-1">
                        <Check size={14} weight="bold" /> OWNED
                      </span>
                    ) : locked ? (
                      <button disabled className="w-full px-3 py-2 bg-[#262626] text-[#525252] font-bold text-xs cursor-not-allowed">LOCKED</button>
                    ) : (
                      <button data-testid={`redeem-${p.id}`} disabled={!canAfford || redeeming === p.id} onClick={() => redeem(p)}
                        className="w-full px-3 py-2 bg-[#FF3B30] text-white font-bold text-xs hover:bg-[#D62F26] transition-colors disabled:opacity-50">
                        {redeeming === p.id ? '...' : canAfford ? 'REDEEM' : 'NEED MORE CR'}
                      </button>
                    )}
                    {isAdmin && (
                      <div className="mt-2 flex gap-1">
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
                </div>
              );
            })}
          </div>
        )}

        {/* MY INVENTORY */}
        {user && inventory.items.length > 0 && (
          <div className="mt-12">
            <h3 className="text-2xl font-bold mb-4" style={{fontFamily:'Chivo'}}>MY INVENTORY</h3>
            <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              {inventory.items.map(i => (
                <div key={i.inventory_id} data-testid={`inventory-${i.inventory_id}`}
                  className={`border ${i.is_equipped ? 'border-[#22C55E]' : 'border-[#262626]'} bg-[#141414] overflow-hidden`}>
                  <div className="aspect-square bg-[#0A0A0A]">
                    {i.image_url
                      ? <img src={i.image_url} alt={i.name} className="w-full h-full object-cover" />
                      : <div className="w-full h-full flex items-center justify-center text-[#3F3F3F]"><TrophyIcon size={32} weight="duotone" /></div>}
                  </div>
                  <div className="p-2">
                    <p className="text-xs font-bold text-white truncate">{i.name}</p>
                    {i.is_equipped ? (
                      <p className="text-[10px] font-bold text-[#22C55E] uppercase mt-1">✓ EQUIPPED</p>
                    ) : (
                      <button onClick={() => equip(i)} data-testid={`equip-${i.inventory_id}`}
                        className="mt-1 w-full px-2 py-1 text-[10px] font-bold bg-[#FF3B30] text-white hover:bg-[#D62F26]">EQUIP</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ADMIN FORM */}
      {form.open && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setForm(blankForm)}>
          <div className="bg-[#141414] border border-[#262626] max-w-lg w-full max-h-[92vh] overflow-y-auto p-6 space-y-3" onClick={e=>e.stopPropagation()} data-testid="admin-prize-form">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-xl font-bold" style={{fontFamily:'Chivo'}}>{form.editing ? 'EDIT PRIZE' : 'NEW PRIZE'}</h3>
              <button onClick={() => setForm(blankForm)} className="text-[#A3A3A3] hover:text-white"><X size={24} weight="bold" /></button>
            </div>

            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block">NAME</label>
            <input data-testid="admin-prize-name" placeholder="e.g. ASPHALT ASSASSIN" value={form.name} onChange={e=>setForm({...form, name:e.target.value})}
              className="w-full px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />

            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block">PROFILE IMAGE (large, square preferred)</label>
            <div className="flex items-center gap-3">
              {form.image_url && <img src={form.image_url} alt="" className="w-16 h-16 object-cover border border-[#262626]" />}
              <button type="button" onClick={() => mainFileRef.current?.click()} disabled={uploading.main}
                className="flex-1 px-3 py-2 bg-transparent border border-[#3F3F3F] text-[#A3A3A3] hover:border-white hover:text-white text-xs font-bold flex items-center justify-center gap-1">
                <UploadSimple size={14} weight="bold" /> {uploading.main ? 'UPLOADING...' : form.image_url ? 'REPLACE IMAGE' : 'UPLOAD IMAGE'}
              </button>
              <input ref={mainFileRef} type="file" accept="image/*" className="hidden" onChange={e => uploadImage(e.target.files?.[0], 'main')} data-testid="admin-prize-image-input" />
            </div>

            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block">LEADERBOARD ICON (small thumbnail — falls back to main image if empty)</label>
            <div className="flex items-center gap-3">
              {form.thumb_url && <img src={form.thumb_url} alt="" className="w-12 h-12 object-cover border border-[#262626]" />}
              <button type="button" onClick={() => thumbFileRef.current?.click()} disabled={uploading.thumb}
                className="flex-1 px-3 py-2 bg-transparent border border-[#3F3F3F] text-[#A3A3A3] hover:border-white hover:text-white text-xs font-bold flex items-center justify-center gap-1">
                <UploadSimple size={14} weight="bold" /> {uploading.thumb ? 'UPLOADING...' : form.thumb_url ? 'REPLACE THUMB' : 'UPLOAD THUMB (OPTIONAL)'}
              </button>
              <input ref={thumbFileRef} type="file" accept="image/*" className="hidden" onChange={e => uploadImage(e.target.files?.[0], 'thumb')} data-testid="admin-prize-thumb-input" />
            </div>

            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block">COST (CR)</label>
            <input data-testid="admin-prize-cost" type="number" min="1" value={form.cost} onChange={e=>setForm({...form, cost:e.target.value})}
              className="w-full px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />

            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block">FEAT REQUIRED TO UNLOCK</label>
            <select data-testid="admin-prize-feat-type" value={form.feat_type} onChange={e=>setForm({...form, feat_type:e.target.value, feat_genre: FEAT_NEEDS_GENRE(e.target.value) ? form.feat_genre : ''})}
              className="w-full px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]">
              {FEAT_TYPES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {form.feat_type && (
              <div className="grid grid-cols-2 gap-2">
                <input data-testid="admin-prize-feat-count" type="number" min="1" placeholder="Threshold count (e.g. 10)" value={form.feat_count} onChange={e=>setForm({...form, feat_count:e.target.value})}
                  className="px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
                {FEAT_NEEDS_GENRE(form.feat_type) && (
                  <input data-testid="admin-prize-feat-genre" placeholder="Genre e.g. Racing / FPS / Strategy" value={form.feat_genre} onChange={e=>setForm({...form, feat_genre:e.target.value})}
                    className="px-3 py-2 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:border-[#FF3B30]" />
                )}
              </div>
            )}

            <button data-testid="admin-prize-save" onClick={submitForm}
              className="w-full px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors mt-3">
              {form.editing ? 'SAVE CHANGES' : 'CREATE PRIZE'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Prizes;
