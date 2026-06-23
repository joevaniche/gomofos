import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const ROTATE_MS = 5000;
const SLOTS = 3;

// Right-rail rotating ad slot — shows 3 stacked ads.
// Each slot independently rotates every ~5s (staggered start so they don't flip in sync).
//
// Layout:
//   • Desktop (xl+): floats on the right side, absolutely positioned RELATIVE TO THE DOCUMENT
//     (parent must be `position: relative` — see ProtectedRoute) so it SCROLLS with the page
//     instead of staying fixed.
//   • Mobile/tablet: renders inline at the END of the page (row of 3 cards stacked vertically).
//
// Visuals: each card is 30% shorter than a square (160 × 112 image area)
//          and slots are separated by extra vertical breathing room (gap-12).
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

  // Stagger rotation so the 3 slots don't all flip at the same moment.
  useEffect(() => {
    if (ads.length === 0) return;
    let slot = 0;
    const i = setInterval(() => {
      const next = [...indexesRef.current];
      next[slot] = (next[slot] + SLOTS) % Math.max(ads.length, SLOTS);
      indexesRef.current = next;
      setIndexes(next);
      slot = (slot + 1) % SLOTS;
    }, ROTATE_MS / SLOTS); // ~1.67s — each slot still flips ~every 5s
    return () => clearInterval(i);
  }, [ads.length]);

  // Fire impression once per ad per session
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
    <aside
      data-testid="ad-rail"
      className="
        ad-rail
        w-full max-w-md mx-auto px-6 py-8
        flex flex-col gap-12
        xl:absolute xl:right-6 xl:top-24 xl:w-[170px] xl:max-w-none xl:mx-0 xl:px-0 xl:py-0
        z-20
      "
    >
      <div className="text-[10px] font-bold tracking-[0.25em] text-[#525252] uppercase">Sponsored</div>
      {visible.map((ad, i) => (
        <a
          key={`${ad.id}-${i}`}
          href={`${API}/ads/${ad.id}/click`}
          target="_blank"
          rel="noopener noreferrer sponsored"
          data-testid={`ad-slot-${i}`}
          className="block border border-[#262626] bg-[#141414] hover:border-[#FF3B30] transition-all duration-300 group"
          title={ad.name}
        >
          {/* Image area: 30% shorter than aspect-square. Square => 1:1; we use ~7:5 (image height = 70% width).
              Tailwind arbitrary aspect-ratio keeps it crisp at any width. */}
          <div className="overflow-hidden bg-[#0A0A0A] w-full" style={{ aspectRatio: '10 / 7' }}>
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
