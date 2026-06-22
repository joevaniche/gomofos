import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import axios from 'axios';
import TopNav from '../components/TopNav';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { MagnifyingGlass, Trash, Plus, ToggleLeft, ToggleRight, Image as ImageIcon } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminAds() {
  const { user } = useAuth();
  const [ads, setAds] = useState([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', image_url: '', click_url: '', active: true });
  const [uploading, setUploading] = useState(false);

  const canAccess = user && (user.role === 'admin' || user.can_manage_ads === true);

  const load = async (search = '') => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/ads`, { params: search ? { q: search } : {}, withCredentials: true });
      setAds(r.data || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load ads');
    } finally { setLoading(false); }
  };
  useEffect(() => { if (canAccess) load(); }, [canAccess]);

  if (!user) return null;
  if (!canAccess) return <Navigate to="/dashboard" replace />;

  const handleSearch = (e) => { e.preventDefault(); load(q); };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await axios.post(`${API}/admin/ads/upload-image`, fd, { withCredentials: true });
      const fullUrl = `${process.env.REACT_APP_BACKEND_URL}${r.data.url}`;
      setForm(f => ({ ...f, image_url: fullUrl }));
      toast.success('Image uploaded');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name || !form.image_url || !form.click_url) {
      toast.error('All fields required');
      return;
    }
    try {
      await axios.post(`${API}/admin/ads`, form, { withCredentials: true });
      setForm({ name: '', image_url: '', click_url: '', active: true });
      toast.success('Ad created');
      load(q);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Create failed');
    }
  };

  const handleToggle = async (ad) => {
    try {
      await axios.patch(`${API}/admin/ads/${ad.id}`, {
        name: ad.name, image_url: ad.image_url, click_url: ad.click_url, active: !ad.active,
      }, { withCredentials: true });
      load(q);
    } catch (err) {
      toast.error('Toggle failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this ad permanently?')) return;
    try {
      await axios.delete(`${API}/admin/ads/${id}`, { withCredentials: true });
      toast.success('Ad deleted');
      load(q);
    } catch (err) {
      toast.error('Delete failed');
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]/60 text-white">
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-10" data-testid="admin-ads-page">
        <div className="mb-8">
          <p className="text-xs font-bold tracking-[0.3em] text-[#FF3B30]">ADMIN</p>
          <h1 className="text-4xl font-black mt-1">ADVERTISING</h1>
          <p className="text-sm text-[#A3A3A3] mt-2">Add, search and toggle ads shown in the right rail to every logged-in user.</p>
        </div>

        {/* Create form */}
        <div className="border border-[#262626] bg-[#141414] p-6 mb-8">
          <h2 className="text-sm font-bold tracking-[0.25em] text-[#A3A3A3] mb-4 flex items-center gap-2"><Plus weight="bold" /> NEW AD</h2>
          <form onSubmit={handleCreate} className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-[#A3A3A3] block mb-1">Name (searchable)</label>
              <input
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                data-testid="ad-name-input"
                className="w-full bg-[#0A0A0A] border border-[#262626] px-3 py-2 text-sm"
                placeholder="Pizza Joe — May Promo"
              />
            </div>
            <div>
              <label className="text-xs text-[#A3A3A3] block mb-1">Click URL</label>
              <input
                value={form.click_url}
                onChange={e => setForm({ ...form, click_url: e.target.value })}
                data-testid="ad-url-input"
                className="w-full bg-[#0A0A0A] border border-[#262626] px-3 py-2 text-sm"
                placeholder="https://example.com"
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-[#A3A3A3] block mb-1">Image URL</label>
              <div className="flex gap-2 items-center">
                <input
                  value={form.image_url}
                  onChange={e => setForm({ ...form, image_url: e.target.value })}
                  data-testid="ad-image-input"
                  className="flex-1 bg-[#0A0A0A] border border-[#262626] px-3 py-2 text-sm"
                  placeholder="https://..."
                />
                <label className="cursor-pointer border border-[#FF3B30] text-[#FF3B30] hover:bg-[#FF3B30] hover:text-white px-3 py-2 text-xs font-bold flex items-center gap-1">
                  <ImageIcon weight="bold" />
                  {uploading ? 'UPLOADING…' : 'UPLOAD'}
                  <input type="file" accept="image/*" onChange={handleUpload} className="hidden" data-testid="ad-image-upload" />
                </label>
              </div>
              {form.image_url && (
                <img src={form.image_url} alt="preview" className="mt-3 h-32 object-contain border border-[#262626]" />
              )}
            </div>
            <div className="md:col-span-2">
              <button type="submit" data-testid="ad-create-btn" className="bg-[#FF3B30] hover:bg-[#FF3B30]/80 text-white font-bold tracking-wider px-6 py-2.5 text-sm">
                CREATE AD
              </button>
            </div>
          </form>
        </div>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A3A3A3]" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              data-testid="ad-search-input"
              placeholder="Search name or URL…"
              className="w-full bg-[#141414] border border-[#262626] pl-10 pr-3 py-2 text-sm"
            />
          </div>
          <button type="submit" className="border border-[#262626] hover:border-white px-5 py-2 text-sm font-bold tracking-wider">SEARCH</button>
        </form>

        {/* Ads list */}
        {loading ? (
          <div className="text-[#A3A3A3] text-sm">Loading ads…</div>
        ) : ads.length === 0 ? (
          <div className="border border-[#262626] bg-[#141414] p-8 text-center text-[#A3A3A3] text-sm" data-testid="no-ads">
            No ads yet. Create one above.
          </div>
        ) : (
          <div className="space-y-3" data-testid="ads-list">
            {ads.map(ad => (
              <div key={ad.id} className="flex items-center gap-4 border border-[#262626] bg-[#141414] p-3" data-testid={`ad-row-${ad.id}`}>
                <img src={ad.image_url} alt="" className="w-16 h-16 object-cover border border-[#262626] bg-[#0A0A0A]" />
                <div className="flex-1 min-w-0">
                  <div className="font-bold truncate">{ad.name}</div>
                  <a href={ad.click_url} target="_blank" rel="noopener noreferrer" className="text-xs text-[#A3A3A3] hover:text-[#FF3B30] truncate block">{ad.click_url}</a>
                  <div className="text-[10px] text-[#525252] mt-1">
                    {ad.impression_count} impressions · {ad.click_count} clicks · added by {ad.created_by_username || '?'}
                  </div>
                </div>
                <button onClick={() => handleToggle(ad)} className="text-[#A3A3A3] hover:text-white" title={ad.active ? 'Disable' : 'Enable'} data-testid={`ad-toggle-${ad.id}`}>
                  {ad.active ? <ToggleRight size={36} weight="fill" className="text-[#22C55E]" /> : <ToggleLeft size={36} weight="fill" />}
                </button>
                <button onClick={() => handleDelete(ad.id)} className="text-[#A3A3A3] hover:text-[#FF3B30]" data-testid={`ad-delete-${ad.id}`}>
                  <Trash size={20} weight="bold" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
