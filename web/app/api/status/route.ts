import { NextResponse } from 'next/server';
import { readJsonArtifact, SelectionArtifact } from '../../../lib/localArtifacts';
import path from 'path';
import fs from 'fs/promises';

export const dynamic = 'force-dynamic';

interface ServiceHeartbeat {
  name: string;
  status: string;
}

interface TimelineEvent {
  ts: string;
  type: 'signal' | 'execution' | 'system';
  summary: string;
  status: 'ok' | 'warn' | 'error';
}

interface CoverageSummary {
  windowsTotal: number | null;
  windowsCompleted: number | null;
  windowsFailed: number | null;
  latestBacktestTs: string | null;
  source: string;
}

interface HongVsBh {
  hongReturn: number | null;
  buyHoldReturn: number | null;
  delta: number | null;
  source: string;
}

interface StatusPayload {
  executionMode: string;
  detail: string;
  offlineMode: string;
  portfolioId: string;
  updatedAtUtc: string | null;
  services: ServiceHeartbeat[];
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
  rows?: any[];
  ts_utc?: string;
}

interface RegimeMonitorSummary {
  status: 'OK' | 'WARN' | 'FAIL' | 'UNKNOWN';
  updatedAtUtc: string | null;
  topReason: string | null;
}

interface FreshnessItem {
  symbol: string;
  tf: string;
  age_h: number | null;
  status: 'OK' | 'WARN' | 'FAIL';
  reason?: string | null;
  source?: string | null;
}

interface FreshnessTable {
  generated_utc: string;
  thresholds: { ok_h: number; warn_h: number };
  rows: FreshnessItem[];
}

interface BacktestRun {
  id: string;
  date: string;
  runId: string;
  mtime: string;
  isFull: boolean;
  flags: {
    selection: boolean;
    summary: boolean;
    gate: boolean;
    regime: boolean;
    optimizer: boolean;
  };
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
  allRuns: BacktestRun[];
  topFullRuns: BacktestRun[];
  currentRunId: string | null;
  freshnessTable: FreshnessTable | null;
}

interface WalkforwardLatest {
  windows_total?: number;
  windows_completed?: number;
  windows_failed?: number;
}

