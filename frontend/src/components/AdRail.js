import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const ROTATE_MS = 5000;
const SLOTS = 3;

// Right-rail rotating ad slot — shows 3 stacked ads, each rotating every 5s.
// Slots rotate with staggered offsets so they don't all flip in sync.
export default function AdRail() {
  const [ads, setAds] = useState([]);
  const [indexes, setIndexes] = useState([0, 1, 2]);
  const indexesRef = useRef([0, 1, 2]);
  const impressedRef = useRef(new Set());

  useEffect(() => {
    let mounted = true;
    axios.get(`${API}/ads/rotation`, { withCredentials: true })
      .then(r => { if (mounted) setAds(r.data || []); })
      .catch(() => {});
    return () => { mounted = false; };
  }, []);

  // Rotate one slot at a time with a staggered cycle so they don't flip together.
  useEffect(() => {
    if (ads.length === 0) return;
    let slot = 0;
    const i = setInterval(() => {
      const next = [...indexesRef.current];
      next[slot] = (next[slot] + SLOTS) % Math.max(ads.length, SLOTS);
      indexesRef.current = next;
      setIndexes(next);
      slot = (slot + 1) % SLOTS;
    }, ROTATE_MS / SLOTS); // ~1.66s — each slot still flips every ~5s
    return () => clearInterval(i);
  }, [ads.length]);

  // Fire impression on each visible ad (once per session per ad)
  useEffect(() => {
    if (ads.length === 0) return;
    indexes.forEach(idx => {
      const ad = ads[idx % ads.length];
      if (ad && !impressedRef.current.has(ad.id)) {
        impressedRef.current.add(ad.id);
        axios.post(`${API}/ads/${ad.id}/impression`, {}, { withCredentials: true }).catch(() => {});
      }
    });
  }, [indexes, ads]);

  if (ads.length === 0) return null;

  const visible = indexes.map(i => ads[i % ads.length]).filter(Boolean);

  return (
    <aside data-testid="ad-rail" className="hidden xl:flex flex-col gap-4 w-[180px] fixed right-4 top-24 z-30">
      <div className="text-[10px] font-bold tracking-[0.25em] text-[#525252] uppercase">Sponsored</div>
      {visible.map((ad, i) => (
        <a
          key={`${ad.id}-${i}`}
          href={`${API}/ads/${ad.id}/click`}
          target="_blank"
          rel="noopener noreferrer sponsored"
          data-testid={`ad-slot-${i}`}
          className="block border border-[#262626] bg-[#141414]/95 backdrop-blur-md hover:border-[#FF3B30] transition-all duration-300 group"
          title={ad.name}
        >
          <div className="aspect-square overflow-hidden bg-[#0A0A0A]">
            <img
              src={ad.image_url}
              alt={ad.name}
              loading="lazy"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          </div>
          <div className="px-2 py-1.5 text-[10px] text-[#A3A3A3] truncate">{ad.name}</div>
        </a>
      ))}
    </aside>
  );
}
