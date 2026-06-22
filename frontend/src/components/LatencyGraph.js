import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Legend, CartesianGrid } from 'recharts';

const SERIES_COLORS = ['#FF3B30', '#3B82F6', '#22C55E', '#F59E0B', '#8B5CF6', '#EC4899'];

// Normalises {series:[{username,points:[{t,ms}]}], thresholds:{warn,high}} into a flat
// recharts dataset with one column per user, indexed by timestamp.
function flatten(series) {
  const tsSet = new Set();
  series.forEach(s => s.points.forEach(p => tsSet.add(p.t)));
  const sorted = Array.from(tsSet).sort();
  return sorted.map(t => {
    const row = { t, label: new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) };
    series.forEach(s => {
      const p = s.points.find(pp => pp.t === t);
      row[s.username] = p ? p.ms : null;
    });
    return row;
  });
}

// Latency line graph — spikes/dips per player. Used by admin pages.
// Props:
//   data: backend response with {series:[{user_id, username, points:[{t,ms}], avg_ms, max_ms, status}], thresholds:{warn,high}}
//   height: optional, default 320
export default function LatencyGraph({ data, height = 320 }) {
  if (!data || !data.series || data.series.length === 0) {
    return (
      <div data-testid="latency-graph-empty" className="border border-[#262626] bg-[#141414] p-8 text-center text-sm text-[#A3A3A3]">
        No latency samples recorded for this match yet.
      </div>
    );
  }
  const rows = flatten(data.series);
  const warn = data.thresholds?.warn ?? 100;
  const high = data.thresholds?.high ?? 200;
  return (
    <div data-testid="latency-graph" className="border border-[#262626] bg-[#141414] p-4">
      {/* Per-player summary chips */}
      <div className="flex flex-wrap gap-3 mb-4">
        {data.series.map((s, i) => (
          <div key={s.user_id} className="flex items-center gap-2 px-3 py-1.5 border border-[#262626] bg-[#0A0A0A]">
            <span className="w-2 h-2 rounded-full" style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />
            <span className="text-sm font-bold">{s.username}</span>
            <span className="text-xs text-[#A3A3A3]">avg {s.avg_ms}ms · peak {s.max_ms}ms · n={s.sample_count}</span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 ${
              s.status === 'high' ? 'bg-[#FF3B30] text-white' :
              s.status === 'warn' ? 'bg-[#F59E0B] text-black' :
              'bg-[#22C55E] text-black'
            }`}>{s.status.toUpperCase()}</span>
          </div>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid stroke="#262626" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#262626" />
          <YAxis tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#262626" unit="ms" />
          <Tooltip contentStyle={{ background: '#0A0A0A', border: '1px solid #262626', fontSize: 12 }} labelStyle={{ color: '#A3A3A3' }} />
          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
          <ReferenceLine y={warn} stroke="#F59E0B" strokeDasharray="4 4" label={{ value: `warn ${warn}ms`, fill: '#F59E0B', fontSize: 10, position: 'right' }} />
          <ReferenceLine y={high} stroke="#FF3B30" strokeDasharray="4 4" label={{ value: `high ${high}ms`, fill: '#FF3B30', fontSize: 10, position: 'right' }} />
          {data.series.map((s, i) => (
            <Line
              key={s.user_id}
              type="monotone"
              dataKey={s.username}
              stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
              strokeWidth={2}
              connectNulls
              dot={{ r: 2 }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
