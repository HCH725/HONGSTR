'use client';

import React, { useEffect, useState } from 'react';

type MetricKey = 'total_return' | 'cagr' | 'sharpe' | 'max_drawdown';

interface SeriesPoint {
  ts_utc: string;
  btc_bh: number;
  hong: number | null;
}

interface MetricBlock {
  total_return: number | null;
  cagr: number | null;
  sharpe: number | null;
  max_drawdown: number | null;
  series_points?: number | null;
  curve_available?: boolean;
}

interface RegimeBlock {
  status: string;
  strategies: { name: string; role: string }[];
  kpis: MetricBlock;
  notes: string[];
}

interface StrategyDashboardPayload {
  schema: string;
  generated_utc: string;
  window: {
    start_utc: string;
    end_utc: string;
  };
  series: SeriesPoint[];
  kpis: {
    btc_bh: MetricBlock;
    hong: MetricBlock;
    delta: MetricBlock;
  };
  regimes: Record<string, RegimeBlock>;
  blend: {
    kpis: {
      run_id?: string | null;
      total_return?: number | null;
      cagr?: number | null;
      sharpe?: number | null;
      max_drawdown?: number | null;
      trades_count?: number | null;
      win_rate?: number | null;
      start_ts?: string | null;
      end_ts?: string | null;
    };
    notes: string[];
  };
  sources: {
    refresh_hint?: string;
  };
}

interface ApiErrorPayload {
  ok: false;
  message: string;
}

const CHART_WIDTH = 1120;
const CHART_HEIGHT = 360;
const CHART_PADDING = { top: 24, right: 18, bottom: 28, left: 22 };
const METRIC_ROWS: { key: MetricKey; label: string; kind: 'pct' | 'num' }[] = [
  { key: 'total_return', label: 'Total Return', kind: 'pct' },
  { key: 'cagr', label: 'CAGR', kind: 'pct' },
  { key: 'sharpe', label: 'Sharpe', kind: 'num' },
  { key: 'max_drawdown', label: 'Max DD', kind: 'pct' },
];
const REGIME_ORDER = [
  { key: 'BULL', label: 'Bull', tone: 'from-emerald-500/20 to-emerald-950/20', border: 'border-emerald-500/20', accent: 'text-emerald-300' },
  { key: 'BEAR', label: 'Bear', tone: 'from-rose-500/20 to-rose-950/20', border: 'border-rose-500/20', accent: 'text-rose-300' },
  { key: 'SIDEWAYS', label: 'Sideways', tone: 'from-amber-500/20 to-amber-950/20', border: 'border-amber-500/20', accent: 'text-amber-300' },
];

function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'Unknown';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString();
}

function formatMetric(value: number | null | undefined, kind: 'pct' | 'num'): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'Unavailable';
  if (kind === 'pct') return `${(value * 100).toFixed(2)}%`;
  return value.toFixed(2);
}

function buildPath(points: Array<[number, number]>): string {
  if (points.length === 0) return '';
  return points
    .map(([x, y], index) => `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`)
    .join(' ');
}

function buildSegmentedPath(points: Array<[number, number] | null>): string {
  let path = '';
  let segmentOpen = false;
  for (const point of points) {
    if (point === null) {
      segmentOpen = false;
      continue;
    }
    const [x, y] = point;
    if (!segmentOpen) {
      path += `${path ? ' ' : ''}M ${x.toFixed(2)} ${y.toFixed(2)}`;
      segmentOpen = true;
    } else {
      path += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
    }
  }
  return path;
}

function statusTone(status: string): string {
  const normalized = String(status || '').toUpperCase();
  if (normalized === 'OK') return 'bg-emerald-500/15 text-emerald-300';
  if (normalized === 'WARN') return 'bg-amber-500/15 text-amber-300';
  if (normalized === 'FAIL') return 'bg-rose-500/15 text-rose-300';
  return 'bg-slate-700/40 text-slate-300';
}

