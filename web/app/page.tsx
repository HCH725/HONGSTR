'use client';

import { useEffect, useState } from 'react';

interface ServiceHeartbeat {
  name: string;
  status: string;
}

interface StatusPayload {
  executionMode: string;
  detail: string;
  offlineMode: string;
  portfolioId: string;
  updatedAtUtc: string | null;
  services: ServiceHeartbeat[];
}

interface HongVsBh {
  hongReturn: number | null;
  buyHoldReturn: number | null;
  delta: number | null;
  source: string;
}

interface CoverageSummary {
  windowsTotal: number | null;
  windowsCompleted: number | null;
  windowsFailed: number | null;
  latestBacktestTs: string | null;
  source: string;
}

interface TimelineEvent {
  ts: string;
  type: 'signal' | 'execution' | 'system';
  summary: string;
  status: 'ok' | 'warn' | 'error';
}

interface SelectionArtifact {
  schema_version: string;
  portfolio_id: string;
  timestamp_gmt8: string;
  selection: {
    BULL: string[];
    BEAR: string[];
    NEUTRAL: string[];
  };
}

interface StrategyPoolSummary {
  poolId: string;
  candidatesCount: number;
  promotedCount: number;
  leaderboard: { id: string; score: number; sharpe: number }[];
}

interface CoverageMatrixSummary {
  done: number;
  inProgress: number;
  blocked: number;
  rebase: number;
}

interface RegimeMonitorSummary {
  status: 'OK' | 'WARN' | 'FAIL' | 'UNKNOWN';
  updatedAtUtc: string | null;
  topReason: string | null;
}

interface DashboardData {
  ok: boolean;
  status: StatusPayload;
  hongVsBh: HongVsBh;
  top3: string[];
  coverage: CoverageSummary;
  timeline: TimelineEvent[];
  selection: SelectionArtifact | null;
  warnings: string[];
  timestamp: string;
  strategyPool: StrategyPoolSummary | null;
  coverageMatrix: CoverageMatrixSummary | null;
  regimeMonitor: RegimeMonitorSummary | null;
}

function formatPct(value: number | null): string {
  if (value === null || Number.isNaN(value)) return 'N/A';
  return `${(value * 100).toFixed(2)}%`;
}

