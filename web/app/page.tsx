'use client';

import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface KpiMetrics {
  cagr: number | null;
  sharpe: number | null;
  max_dd: number | null;
  total_return: number | null;
}

interface StrategyItem {
  id: string;
  sharpe: number | null;
  return: number | null;
}

interface Regime {
  strategies: StrategyItem[];
  kpis: any;
}

interface DashboardData {
  schema: string;
  generated_utc: string;
  window: {
    start_utc: string;
    end_utc: string;
  };
  series: any[];
  kpis: {
    btc: KpiMetrics;
    hong: KpiMetrics;
    delta_total_return: number | null;
  };
  regimes: {
    BULL: Regime;
    BEAR: Regime;
    SIDEWAYS: Regime;
  };
  blend: {
    kpis: KpiMetrics;
    notes: string[];
  };
  sources: {
    regime_timeline: string;
    selection_or_leaderboard: string;
    equity_curve_source: string;
  };
}

function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
  return `${(value * 100).toFixed(2)}%`;
}

function formatNum(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
  return value.toFixed(decimals);
}

function formatDateTimeShort(isoStr: string | null): string {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        const url = new URL('/api/strategy_dashboard', window.location.origin);
        const res = await fetch(url.toString(), { cache: 'no-store' });
        if (!res.ok) {
          const e = await res.json().catch(() => ({}));
          throw new Error(e.error || `HTTP ${res.status}`);
        }
        const json = (await res.json()) as DashboardData;
        if (!mounted) return;
        setData(json);
        setError(null);
      } catch (err: any) {
        console.error(err);
        if (!mounted) return;
        setError(err.message || 'Failed to fetch strategy dashboard state');
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading && !data) {
    return (
      <main className="min-h-screen bg-slate-950 p-6 flex items-center justify-center text-slate-100">
        <div className="animate-pulse flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-cyan-400 font-mono text-sm tracking-widest">LOADING ENGINE STATE</p>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="min-h-screen bg-[#0A0D14] flex items-center justify-center p-6 text-slate-100 font-sans">
        <div className="max-w-xl w-full rounded-2xl border border-rose-900/50 bg-rose-950/20 p-8 text-center shadow-xl backdrop-blur-xl">
          <div className="w-16 h-16 bg-rose-900/40 rounded-full flex items-center justify-center mx-auto mb-4 border border-rose-500/30">
            <span className="text-2xl">🚨</span>
          </div>
          <h1 className="text-xl font-bold text-rose-100 mb-2">Strategy Dashboard Unavailable</h1>
          <p className="text-sm text-rose-300 font-mono bg-rose-950/50 p-3 rounded mb-6 break-all">
            {error || 'No strategy data returned.'}
          </p>
          <div className="bg-slate-900/80 rounded-xl p-4 text-left border border-slate-800">
            <p className="text-xs uppercase tracking-wider font-bold text-slate-500 mb-2">Resolution Hint</p>
            <p className="text-sm text-slate-300">
              Run the canonical state refresher in the repository root to compile the latest SSOT:
            </p>
            <code className="block mt-2 bg-black/50 text-cyan-400 p-2 rounded text-xs font-mono border border-cyan-900/30">
              bash scripts/refresh_state.sh
            </code>
          </div>
        </div>
      </main>
    );
  }

  // Formatting series data for Recharts
  const chartData = (data.series || []).map(pt => ({
    date: formatDateTimeShort(pt.ts_utc),
    BTC: pt.btc_bh,
    HONG: pt.hong
  }));

  const hasHongCurve = chartData.some(d => d.HONG !== null && d.HONG !== undefined);

  return (
    <main className="min-h-screen bg-[#0A0D14] text-slate-200 font-sans selection:bg-cyan-900 selection:text-cyan-50 relative overflow-hidden">
      {/* Background ambient light */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-cyan-900/20 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-900/20 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10 flex flex-col gap-8">

        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-800/80 pb-6">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500">
              HONGSTR Strategy Explorer
            </h1>
            <p className="text-sm text-slate-400 mt-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
              Live Synthetic State • Generated {new Date(data.generated_utc).toLocaleString()}
            </p>
          </div>
          <div className="flex gap-4 text-xs font-mono text-slate-500">
            <div className="bg-slate-900/60 border border-slate-800 rounded px-3 py-1.5 backdrop-blur">
              <span className="text-slate-400 block mb-0.5">Time Window</span>
              <span className="text-slate-300">{formatDateTimeShort(data.window.start_utc)} → {formatDateTimeShort(data.window.end_utc)}</span>
            </div>
          </div>
        </header>

        {/* Global Warnings / Data Missing Overlays */}
        {data.blend.notes && data.blend.notes.length > 0 && (
          <div className="bg-amber-950/30 border border-amber-800/50 rounded-xl p-4 backdrop-blur-sm">
            <h3 className="text-amber-500 font-bold text-sm tracking-wide uppercase mb-2 flex items-center gap-2">
              ⚠️ Data Completeness Notice
            </h3>
            <ul className="list-disc pl-5 space-y-1 text-amber-200/80 text-sm">
              {data.blend.notes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Hero Chart Section */}
        <section className="bg-slate-900/40 border border-slate-800/60 rounded-2xl overflow-hidden backdrop-blur-xl shadow-2xl">
          <div className="p-6 border-b border-slate-800/60 bg-slate-900/80 flex flex-col lg:flex-row justify-between gap-6">
            <div className="flex-1">
              <h2 className="text-lg font-bold text-white mb-4">Portfolio Equity Comparison (Normalized)</h2>

              <div className="flex flex-wrap gap-x-8 gap-y-4">

                {/* HONG KPIs */}
                <div className="space-y-1 relative pl-3">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyan-500 rounded-full"></div>
                  <span className="text-xs font-bold uppercase tracking-wider text-cyan-500">HONG Blended</span>
                  <div className="flex gap-4 text-sm mt-1">
                    <div><span className="text-slate-500 mr-2">TR</span><span className="font-mono text-slate-200">{formatPct(data.kpis.hong.total_return)}</span></div>
                    <div><span className="text-slate-500 mr-2">CAGR</span><span className="font-mono text-slate-200">{formatPct(data.kpis.hong.cagr)}</span></div>
                    <div><span className="text-slate-500 mr-2">MDD</span><span className="font-mono text-rose-400">{formatPct(data.kpis.hong.max_dd)}</span></div>
                    <div><span className="text-slate-500 mr-2">SHR</span><span className="font-mono text-emerald-400">{formatNum(data.kpis.hong.sharpe)}</span></div>
                  </div>
                </div>

                {/* BTC KPIs */}
                <div className="space-y-1 relative pl-3">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-orange-500 rounded-full"></div>
                  <span className="text-xs font-bold uppercase tracking-wider text-orange-500">BTC Buy & Hold</span>
                  <div className="flex gap-4 text-sm mt-1">
                    <div><span className="text-slate-500 mr-2">TR</span><span className="font-mono text-slate-200">{formatPct(data.kpis.btc.total_return)}</span></div>
                    <div><span className="text-slate-500 mr-2">CAGR</span><span className="font-mono text-slate-200">{formatPct(data.kpis.btc.cagr)}</span></div>
                    <div><span className="text-slate-500 mr-2">MDD</span><span className="font-mono text-rose-400">{formatPct(data.kpis.btc.max_dd)}</span></div>
                  </div>
                </div>

              </div>
            </div>

            <div className="bg-slate-950/50 rounded-xl border border-slate-800/80 p-4 flex flex-col justify-center min-w-[200px]">
              <span className="text-xs text-slate-500 uppercase font-bold tracking-wider text-center block mb-1">Delta vs BTC</span>
              <div className={`text-3xl font-mono font-bold text-center ${data.kpis.delta_total_return && data.kpis.delta_total_return >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {data.kpis.delta_total_return && data.kpis.delta_total_return > 0 ? '+' : ''}{formatPct(data.kpis.delta_total_return)}
              </div>
            </div>
          </div>

          <div className="h-[400px] w-full p-4 relative">
            {!hasHongCurve && (
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-slate-950/60 backdrop-blur-sm pointer-events-none">
                <span className="text-3xl mb-3">👻</span>
                <span className="text-slate-300 font-bold bg-slate-900/80 px-4 py-2 border border-slate-700 rounded-lg shadow-lg uppercase tracking-widest text-sm">HONG Curve Unavailable in SSOT</span>
              </div>
            )}
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorBTC" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f97316" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorHONG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#64748b"
                  fontSize={12}
                  tickMargin={10}
                  tickFormatter={(val: string) => val.substring(0, 7)} // Just show YYYY-MM
                  minTickGap={30}
                />
                <YAxis
                  stroke="#64748b"
                  fontSize={12}
                  tickFormatter={(val) => val.toFixed(1) + 'x'}
                  domain={['auto', 'auto']}
                  orientation="right"
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }}
                  itemStyle={{ fontFamily: 'monospace' }}
                  labelStyle={{ color: '#94a3b8', marginBottom: '8px', fontWeight: 'bold' }}
                />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                <Line type="monotone" dataKey="BTC" name="Buy & Hold (BTC)" stroke="#f97316" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
                {hasHongCurve && (
                  <Line type="monotone" dataKey="HONG" name="HONG Blended" stroke="#06b6d4" strokeWidth={3} dot={false} activeDot={{ r: 8 }} />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Strategy Portfolio Section */}
        <section>
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="text-xl">🛡️</span>
              Strategy Portfolio
            </h2>
            <div className="text-xs text-slate-500 font-mono tracking-widest uppercase border border-slate-800 px-3 py-1 rounded bg-slate-900/50">
              Live Compositions
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

            {/* BULL Card */}
            <div className="bg-gradient-to-br from-emerald-950/40 to-slate-900/80 border border-emerald-900/30 rounded-2xl overflow-hidden backdrop-blur-md hover:border-emerald-700/50 transition-colors">
              <div className="bg-emerald-900/20 py-3 px-5 border-b border-emerald-900/30">
                <h3 className="text-emerald-400 font-bold uppercase tracking-wider flex justify-between items-center">
                  BULL Regime
                  <span className="bg-emerald-950 text-emerald-300 text-[10px] px-2 py-0.5 rounded-full border border-emerald-800/50">{data.regimes.BULL.strategies.length} Strats</span>
                </h3>
              </div>
              <div className="p-5">
                {data.regimes.BULL.strategies.length > 0 ? (
                  <ul className="space-y-3">
                    {data.regimes.BULL.strategies.map(s => (
                      <li key={s.id} className="bg-slate-950/50 rounded-lg p-3 border border-emerald-900/10 hover:border-emerald-500/20 transition-all">
                        <div className="font-mono text-sm text-emerald-100/90 break-all mb-2">{s.id}</div>
                        <div className="flex justify-between text-xs font-mono text-emerald-400/70 bg-emerald-950/30 rounded px-2 py-1">
                          <span>SR: {formatNum(s.sharpe)}</span>
                          <span>Ret: {formatPct(s.return)}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 italic text-center py-8">No strategies assigned.</p>
                )}
              </div>
            </div>

            {/* SIDEWAYS Card */}
            <div className="bg-gradient-to-br from-indigo-950/40 to-slate-900/80 border border-indigo-900/30 rounded-2xl overflow-hidden backdrop-blur-md hover:border-indigo-700/50 transition-colors">
              <div className="bg-indigo-900/20 py-3 px-5 border-b border-indigo-900/30">
                <h3 className="text-indigo-400 font-bold uppercase tracking-wider flex justify-between items-center">
                  SIDEWAYS Regime
                  <span className="bg-indigo-950 text-indigo-300 text-[10px] px-2 py-0.5 rounded-full border border-indigo-800/50">{data.regimes.SIDEWAYS.strategies.length} Strats</span>
                </h3>
              </div>
              <div className="p-5">
                {data.regimes.SIDEWAYS.strategies.length > 0 ? (
                  <ul className="space-y-3">
                    {data.regimes.SIDEWAYS.strategies.map(s => (
                      <li key={s.id} className="bg-slate-950/50 rounded-lg p-3 border border-indigo-900/10 hover:border-indigo-500/20 transition-all">
                        <div className="font-mono text-sm text-indigo-100/90 break-all mb-2">{s.id}</div>
                        <div className="flex justify-between text-xs font-mono text-indigo-400/70 bg-indigo-950/30 rounded px-2 py-1">
                          <span>SR: {formatNum(s.sharpe)}</span>
                          <span>Ret: {formatPct(s.return)}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 italic text-center py-8">No strategies assigned.</p>
                )}
              </div>
            </div>

            {/* BEAR Card */}
            <div className="bg-gradient-to-br from-rose-950/40 to-slate-900/80 border border-rose-900/30 rounded-2xl overflow-hidden backdrop-blur-md hover:border-rose-700/50 transition-colors">
              <div className="bg-rose-900/20 py-3 px-5 border-b border-rose-900/30">
                <h3 className="text-rose-400 font-bold uppercase tracking-wider flex justify-between items-center">
                  BEAR Regime
                  <span className="bg-rose-950 text-rose-300 text-[10px] px-2 py-0.5 rounded-full border border-rose-800/50">{data.regimes.BEAR.strategies.length} Strats</span>
                </h3>
              </div>
              <div className="p-5">
                {data.regimes.BEAR.strategies.length > 0 ? (
                  <ul className="space-y-3">
                    {data.regimes.BEAR.strategies.map(s => (
                      <li key={s.id} className="bg-slate-950/50 rounded-lg p-3 border border-rose-900/10 hover:border-rose-500/20 transition-all">
                        <div className="font-mono text-sm text-rose-100/90 break-all mb-2">{s.id}</div>
                        <div className="flex justify-between text-xs font-mono text-rose-400/70 bg-rose-950/30 rounded px-2 py-1">
                          <span>SR: {formatNum(s.sharpe)}</span>
                          <span>Ret: {formatPct(s.return)}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 italic text-center py-8">No strategies assigned.</p>
                )}
              </div>
            </div>

          </div>
        </section>

      </div>
    </main>
  );
}
