import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { VideoCamera, Trash, Play, X, UploadSimple, Eye } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const MAX_BYTES = 50 * 1024 * 1024;
const MAX_DURATION = 60;

export function HighlightReels({ userId, isOwner, games = [] }) {
  const [reels, setReels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [playing, setPlaying] = useState(null);

  useEffect(() => { loadReels(); /* eslint-disable-next-line */ }, [userId]);

  const loadReels = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/highlights/user/${userId}`);
      setReels(data);
    } catch {
      // Empty state is fine
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this highlight reel? This cannot be undone.')) return;
    try {
      await axios.delete(`${API}/highlights/${id}`, { withCredentials: true });
      toast.success('Highlight deleted');
      setReels(reels.filter(r => r.id !== id));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to delete');
    }
  };

  const handlePlay = async (reel) => {
    setPlaying(reel);
    // Fire-and-forget view count increment
    axios.get(`${API}/highlights/${reel.id}`).catch(() => {});
  };

  return (
    <div className="border border-[#262626] bg-[#141414]/85 backdrop-blur-sm p-6" data-testid="highlights-section">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <VideoCamera size={24} weight="duotone" className="text-[#FF3B30]" />
          <h3 className="text-xl font-bold tracking-tight" style={{ fontFamily: 'Chivo' }}>HIGHLIGHT REELS</h3>
          <span className="text-xs text-[#A3A3A3]">({reels.length})</span>
        </div>
        {isOwner && (
          <button data-testid="upload-highlight-btn" onClick={() => setShowUpload(true)}
            className="px-4 py-2 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors flex items-center gap-2 text-sm">
            <UploadSimple size={16} weight="bold" /> UPLOAD CLIP
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-[#A3A3A3]">Loading...</p>
      ) : reels.length === 0 ? (
        <p className="text-sm text-[#A3A3A3]">
          {isOwner ? 'No highlights yet. Upload your best plays — up to 60s, MP4/MOV/WebM.' : 'No highlights uploaded yet.'}
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {reels.map(r => (
            <ReelCard key={r.id} reel={r} isOwner={isOwner} onPlay={() => handlePlay(r)} onDelete={() => handleDelete(r.id)} />
          ))}
        </div>
      )}

      {showUpload && (
        <UploadHighlightModal games={games} onClose={() => setShowUpload(false)} onUploaded={() => { setShowUpload(false); loadReels(); }} />
      )}
      {playing && (
        <PlayerModal reel={playing} onClose={() => setPlaying(null)} />
      )}
    </div>
  );
}

function ReelCard({ reel, isOwner, onPlay, onDelete }) {
  const fmt = (n) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : n;
  return (
    <div className="border border-[#262626] bg-[#0A0A0A] group" data-testid={`reel-${reel.id}`}>
      <button onClick={onPlay} className="relative w-full aspect-video bg-black overflow-hidden flex items-center justify-center hover:opacity-90 transition-opacity">
        <video
          src={`${process.env.REACT_APP_BACKEND_URL}${reel.video_url}#t=0.5`}
          preload="metadata"
          className="w-full h-full object-cover"
          muted
        />
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/20 transition-colors">
          <Play size={48} weight="fill" className="text-white drop-shadow-lg" />
        </div>
        {reel.duration_sec > 0 && (
          <span className="absolute bottom-2 right-2 px-2 py-0.5 bg-black/80 text-white text-xs font-bold">
            {Math.round(reel.duration_sec)}s
          </span>
        )}
      </button>
      <div className="p-3">
        <p className="text-sm font-bold text-white truncate" title={reel.title}>{reel.title}</p>
        <div className="flex items-center justify-between mt-1">
          <p className="text-xs text-[#A3A3A3] truncate">{reel.game_name || 'Untagged'}</p>
          <p className="text-xs text-[#A3A3A3] flex items-center gap-1"><Eye size={12} weight="bold" /> {fmt(reel.view_count || 0)}</p>
        </div>
        {isOwner && (
          <button data-testid={`delete-reel-${reel.id}`} onClick={onDelete}
            className="mt-2 w-full px-3 py-1.5 bg-transparent border border-[#3F3F3F] text-[#A3A3A3] hover:border-[#EF4444] hover:text-[#EF4444] font-bold text-xs transition-all flex items-center justify-center gap-1">
            <Trash size={12} weight="bold" /> DELETE
          </button>
        )}
      </div>
    </div>
  );
}

function PlayerModal({ reel, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="reel-player-modal">
      <div className="max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-bold text-white" style={{ fontFamily: 'Chivo' }}>{reel.title}</h3>
          <button onClick={onClose} className="text-white hover:text-[#FF3B30]" data-testid="close-reel-player"><X size={28} weight="bold" /></button>
        </div>
        <video
          src={`${process.env.REACT_APP_BACKEND_URL}${reel.video_url}`}
          className="w-full bg-black"
          controls
          autoPlay
          playsInline
        />
        <p className="text-sm text-[#A3A3A3] mt-2">{reel.game_name || 'Untagged'} · {Math.round(reel.duration_sec || 0)}s · {reel.view_count} views</p>
      </div>
    </div>
  );
}