function formatDateTime(value: string | null): string {
  if (!value) return 'N/A';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function statusTone(status: TimelineEvent['status']): string {
  if (status === 'ok') return 'text-emerald-400';
  if (status === 'warn') return 'text-amber-400';
  return 'text-rose-400';
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        const res = await fetch('/api/status', { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as DashboardData;
        if (!mounted) return;
        setData(json);
        setError(null);
      } catch (err) {
        console.error(err);
        if (!mounted) return;
        setError('Failed to fetch dashboard status');
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchData();
    const timer = setInterval(fetchData, 10000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  if (loading && !data) {
    return <main className="min-h-screen bg-slate-950 p-6 text-slate-100">Loading dashboard...</main>;
  }

  if (error && !data) {
    return (
      <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
        <div className="mx-auto max-w-6xl rounded-xl border border-rose-700/40 bg-rose-950/30 p-4 text-rose-200">
          {error}
        </div>
      </main>
    );
  }

  if (!data) return null;

  const offline = data.status.offlineMode.toLowerCase() === 'true' || data.status.offlineMode === '1';

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-6 text-slate-100 md:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">HONGSTR Dashboard (Read-only)</h1>
              <p className="mt-1 text-sm text-slate-400">Updated: {formatDateTime(data.timestamp)}</p>
            </div>
            <div className={`rounded-lg px-3 py-2 text-sm font-semibold ${offline ? 'bg-amber-600/20 text-amber-300' : 'bg-emerald-600/20 text-emerald-300'}`}>
              {offline ? 'OFFLINE MODE' : `LIVE (${data.status.executionMode})`}
            </div>
          </div>
          {data.warnings.length > 0 && (
            <div className="mt-4 rounded-lg border border-amber-600/40 bg-amber-950/40 p-3 text-xs text-amber-200">
              <p className="mb-2 font-semibold">Warnings</p>
              <ul className="list-disc space-y-1 pl-5">
                {data.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </header>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <h2 className="mb-3 text-lg font-semibold">狀態列</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-slate-400">Portfolio</span>
                <span className="font-mono">{data.status.portfolioId}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-400">Execution Mode</span>
                <span className="font-mono">{data.status.executionMode}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-400">Detail</span>
                <span className="font-mono">{data.status.detail}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-400">Mode Updated</span>
                <span className="font-mono">{formatDateTime(data.status.updatedAtUtc)}</span>
              </div>
              <div className="pt-2">
                <p className="mb-1 text-slate-400">Services</p>
                {data.status.services.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {data.status.services.map((service) => (
                      <span key={`${service.name}:${service.status}`} className="rounded bg-slate-800 px-2 py-1 text-xs">
                        {service.name}: {service.status}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No service heartbeat found.</p>
                )}
              </div>
            </div>
          </article>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <h2 className="mb-3 text-lg font-semibold">HONG vs B&amp;H</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-800/70 p-3">
                <p className="text-xs text-slate-400">HONG Return</p>
                <p className="mt-1 text-xl font-semibold">{formatPct(data.hongVsBh.hongReturn)}</p>
              </div>
              <div className="rounded-xl bg-slate-800/70 p-3">
                <p className="text-xs text-slate-400">B&amp;H Return</p>
                <p className="mt-1 text-xl font-semibold">{formatPct(data.hongVsBh.buyHoldReturn)}</p>
              </div>
              <div className="rounded-xl bg-slate-800/70 p-3">
                <p className="text-xs text-slate-400">Delta</p>
                <p className="mt-1 text-xl font-semibold">{formatPct(data.hongVsBh.delta)}</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-500">Source: {data.hongVsBh.source}</p>
          </article>
        </section>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <h2 className="mb-3 text-lg font-semibold">Top3</h2>
            {data.top3.length > 0 ? (
              <ol className="space-y-2">
                {data.top3.map((name, idx) => (
                  <li key={name} className="flex items-center gap-3 rounded-lg bg-slate-800/60 p-2 text-sm">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-cyan-700/40 text-xs font-semibold">
                      {idx + 1}
                    </span>
                    <span className="font-mono">{name}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-slate-500">No strategy selection available.</p>
            )}
          </article>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <h2 className="mb-3 text-lg font-semibold">Coverage 摘要</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-800/70 p-3">
                <p className="text-xs text-slate-400">Windows</p>
                <p className="mt-1 text-lg font-semibold">
                  {data.coverage.windowsCompleted ?? 'N/A'} / {data.coverage.windowsTotal ?? 'N/A'}
                </p>
              </div>
              <div className="rounded-xl bg-slate-800/70 p-3">
                <p className="text-xs text-slate-400">Failed</p>
                <p className="mt-1 text-lg font-semibold">{data.coverage.windowsFailed ?? 'N/A'}</p>
              </div>
              <div className="rounded-xl bg-slate-800/70 p-3">
                <p className="text-xs text-slate-400">Latest Backtest</p>
                <p className="mt-1 text-sm font-semibold">{formatDateTime(data.coverage.latestBacktestTs)}</p>
              </div>
            </div>
            {data.coverageMatrix && (
              <div className="mt-4 flex gap-3 text-sm">
                <span className="rounded bg-emerald-900/40 px-2 py-1 text-emerald-300">DONE: {data.coverageMatrix.done}</span>
                <span className="rounded bg-blue-900/40 px-2 py-1 text-blue-300">IN_PROG: {data.coverageMatrix.inProgress}</span>
                <span className="rounded bg-amber-900/40 px-2 py-1 text-amber-300">REBASE: {data.coverageMatrix.rebase}</span>
              </div>
            )}
            <p className="mt-3 text-xs text-slate-500">Source: {data.coverage.source}</p>
          </article>

          {data.regimeMonitor && (
            <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="mb-3 text-lg font-semibold">Regime Monitor</h2>
              <div className="flex items-center gap-4">
                <div className={`rounded-xl px-4 py-3 text-2xl font-bold ${data.regimeMonitor.status === 'OK' ? 'bg-emerald-600/20 text-emerald-400' :
                    data.regimeMonitor.status === 'WARN' ? 'bg-amber-600/20 text-amber-400' :
                      data.regimeMonitor.status === 'FAIL' ? 'bg-rose-600/20 text-rose-400' :
                        'bg-slate-800 text-slate-400'
                  }`}>
                  {data.regimeMonitor.status}
                </div>
                <div className="flex-1 text-sm">
                  <p className="text-slate-400">Latest Observation:</p>
                  <p className="font-medium">{data.regimeMonitor.topReason || 'No issues detected'}</p>
                </div>
              </div>
              <p className="mt-4 text-xs text-slate-500">Updated: {formatDateTime(data.regimeMonitor.updatedAtUtc)}</p>
            </article>
          )}
        </section>

        {data.strategyPool && (
          <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">策略池看板 (Strategy Pool)</h2>
              <span className="text-sm text-slate-400 font-mono">Pool: {data.strategyPool.poolId}</span>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4 sm:grid-cols-4">
              <div className="rounded-lg bg-slate-800/40 p-3 text-center">
                <p className="text-xs text-slate-400">Candidates</p>
                <p className="mt-1 text-xl font-bold">{data.strategyPool.candidatesCount}</p>
              </div>
              <div className="rounded-lg bg-slate-800/40 p-3 text-center">
                <p className="text-xs text-slate-400">Promoted</p>
                <p className="mt-1 text-xl font-bold text-amber-400">{data.strategyPool.promotedCount}</p>
              </div>
            </div>

            <h3 className="mb-2 text-sm font-semibold text-slate-300">Leaderboard</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs tracking-wide text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="pb-2 font-medium">Strategy ID</th>
                    <th className="pb-2 font-medium">Score</th>
                    <th className="pb-2 font-medium">OOS Sharpe</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {data.strategyPool.leaderboard.map((strat) => (
                    <tr key={strat.id}>
                      <td className="py-2 font-mono text-cyan-400">{strat.id}</td>
                      <td className="py-2 text-slate-300">{strat.score.toFixed(3)}</td>
                      <td className="py-2 text-slate-300">{strat.sharpe.toFixed(2)}</td>
                    </tr>
                  ))}
                  {data.strategyPool.leaderboard.length === 0 && (
                    <tr><td colSpan={3} className="py-4 text-center text-slate-500">No candidates available</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <h2 className="mb-3 text-lg font-semibold">事件時間軸</h2>
          {data.timeline.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="pb-2 pr-4">Time</th>
                    <th className="pb-2 pr-4">Type</th>
                    <th className="pb-2 pr-4">Summary</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.timeline.map((event) => (
                    <tr key={`${event.ts}:${event.type}:${event.summary}`} className="border-t border-slate-800">
                      <td className="py-2 pr-4 font-mono text-xs text-slate-300">{formatDateTime(event.ts)}</td>
                      <td className="py-2 pr-4 uppercase text-slate-400">{event.type}</td>
                      <td className="py-2 pr-4">{event.summary}</td>
                      <td className={`py-2 font-semibold uppercase ${statusTone(event.status)}`}>{event.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No recent events.</p>
          )}
        </section>
      </div>
    </main>
  );
}
