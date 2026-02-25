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

type JsonReadError = 'missing' | 'unreadable';

interface ReadStateJsonResult<T> {
  data: T | null;
  error: JsonReadError | null;
}

interface SystemHealthComponents {
  freshness?: Record<string, unknown>;
  coverage_matrix?: Record<string, unknown>;
  brake?: Record<string, unknown>;
  regime_monitor?: Record<string, unknown>;
  regime_signal?: Record<string, unknown>;
}

interface SystemHealthPack {
  generated_utc?: string;
  ssot_status?: string;
  refresh_hint?: string;
  components?: SystemHealthComponents;
  sources?: Record<string, unknown>;
}

interface DashboardSsotContext {
  mode: 'health-pack' | 'fallback' | 'unknown';
  refreshHint: string;
  missing: string[];
  unreadable: string[];
  healthPack: SystemHealthPack | null;
  freshnessTable: FreshnessTable | null;
  coverageMatrixSnapshot: Record<string, unknown> | null;
  brakeHealth: Record<string, unknown> | null;
  regimeMonitorLatest: Record<string, unknown> | null;
}

const SSOT_REFRESH_HINT = 'bash scripts/refresh_state.sh';
const SSOT_FALLBACK_FILES = [
  'data/state/freshness_table.json',
  'data/state/coverage_matrix_latest.json',
  'data/state/brake_health_latest.json',
  'data/state/regime_monitor_latest.json',
] as const;

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