function UploadHighlightModal({ games, onClose, onUploaded }) {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [gameId, setGameId] = useState('');
  const [duration, setDuration] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleFile = (f) => {
    if (!f) return;
    if (!f.type.startsWith('video/')) {
      toast.error('Please pick a video file (MP4, MOV, or WebM).');
      return;
    }
    if (f.size > MAX_BYTES) {
      toast.error(`File too big — max ${Math.round(MAX_BYTES / 1024 / 1024)} MB.`);
      return;
    }
    // Probe duration
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.onloadedmetadata = () => {
      window.URL.revokeObjectURL(video.src);
      if (video.duration > MAX_DURATION + 0.5) {
        toast.error(`Clip too long — max ${MAX_DURATION}s. Yours: ${Math.round(video.duration)}s.`);
        return;
      }
      setDuration(video.duration);
      setFile(f);
      if (!title) setTitle(f.name.replace(/\.[^/.]+$/, '').slice(0, 80));
    };
    video.onerror = () => {
      toast.error("Couldn't read that video. Try MP4.");
    };
    video.src = window.URL.createObjectURL(f);
  };

  const handleUpload = async () => {
    if (!file) { toast.error('Pick a video first'); return; }
    if (!title.trim()) { toast.error('Title required'); return; }
    setUploading(true);
    setProgress(0);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('title', title.trim());
      if (gameId) form.append('game_id', gameId);
      if (duration) form.append('duration_sec', duration.toFixed(2));
      await axios.post(`${API}/highlights`, form, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
        },
      });
      toast.success('Highlight uploaded!');
      onUploaded();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="upload-highlight-modal">
      <div className="bg-[#141414] border border-[#262626] max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-6 border-b border-[#262626]">
          <div className="flex items-center gap-2">
            <UploadSimple size={24} weight="duotone" className="text-[#FF3B30]" />
            <h3 className="text-xl font-bold" style={{ fontFamily: 'Chivo' }}>UPLOAD HIGHLIGHT</h3>
          </div>
          <button onClick={onClose} className="text-[#A3A3A3] hover:text-white"><X size={24} weight="bold" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">VIDEO FILE</label>
            <input ref={fileInputRef} type="file" accept="video/mp4,video/quicktime,video/webm,video/*"
              onChange={(e) => handleFile(e.target.files?.[0])}
              data-testid="highlight-file-input"
              className="hidden" />
            <button onClick={() => fileInputRef.current?.click()}
              className="w-full px-4 py-3 bg-[#0A0A0A] border-2 border-dashed border-[#3F3F3F] text-white hover:border-[#FF3B30] transition-all">
              {file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB · ${Math.round(duration)}s` : 'Click to pick a video (max 60s, 50MB)'}
            </button>
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">TITLE</label>
            <input data-testid="highlight-title-input" type="text" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]"
              placeholder="Insane comeback in extra time!" />
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-[0.1em] text-[#A3A3A3] block mb-2">GAME (OPTIONAL)</label>
            <select data-testid="highlight-game-select" value={gameId} onChange={(e) => setGameId(e.target.value)}
              className="w-full px-4 py-3 bg-[#0A0A0A] border border-[#262626] text-white focus:outline-none focus:ring-1 focus:ring-[#FF3B30] focus:border-[#FF3B30]">
              <option value="">No game tag</option>
              {games.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </div>
          {uploading && (
            <div className="w-full bg-[#0A0A0A] h-2 border border-[#262626]">
              <div className="bg-[#FF3B30] h-full transition-all" style={{ width: `${progress}%` }} />
            </div>
          )}
          <div className="flex gap-3">
            <button data-testid="confirm-upload-highlight-btn" onClick={handleUpload} disabled={uploading || !file}
              className="flex-1 px-6 py-3 bg-[#FF3B30] text-white font-bold hover:bg-[#D62F26] transition-colors disabled:opacity-50">
              {uploading ? `UPLOADING... ${progress}%` : 'UPLOAD'}
            </button>
            <button onClick={onClose} className="px-6 py-3 bg-transparent border border-[#3F3F3F] text-white hover:border-[#FF3B30] hover:text-[#FF3B30] font-bold transition-all">
              CANCEL
            </button>
          </div>
          <p className="text-xs text-[#A3A3A3]">
            By uploading, you confirm you own the rights to this clip. Highlights are public and may appear on your profile and tournament share cards.
          </p>
        </div>
      </div>
    </div>
  );
}

export default HighlightReels;
