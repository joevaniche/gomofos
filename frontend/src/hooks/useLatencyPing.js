import { useEffect, useRef } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Pings the backend every 60s while a tournament/competition match is active.
// Uses HTTP latency timing (round-trip to /api/health/time) rather than WS so
// every page that uses this hook gets a sample without keeping a socket open.
//
// Usage:
//   useLatencyPing({ tournament_id: t.id, active: t.status === 'in_progress' })
//   useLatencyPing({ competition_id: c.id, match_id: m.id, active: m.status === 'pending_confirmation' })
export default function useLatencyPing({ tournament_id, competition_id, match_id, active, intervalMs = 60000 }) {
  const stopRef = useRef(false);

  useEffect(() => {
    if (!active) return;
    stopRef.current = false;

    const ping = async () => {
      if (stopRef.current) return;
      const start = performance.now();
      try {
        await axios.get(`${API}/health/time`, { withCredentials: true });
      } catch { /* ignore */ }
      const rtt = performance.now() - start;
      if (rtt <= 0) return;
      try {
        if (tournament_id) {
          await axios.post(`${API}/tournaments/${tournament_id}/latency`,
            null, { params: { latency_ms: rtt }, withCredentials: true });
        } else if (competition_id) {
          await axios.post(`${API}/competitions/${competition_id}/latency`,
            null, { params: { latency_ms: rtt, ...(match_id ? { match_id } : {}) }, withCredentials: true });
        }
      } catch { /* fire & forget */ }
    };

    ping(); // immediately
    const id = setInterval(ping, intervalMs);
    return () => { stopRef.current = true; clearInterval(id); };
  }, [tournament_id, competition_id, match_id, active, intervalMs]);
}