async function readStateJsonWithError<T>(relativePath: string): Promise<ReadStateJsonResult<T>> {
  const root = path.resolve(process.cwd(), '..');
  const filePath = path.join(root, relativePath);
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    try {
      return { data: JSON.parse(content) as T, error: null };
    } catch {
      return { data: null, error: 'unreadable' };
    }
  } catch (err) {
    const code = (err as NodeJS.ErrnoException | null)?.code;
    if (code === 'ENOENT') {
      return { data: null, error: 'missing' };
    }
    return { data: null, error: 'unreadable' };
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function normalizeHealthStatus(value: unknown): 'OK' | 'WARN' | 'FAIL' | 'UNKNOWN' {
  const raw = typeof value === 'string' ? value.trim().toUpperCase() : '';
  if (raw === 'PASS') return 'OK';
  if (raw === 'OK' || raw === 'WARN' || raw === 'FAIL') return raw;
  return 'UNKNOWN';
}

function extractHealthSourceTs(healthPack: SystemHealthPack | null, sourceName: string): string | null {
  const sources = asRecord(healthPack?.sources);
  if (!sources) return null;
  const source = asRecord(sources[sourceName]);
  if (!source) return null;
  const ts = source.ts_utc;
  return typeof ts === 'string' && ts.trim() ? ts : null;
}

function toFreshnessTable(value: unknown): FreshnessTable | null {
  const obj = asRecord(value);
  if (!obj) return null;
  if (!Array.isArray(obj.rows)) return null;
  return obj as unknown as FreshnessTable;
}

function extractRegimeReason(regimeLatest: Record<string, unknown> | null): string | null {
  if (!regimeLatest) return null;
  const reasonValue = regimeLatest.reason;
  if (Array.isArray(reasonValue) && reasonValue.length > 0 && typeof reasonValue[0] === 'string') {
    const reason = reasonValue[0].trim();
    return reason || null;
  }
  return null;
}

async function loadDashboardSsotContext(): Promise<DashboardSsotContext> {
  const healthPackResult = await readStateJsonWithError<SystemHealthPack>('data/state/system_health_latest.json');
  const healthPack = healthPackResult.data && asRecord(healthPackResult.data.components)
    ? healthPackResult.data
    : null;
  const refreshHint =
    healthPack && typeof healthPack.refresh_hint === 'string' && healthPack.refresh_hint.trim()
      ? healthPack.refresh_hint.trim()
      : SSOT_REFRESH_HINT;

  const [freshnessResult, coverageResult, brakeResult, regimeResult] = await Promise.all([
    readStateJsonWithError<FreshnessTable>(SSOT_FALLBACK_FILES[0]),
    readStateJsonWithError<Record<string, unknown>>(SSOT_FALLBACK_FILES[1]),
    readStateJsonWithError<Record<string, unknown>>(SSOT_FALLBACK_FILES[2]),
    readStateJsonWithError<Record<string, unknown>>(SSOT_FALLBACK_FILES[3]),
  ]);

  const missing: string[] = [];
  const unreadable: string[] = [];
  const appendError = (relativePath: string, error: JsonReadError | null) => {
    if (error === 'missing') missing.push(path.basename(relativePath));
    if (error === 'unreadable') unreadable.push(path.basename(relativePath));
  };
  appendError(SSOT_FALLBACK_FILES[0], freshnessResult.error);
  appendError(SSOT_FALLBACK_FILES[1], coverageResult.error);
  appendError(SSOT_FALLBACK_FILES[2], brakeResult.error);
  appendError(SSOT_FALLBACK_FILES[3], regimeResult.error);

  const mode: DashboardSsotContext['mode'] = healthPack
    ? 'health-pack'
    : missing.length === 0 && unreadable.length === 0
      ? 'fallback'
      : 'unknown';

  return {
    mode,
    refreshHint,
    missing,
    unreadable,
    healthPack,
    freshnessTable: toFreshnessTable(freshnessResult.data),
    coverageMatrixSnapshot: asRecord(coverageResult.data),
    brakeHealth: asRecord(brakeResult.data),
    regimeMonitorLatest: asRecord(regimeResult.data),
  };
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

async function buildStatus(envConfig: Record<string, string>, ssotContext: DashboardSsotContext): Promise<StatusPayload> {
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

  const fallbackDetail =
    ssotContext.mode === 'unknown'
      ? `UNKNOWN (Run: ${ssotContext.refreshHint})`
      : ssotContext.mode === 'health-pack'
        ? `SSOT=${normalizeHealthStatus(ssotContext.healthPack?.ssot_status)}`
        : 'N/A';

  return {
    executionMode: envConfig.EXECUTION_MODE || modeFromArtifact || 'LOCAL',
    detail: detailFromArtifact || fallbackDetail,
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

async function buildCoverageSummary(ssotContext: DashboardSsotContext): Promise<CoverageSummary> {
  if (ssotContext.mode === 'health-pack' && ssotContext.healthPack) {
    const coverage = asRecord(ssotContext.healthPack.components?.coverage_matrix);
    const done = asNumber(coverage?.done);
    const total = asNumber(coverage?.total);
    const blocked = asNumber(coverage?.blocked);
    return {
      windowsTotal: total,
      windowsCompleted: done,
      windowsFailed: blocked,
      latestBacktestTs:
        extractHealthSourceTs(ssotContext.healthPack, 'coverage_matrix_latest.json')
        || ssotContext.healthPack.generated_utc
        || null,
      source: 'data/state/system_health_latest.json',
    };
  }

  if (ssotContext.mode === 'fallback' && ssotContext.coverageMatrixSnapshot) {
    const totals = asRecord(ssotContext.coverageMatrixSnapshot.totals);
    const done = asNumber(totals?.done);
    const inProgress = asNumber(totals?.inProgress);
    const blocked = asNumber(totals?.blocked);
    const hasAny = done !== null || inProgress !== null || blocked !== null;
    return {
      windowsTotal: hasAny ? (done ?? 0) + (inProgress ?? 0) + (blocked ?? 0) : null,
      windowsCompleted: done,
      windowsFailed: blocked,
      latestBacktestTs:
        (typeof ssotContext.coverageMatrixSnapshot.ts_utc === 'string'
          ? ssotContext.coverageMatrixSnapshot.ts_utc
          : null),
      source: 'data/state/coverage_matrix_latest.json',
    };
  }

  return {
    windowsTotal: null,
    windowsCompleted: null,
    windowsFailed: null,
    latestBacktestTs: null,
    source: `UNKNOWN (Run: ${ssotContext.refreshHint})`,
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

async function buildCoverageMatrix(ssotContext: DashboardSsotContext): Promise<CoverageMatrixSummary | null> {
  if (ssotContext.mode === 'health-pack' && ssotContext.healthPack) {
    const coverage = asRecord(ssotContext.healthPack.components?.coverage_matrix);
    if (!coverage) return null;
    const done = asNumber(coverage.done) ?? 0;
    const total = asNumber(coverage.total) ?? done;
    const blocked = asNumber(coverage.blocked) ?? 0;
    const inProgress = Math.max(0, total - done - blocked);
    return {
      done,
      inProgress,
      blocked,
      rebase: asNumber(coverage.rebase) ?? 0,
      ts_utc:
        extractHealthSourceTs(ssotContext.healthPack, 'coverage_matrix_latest.json')
        || ssotContext.healthPack.generated_utc,
    };
  }

  if (!ssotContext.coverageMatrixSnapshot) return null;
  const totals = asRecord(ssotContext.coverageMatrixSnapshot.totals);
  if (!totals) return null;
  return {
    done: asNumber(totals.done) ?? 0,
    inProgress: asNumber(totals.inProgress) ?? 0,
    blocked: asNumber(totals.blocked) ?? 0,
    rebase: asNumber(totals.rebase) ?? 0,
    rows: Array.isArray(ssotContext.coverageMatrixSnapshot.rows)
      ? ssotContext.coverageMatrixSnapshot.rows
      : undefined,
    ts_utc:
      typeof ssotContext.coverageMatrixSnapshot.ts_utc === 'string'
        ? ssotContext.coverageMatrixSnapshot.ts_utc
        : undefined,
  };
}

async function buildRegimeMonitor(ssotContext: DashboardSsotContext): Promise<RegimeMonitorSummary | null> {
  if (ssotContext.mode === 'health-pack' && ssotContext.healthPack) {
    const regimeMonitor = asRecord(ssotContext.healthPack.components?.regime_monitor);
    const regimeSignal = asRecord(ssotContext.healthPack.components?.regime_signal);
    const topReason =
      typeof regimeSignal?.top_reason === 'string' && regimeSignal.top_reason.trim()
        ? regimeSignal.top_reason
        : extractRegimeReason(ssotContext.regimeMonitorLatest);
    return {
      status: normalizeHealthStatus(regimeMonitor?.status),
      updatedAtUtc:
        extractHealthSourceTs(ssotContext.healthPack, 'regime_monitor_latest.json')
        || ssotContext.healthPack.generated_utc
        || null,
      topReason,
    };
  }

  if (ssotContext.mode === 'fallback' && ssotContext.regimeMonitorLatest) {
    return {
      status: normalizeHealthStatus(ssotContext.regimeMonitorLatest.overall),
      updatedAtUtc:
        typeof ssotContext.regimeMonitorLatest.ts_utc === 'string'
          ? ssotContext.regimeMonitorLatest.ts_utc
          : null,
      topReason: extractRegimeReason(ssotContext.regimeMonitorLatest),
    };
  }

  return {
    status: 'UNKNOWN',
    updatedAtUtc: null,
    topReason: `Run: ${ssotContext.refreshHint}`,
  };
}

async function buildFreshnessTable(ssotContext: DashboardSsotContext): Promise<FreshnessTable | null> {
  if (ssotContext.mode === 'unknown') return null;
  return ssotContext.freshnessTable;
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
  const ssotContext = await loadDashboardSsotContext();

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
    buildStatus(envConfig, ssotContext),
    buildHongVsBh(),
    buildTop3(selection),
    buildCoverageSummary(ssotContext),
    buildTimeline(),
    buildStrategyPool(),
    buildCoverageMatrix(ssotContext),
    buildRegimeMonitor(ssotContext),
    buildFreshnessTable(ssotContext),
  ]);

  const warnings: string[] = [];
  if (!selection) warnings.push('selection artifact missing: data/selection/hong_selected.json');
  if (hongVsBh.hongReturn === null) warnings.push('benchmark missing or incomplete: reports/benchmark_latest.json');
  if (coverage.windowsTotal === null) warnings.push(`coverage summary unavailable: run ${ssotContext.refreshHint}`);
  if (timeline.length === 0) warnings.push('event timeline unavailable: data/state/execution_*.jsonl');
  if (!strategyPool) warnings.push('strategy pool missing: data/state/strategy_pool_summary.json');
  if (ssotContext.mode === 'unknown') {
    const missing = ssotContext.missing.length > 0 ? ssotContext.missing.join(', ') : 'none';
    const unreadable = ssotContext.unreadable.length > 0 ? ssotContext.unreadable.join(', ') : 'none';
    warnings.push(`status SSOT unavailable: missing=[${missing}] unreadable=[${unreadable}]`);
  }
  if (!freshnessTable) warnings.push(`freshness snapshot unavailable: run ${ssotContext.refreshHint}`);

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