function cleanEnvValue(raw: string): string {
  return raw.replace(/^['"]|['"]$/g, '').trim();
}

async function readJsonOptional<T>(relativePath: string): Promise<T | null> {
  try {
    const root = path.resolve(process.cwd(), '..');
    const filePath = path.join(root, relativePath);
    const content = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(content) as T;
  } catch {
    return null;
  }
}

async function readEnvConfig(root: string): Promise<Record<string, string>> {
  const out: Record<string, string> = {};
  try {
    const envPath = path.join(root, '.env');
    const content = await fs.readFile(envPath, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue;
      const idx = trimmed.indexOf('=');
      const key = trimmed.slice(0, idx).trim();
      const val = cleanEnvValue(trimmed.slice(idx + 1));
      if (key) out[key] = val;
    }
  } catch {
    // .env is optional
  }
  return out;
}

async function readJsonlTail(relativePath: string, limit: number): Promise<Record<string, unknown>[]> {
  try {
    const root = path.resolve(process.cwd(), '..');
    const filePath = path.join(root, relativePath);
    const content = await fs.readFile(filePath, 'utf-8');
    const lines = content
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    const parsed: Record<string, unknown>[] = [];
    for (const line of lines.slice(-limit)) {
      try {
        const obj = JSON.parse(line) as Record<string, unknown>;
        parsed.push(obj);
      } catch {
        // Skip malformed lines
      }
    }
    return parsed;
  } catch {
    return [];
  }
}

function toIsoString(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function extractString(obj: Record<string, unknown>, key: string): string | null {
  const value = obj[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function buildTimelineEventFromIntent(entry: Record<string, unknown>): TimelineEvent | null {
  const ts = toIsoString(entry.ts) ?? new Date().toISOString();
  const signal = entry.signal;
  if (!signal || typeof signal !== 'object') return null;

  const signalObj = signal as Record<string, unknown>;
  const direction = extractString(signalObj, 'direction') ?? 'UNKNOWN';
  const symbol = extractString(signalObj, 'symbol') ?? 'UNKNOWN';
  const regime = extractString(signalObj, 'regime') ?? 'UNKNOWN';

  return {
    ts,
    type: 'signal',
    summary: `${symbol} ${direction} (${regime})`,
    status: 'ok',
  };
}

function buildTimelineEventFromExecution(entry: Record<string, unknown>): TimelineEvent | null {
  const ts = toIsoString(entry.ts) ?? new Date().toISOString();
  const orderValue = entry.order;
  const resultValue = entry.result;

  if (!orderValue || typeof orderValue !== 'object' || !resultValue || typeof resultValue !== 'object') {
    return null;
  }

  const order = orderValue as Record<string, unknown>;
  const result = resultValue as Record<string, unknown>;

  const symbol = extractString(order, 'symbol') ?? 'UNKNOWN';
  const side = extractString(order, 'side') ?? 'UNKNOWN';
  const statusRaw = extractString(result, 'status') ?? 'UNKNOWN';
  const status = statusRaw.toUpperCase() === 'FILLED' ? 'ok' : 'warn';

  return {
    ts,
    type: 'execution',
    summary: `${symbol} ${side} -> ${statusRaw}`,
    status,
  };
}

async function buildStatus(envConfig: Record<string, string>): Promise<StatusPayload> {
  const executionMode = await readJsonArtifact<Record<string, unknown>>('data/state/execution_mode.json');
  const heartbeat = await readJsonArtifact<Record<string, unknown>>('data/state/services_heartbeat.json');

  const modeFromArtifact = executionMode && typeof executionMode.mode === 'string' ? executionMode.mode : null;
  const detailFromArtifact = executionMode && typeof executionMode.detail === 'string' ? executionMode.detail : null;
  const updatedAtUtc =
    executionMode && typeof executionMode.updated_at_utc === 'string'
      ? executionMode.updated_at_utc
      : executionMode && typeof executionMode.last_updated_utc === 'string'
        ? executionMode.last_updated_utc
        : null;

  const services: ServiceHeartbeat[] = [];
  const rawServices = heartbeat?.services;
  if (Array.isArray(rawServices)) {
    for (const item of rawServices) {
      if (!item || typeof item !== 'object') continue;
      const service = item as Record<string, unknown>;
      const name = typeof service.name === 'string' ? service.name : 'unknown';
      const status = typeof service.status === 'string' ? service.status : 'unknown';
      services.push({ name, status });
    }
  } else if (rawServices && typeof rawServices === 'object') {
    // SSOT producer format in state_snapshots.py: {"services": {"name": {"status": ...}}}
    for (const [name, value] of Object.entries(rawServices as Record<string, unknown>)) {
      const service = value && typeof value === 'object' ? value as Record<string, unknown> : {};
      const status = typeof service.status === 'string' ? service.status : 'unknown';
      services.push({ name, status });
    }
  }

  return {
    executionMode: envConfig.EXECUTION_MODE || modeFromArtifact || 'LOCAL',
    detail: detailFromArtifact || 'N/A',
    offlineMode: envConfig.OFFLINE_MODE || 'UNKNOWN',
    portfolioId: envConfig.PORTFOLIO_ID || 'HONG',
    updatedAtUtc,
    services,
  };
}

async function buildHongVsBh(): Promise<HongVsBh> {
  const benchmark = await readJsonOptional<Record<string, unknown>>('reports/benchmark_latest.json');
  if (!benchmark) {
    return {
      hongReturn: null,
      buyHoldReturn: null,
      delta: null,
      source: 'missing reports/benchmark_latest.json',
    };
  }

  const full = benchmark.FULL as Record<string, unknown> | undefined;
  const top = full?.top as Record<string, unknown> | undefined;
  const hongReturn = typeof top?.total_return === 'number' ? top.total_return : null;

  let buyHoldReturn: number | null = null;
  if (typeof top?.buy_hold_return === 'number') {
    buyHoldReturn = top.buy_hold_return;
  }

  return {
    hongReturn,
    buyHoldReturn,
    delta: hongReturn !== null && buyHoldReturn !== null ? hongReturn - buyHoldReturn : null,
    source: 'reports/benchmark_latest.json',
  };
}

async function buildTop3(selection: SelectionArtifact | null): Promise<string[]> {
  if (!selection?.selection) return [];

  const set = new Set<string>();
  for (const key of ['BULL', 'BEAR', 'NEUTRAL'] as const) {
    const arr = selection.selection[key];
    if (!Array.isArray(arr)) continue;
    for (const name of arr) {
      if (typeof name === 'string' && name.trim()) set.add(name.trim());
    }
  }
  return Array.from(set).slice(0, 3);
}

async function buildCoverageSummary(): Promise<CoverageSummary> {
  const walkforward = await readJsonOptional<WalkforwardLatest>('reports/walkforward_latest.json');

  let latestBacktestTs: string | null = null;
  try {
    const csvPath = path.join(path.resolve(process.cwd(), '..'), 'data/reports/daily_backtest_health.csv');
    const csv = await fs.readFile(csvPath, 'utf-8');
    const rows = csv
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    if (rows.length > 1) {
      const headers = rows[0].split(',');
      const tsIndex = headers.indexOf('ts');
      if (tsIndex >= 0) {
        const last = rows[rows.length - 1].split(',');
        latestBacktestTs = last[tsIndex] || null;
      }
    }
  } catch {
    // ignore optional csv
  }

  return {
    windowsTotal: walkforward?.windows_total ?? null,
    windowsCompleted: walkforward?.windows_completed ?? null,
    windowsFailed: walkforward?.windows_failed ?? null,
    latestBacktestTs,
    source: walkforward ? 'reports/walkforward_latest.json' : 'missing reports/walkforward_latest.json',
  };
}

async function buildTimeline(): Promise<TimelineEvent[]> {
  const [intents, executions] = await Promise.all([
    readJsonlTail('data/state/execution_intent.jsonl', 20),
    readJsonlTail('data/state/execution_result.jsonl', 20),
  ]);

  const items: TimelineEvent[] = [];

  for (const entry of intents) {
    const event = buildTimelineEventFromIntent(entry);
    if (event) items.push(event);
  }

  for (const entry of executions) {
    const event = buildTimelineEventFromExecution(entry);
    if (event) items.push(event);
  }

  items.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
  return items.slice(0, 12);
}

async function buildStrategyPool(): Promise<StrategyPoolSummary | null> {
  const summary = await readJsonOptional<any>('data/state/strategy_pool_summary.json');
  if (!summary) return null;

  return {
    poolId: summary.pool_id || 'hongstr_main_pool',
    candidatesCount: summary.counts?.candidates || 0,
    promotedCount: summary.counts?.promoted || 0,
    leaderboard: summary.leaderboard || []
  };
}

async function buildCoverageMatrix(): Promise<CoverageMatrixSummary | null> {
  const snapshot = await readJsonOptional<any>('data/state/coverage_matrix_latest.json');
  if (!snapshot || !snapshot.totals) return null;

  return {
    ...snapshot.totals,
    rows: snapshot.rows,
    ts_utc: snapshot.ts_utc
  };
}

async function buildRegimeMonitor(): Promise<RegimeMonitorSummary | null> {
  const data = await readJsonOptional<any>('data/state/regime_monitor_summary.json');
  if (!data) return null;

  return {
    status: data.status || 'UNKNOWN',
    updatedAtUtc: data.updated_utc || null,
    topReason: Array.isArray(data.reasons) && data.reasons.length > 0 ? data.reasons[0] : null,
  };
}

async function buildFreshnessTable(): Promise<FreshnessTable | null> {
  return await readJsonOptional<FreshnessTable>('data/state/freshness_table.json');
}

async function listBacktestRuns(root: string, limit = 100): Promise<BacktestRun[]> {
  const backtestDir = path.join(root, 'data/backtests');
  const runs: BacktestRun[] = [];

  try {
    const dates = await fs.readdir(backtestDir);
    for (const date of dates) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
      const datePath = path.join(backtestDir, date);
      const stat = await fs.stat(datePath);
      if (!stat.isDirectory()) continue;

      const runIds = await fs.readdir(datePath);
      for (const runId of runIds) {
        const runDir = path.join(datePath, runId);
        const runStat = await fs.stat(runDir);
        if (!runStat.isDirectory()) continue;

        const summaryPath = path.join(runDir, 'summary.json');
        let summaryExists = false;
        let summaryMtime = runStat.mtime;
        try {
          const sStat = await fs.stat(summaryPath);
          summaryExists = true;
          summaryMtime = sStat.mtime;
        } catch { }

        if (!summaryExists) continue;

        const hasSelection = await fs.access(path.join(runDir, 'selection.json')).then(() => true).catch(() => false);
        const hasGate = await fs.access(path.join(runDir, 'gate.json')).then(() => true).catch(() => false);
        const hasRegime = await fs.access(path.join(runDir, 'regime_report.json')).then(() => true).catch(() => false);
        const hasOptimizer = (await fs.access(path.join(runDir, 'optimizer_regime.json')).then(() => true).catch(() => false)) ||
          (await fs.access(path.join(runDir, 'optimizer.json')).then(() => true).catch(() => false));

        runs.push({
          id: `${date}/${runId}`,
          date,
          runId,
          mtime: summaryMtime.toISOString(),
          isFull: hasSelection && summaryExists,
          flags: {
            selection: hasSelection,
            summary: summaryExists,
            gate: hasGate,
            regime: hasRegime,
            optimizer: hasOptimizer,
          },
        });
      }
    }
  } catch (e) {
    console.error('Error listing backtest runs:', e);
  }

  // Sort by mtime DESC
  return runs.sort((a, b) => new Date(b.mtime).getTime() - new Date(a.mtime).getTime()).slice(0, limit);
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const requestedRun = searchParams.get('run');

  const root = path.resolve(process.cwd(), '..');
  const envConfig = await readEnvConfig(root);

  const allRuns = await listBacktestRuns(root);
  const topFullRuns = allRuns.filter(r => r.isFull).slice(0, 3);

  // Determine which run to use for selection
  let currentRunId = requestedRun;
  if (!currentRunId && topFullRuns.length > 0) {
    currentRunId = topFullRuns[0].id;
  }

  let selection: SelectionArtifact | null = null;
  if (currentRunId) {
    selection = await readJsonArtifact<SelectionArtifact>(path.join('data/backtests', currentRunId, 'selection.json'));
  }

  // Fallback to global selection if still null and no specific run was requested
  if (!selection && !requestedRun) {
    selection = await readJsonArtifact<SelectionArtifact>('data/selection/hong_selected.json');
  }

  const [status, hongVsBh, top3, coverage, timeline, strategyPool, coverageMatrix, regimeMonitor, freshnessTable] = await Promise.all([
    buildStatus(envConfig),
    buildHongVsBh(),
    buildTop3(selection),
    buildCoverageSummary(),
    buildTimeline(),
    buildStrategyPool(),
    buildCoverageMatrix(),
    buildRegimeMonitor(),
    buildFreshnessTable(),
  ]);

  const warnings: string[] = [];
  if (!selection) warnings.push('selection artifact missing: data/selection/hong_selected.json');
  if (hongVsBh.hongReturn === null) warnings.push('benchmark missing or incomplete: reports/benchmark_latest.json');
  if (coverage.windowsTotal === null) warnings.push('coverage summary unavailable: reports/walkforward_latest.json');
  if (timeline.length === 0) warnings.push('event timeline unavailable: data/state/execution_*.jsonl');
  if (!strategyPool) warnings.push('strategy pool missing: data/state/strategy_pool_summary.json');

  return NextResponse.json({
    ok: true,
    status,
    hongVsBh,
    top3,
    coverage,
    timeline,
    selection,
    warnings,
    strategyPool,
    coverageMatrix,
    regimeMonitor,
    allRuns,
    topFullRuns,
    currentRunId,
    freshnessTable,
    timestamp: new Date().toISOString(),
  });
}