export default function StrategyDashboardPage() {
  const [data, setData] = useState<StrategyDashboardPayload | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;

    const load = async () => {
      try {
        const res = await fetch('/api/strategy_dashboard', { cache: 'no-store' });
        const json = (await res.json()) as StrategyDashboardPayload | ApiErrorPayload;
        if (!alive) return;
        if (!res.ok || 'ok' in json) {
          setData(null);
          setErrorMessage((json as ApiErrorPayload).message || 'Strategy dashboard unavailable');
          return;
        }
        setData(json as StrategyDashboardPayload);
        setErrorMessage(null);
      } catch {
        if (!alive) return;
        setData(null);
        setErrorMessage('Failed to load strategy dashboard. Run: bash scripts/refresh_state.sh');
      } finally {
        if (alive) setLoading(false);
      }
    };

    load();
    return () => {
      alive = false;
    };
  }, []);

  if (loading && !data) {
    return (
      <main className="min-h-screen bg-[#07111f] px-6 py-10 text-slate-100">
        <div className="mx-auto max-w-6xl rounded-3xl border border-cyan-900/40 bg-slate-950/70 p-8 shadow-2xl shadow-cyan-950/20">
          Loading strategy dashboard...
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="min-h-screen bg-[#07111f] px-6 py-10 text-slate-100">
        <div className="mx-auto max-w-4xl rounded-3xl border border-amber-500/20 bg-slate-950/70 p-8 shadow-2xl shadow-slate-950/40">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">HONGSTR Strategy Dashboard</h1>
          <p className="mt-4 text-base text-slate-300">{errorMessage || 'Strategy dashboard unavailable.'}</p>
          <p className="mt-3 text-sm text-slate-500">Run: bash scripts/refresh_state.sh</p>
        </div>
      </main>
    );
  }

  const series = Array.isArray(data.series) ? data.series : [];
  const hongVisible = series.some((point) => typeof point.hong === 'number');
  const hoveredPoint =
    hoverIndex !== null && hoverIndex >= 0 && hoverIndex < series.length
      ? series[hoverIndex]
      : series.length > 0
        ? series[series.length - 1]
        : null;

  const values: number[] = [];
  for (const point of series) {
    if (typeof point.btc_bh === 'number') values.push(point.btc_bh);
    if (typeof point.hong === 'number') values.push(point.hong);
  }
  const safeValues = values.length > 0 ? values : [1];
  let minValue = Math.min(...safeValues);
  let maxValue = Math.max(...safeValues);
  if (minValue === maxValue) {
    minValue -= 0.1;
    maxValue += 0.1;
  }
  const padding = (maxValue - minValue) * 0.08;
  minValue -= padding;
  maxValue += padding;

  const plotWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
  const plotHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
  const xAt = (index: number) =>
    CHART_PADDING.left + (series.length <= 1 ? 0 : (index / (series.length - 1)) * plotWidth);
  const yAt = (value: number) =>
    CHART_PADDING.top + ((maxValue - value) / (maxValue - minValue)) * plotHeight;

  const btcPath = buildPath(
    series.map((point, index) => [xAt(index), yAt(point.btc_bh)]),
  );
  const hongPath = buildSegmentedPath(
    series.map((point, index) =>
      typeof point.hong === 'number' ? [xAt(index), yAt(point.hong)] as [number, number] : null,
    ),
  );

  const hoverX =
    hoverIndex !== null && hoverIndex >= 0 && hoverIndex < series.length
      ? xAt(hoverIndex)
      : null;

  const handleChartMove = (event: React.MouseEvent<SVGSVGElement>) => {
    if (series.length === 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const localX = event.clientX - rect.left;
    const clamped = Math.max(CHART_PADDING.left, Math.min(CHART_WIDTH - CHART_PADDING.right, localX));
    const ratio = plotWidth <= 0 ? 0 : (clamped - CHART_PADDING.left) / plotWidth;
    const index = Math.round(ratio * (series.length - 1));
    setHoverIndex(Math.max(0, Math.min(series.length - 1, index)));
  };

  const handleChartLeave = () => setHoverIndex(null);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(17,94,89,0.18),_rgba(7,17,31,1)_45%),linear-gradient(180deg,#07111f_0%,#050b15_100%)] px-4 py-6 text-slate-100 md:px-8 md:py-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <section
          id="hero-chart"
          className="overflow-hidden rounded-3xl border border-cyan-900/35 bg-slate-950/75 shadow-2xl shadow-cyan-950/20"
        >
          <div className="border-b border-cyan-900/20 bg-gradient-to-r from-cyan-500/10 via-transparent to-emerald-500/10 px-6 py-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-cyan-300/80">Strategy / Backtest Only</p>
                <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">
                  BTC Buy &amp; Hold vs HONGSTR
                </h1>
                <p className="mt-2 max-w-3xl text-sm text-slate-400">
                  SSOT source: <span className="font-mono">data/state/strategy_dashboard_latest.json</span>. Window starts at{' '}
                  <span className="font-mono">{data.window.start_utc}</span>.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-right">
                <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">Updated</p>
                <p className="mt-1 text-sm font-medium text-slate-200">{formatDateTime(data.generated_utc)}</p>
              </div>
            </div>
          </div>

          <div className="px-6 py-5">
            {series.length > 0 ? (
              <>
                <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                    <span className="inline-flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full bg-cyan-300" />
                      BTC Buy &amp; Hold
                    </span>
                    <span className="inline-flex items-center gap-2">
                      <span className={`h-2.5 w-2.5 rounded-full ${hongVisible ? 'bg-emerald-300' : 'bg-slate-600'}`} />
                      HONGSTR blended equity
                    </span>
                  </div>

                  <svg
                    viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                    className="h-[320px] w-full"
                    onMouseMove={handleChartMove}
                    onMouseLeave={handleChartLeave}
                    role="img"
                    aria-label="BTC vs HONGSTR equity chart"
                  >
                    <defs>
                      <linearGradient id="btcStroke" x1="0" x2="1" y1="0" y2="0">
                        <stop offset="0%" stopColor="#67e8f9" />
                        <stop offset="100%" stopColor="#0ea5e9" />
                      </linearGradient>
                      <linearGradient id="hongStroke" x1="0" x2="1" y1="0" y2="0">
                        <stop offset="0%" stopColor="#86efac" />
                        <stop offset="100%" stopColor="#10b981" />
                      </linearGradient>
                    </defs>

                    {[0.2, 0.4, 0.6, 0.8].map((ratio) => {
                      const y = CHART_PADDING.top + plotHeight * ratio;
                      return (
                        <line
                          key={ratio}
                          x1={CHART_PADDING.left}
                          x2={CHART_WIDTH - CHART_PADDING.right}
                          y1={y}
                          y2={y}
                          stroke="rgba(71,85,105,0.25)"
                          strokeWidth="1"
                        />
                      );
                    })}

                    <path d={btcPath} fill="none" stroke="url(#btcStroke)" strokeWidth="3" strokeLinecap="round" />
                    {hongVisible && (
                      <path d={hongPath} fill="none" stroke="url(#hongStroke)" strokeWidth="3" strokeLinecap="round" />
                    )}

                    {hoveredPoint && hoverX !== null && (
                      <>
                        <line
                          x1={hoverX}
                          x2={hoverX}
                          y1={CHART_PADDING.top}
                          y2={CHART_HEIGHT - CHART_PADDING.bottom}
                          stroke="rgba(148,163,184,0.35)"
                          strokeDasharray="5 6"
                          strokeWidth="1"
                        />
                        <circle cx={hoverX} cy={yAt(hoveredPoint.btc_bh)} r="4" fill="#67e8f9" />
                        {typeof hoveredPoint.hong === 'number' && (
                          <circle cx={hoverX} cy={yAt(hoveredPoint.hong)} r="4" fill="#86efac" />
                        )}
                      </>
                    )}
                  </svg>

                  {hoveredPoint && (
                    <div className="pointer-events-none absolute right-5 top-5 rounded-xl border border-slate-800 bg-slate-950/90 px-4 py-3 text-xs shadow-xl shadow-slate-950/40">
                      <p className="font-mono text-slate-200">{formatDateTime(hoveredPoint.ts_utc)}</p>
                      <p className="mt-2 text-cyan-300">BTC: {hoveredPoint.btc_bh.toFixed(3)}x</p>
                      <p className={`mt-1 ${typeof hoveredPoint.hong === 'number' ? 'text-emerald-300' : 'text-slate-500'}`}>
                        HONG: {typeof hoveredPoint.hong === 'number' ? `${hoveredPoint.hong.toFixed(3)}x` : 'Unavailable'}
                      </p>
                    </div>
                  )}
                </div>

                {!hongVisible && (
                  <div className="mt-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                    <p className="font-medium">HONG curve unavailable.</p>
                    <p className="mt-1 text-amber-100/80">
                      The dashboard is intentionally not synthesizing a blended HONGSTR equity line. Summary KPIs can still be shown when
                      a latest <span className="font-mono">summary.json</span> exists. To refresh the underlying state, run{' '}
                      <span className="font-mono">{data.sources?.refresh_hint || 'bash scripts/refresh_state.sh'}</span>.
                    </p>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-5 py-6 text-sm text-amber-100">
                BTC curve unavailable. Run <span className="font-mono">{data.sources?.refresh_hint || 'bash scripts/refresh_state.sh'}</span>{' '}
                after ensuring BTC derived klines exist.
              </div>
            )}

            <div className="mt-5 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/60">
              <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr] border-b border-slate-800 px-4 py-3 text-[11px] uppercase tracking-[0.22em] text-slate-500">
                <div>Metric</div>
                <div>BTC</div>
                <div>HONG</div>
                <div>Delta</div>
              </div>
              {METRIC_ROWS.map((row) => (
                <div
                  key={row.key}
                  className="grid grid-cols-[1.2fr_1fr_1fr_1fr] border-b border-slate-900/70 px-4 py-3 text-sm last:border-b-0"
                >
                  <div className="font-medium text-slate-300">{row.label}</div>
                  <div className="text-cyan-200">{formatMetric(data.kpis.btc_bh[row.key], row.kind)}</div>
                  <div className={hongVisible ? 'text-emerald-200' : 'text-slate-300'}>
                    {formatMetric(data.kpis.hong[row.key], row.kind)}
                  </div>
                  <div className="text-slate-300">{formatMetric(data.kpis.delta[row.key], row.kind)}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.35fr_0.95fr]">
          <article
            id="regime-panel"
            className="rounded-3xl border border-slate-800 bg-slate-950/75 p-6 shadow-xl shadow-slate-950/30"
          >
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Strategy Portfolio</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">Regime Panels</h2>
              </div>
              <p className="text-xs text-slate-500">BULL / BEAR / SIDEWAYS</p>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {REGIME_ORDER.map((regime) => {
                const block = data.regimes?.[regime.key] || {
                  status: 'UNKNOWN',
                  strategies: [],
                  kpis: { total_return: null, cagr: null, sharpe: null, max_drawdown: null },
                  notes: [],
                };
                const hasKpis = METRIC_ROWS.some((item) => block.kpis[item.key] !== null && block.kpis[item.key] !== undefined);

                return (
                  <div
                    key={regime.key}
                    className={`rounded-2xl border ${regime.border} bg-gradient-to-b ${regime.tone} p-4`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className={`text-lg font-semibold ${regime.accent}`}>{regime.label}</p>
                        <p className="mt-1 text-xs text-slate-400">{regime.key}</p>
                      </div>
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusTone(block.status)}`}>
                        {block.status}
                      </span>
                    </div>

                    <div className="mt-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Strategies</p>
                      {block.strategies.length > 0 ? (
                        <div className="mt-2 flex flex-col gap-2">
                          {block.strategies.map((strategy) => (
                            <div
                              key={`${regime.key}-${strategy.name}-${strategy.role}`}
                              className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2"
                            >
                              <span className="font-mono text-sm text-slate-200">{strategy.name}</span>
                              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-slate-400">
                                {strategy.role}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-sm text-slate-500">No regime-specific strategy list is available.</p>
                      )}
                    </div>

                    <div className="mt-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">KPIs</p>
                      {hasKpis ? (
                        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-300">
                          {METRIC_ROWS.map((metric) => (
                            <div key={`${regime.key}-${metric.key}`} className="rounded-xl bg-slate-950/50 px-3 py-2">
                              <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{metric.label}</p>
                              <p className="mt-1 font-medium">{formatMetric(block.kpis[metric.key], metric.kind)}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-sm text-slate-500">Regime KPI slice unavailable.</p>
                      )}
                    </div>

                    {block.notes.length > 0 && (
                      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/45 px-3 py-3 text-xs text-slate-400">
                        {block.notes.map((note) => (
                          <p key={`${regime.key}-${note}`} className="mt-1 first:mt-0">
                            {note}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-800 bg-slate-950/75 p-6 shadow-xl shadow-slate-950/30">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Blended Summary</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">Latest Backtest Pack</h2>
            <p className="mt-2 text-sm text-slate-400">
              {data.blend.kpis.run_id ? (
                <>
                  Run <span className="font-mono text-slate-200">{data.blend.kpis.run_id}</span>
                </>
              ) : (
                'No backtest summary detected.'
              )}
            </p>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Total Return</p>
                <p className="mt-2 text-xl font-semibold text-slate-100">
                  {formatMetric(data.blend.kpis.total_return, 'pct')}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">CAGR</p>
                <p className="mt-2 text-xl font-semibold text-slate-100">
                  {formatMetric(data.blend.kpis.cagr, 'pct')}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Sharpe</p>
                <p className="mt-2 text-xl font-semibold text-slate-100">
                  {formatMetric(data.blend.kpis.sharpe, 'num')}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Max DD</p>
                <p className="mt-2 text-xl font-semibold text-slate-100">
                  {formatMetric(data.blend.kpis.max_drawdown, 'pct')}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Trades</p>
                <p className="mt-2 text-xl font-semibold text-slate-100">
                  {data.blend.kpis.trades_count ?? 'Unavailable'}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Win Rate</p>
                <p className="mt-2 text-xl font-semibold text-slate-100">
                  {formatMetric(data.blend.kpis.win_rate, 'pct')}
                </p>
              </div>
            </div>

            {data.blend.notes.length > 0 && (
              <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/55 px-4 py-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Notes</p>
                <div className="mt-3 flex flex-col gap-2 text-sm text-slate-300">
                  {data.blend.notes.map((note) => (
                    <p key={note}>{note}</p>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/55 px-4 py-4 text-sm text-slate-400">
              <p>Window start: <span className="font-mono text-slate-200">{data.window.start_utc}</span></p>
              <p className="mt-2">Window end: <span className="font-mono text-slate-200">{data.window.end_utc}</span></p>
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}
