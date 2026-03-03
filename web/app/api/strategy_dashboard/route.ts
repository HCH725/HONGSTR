import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export const dynamic = 'force-dynamic';

async function readStrategyDashboard(): Promise<Record<string, unknown>> {
  const repoRoot = path.resolve(process.cwd(), '..');
  const filePath = path.join(repoRoot, 'data/state/strategy_dashboard_latest.json');
  const content = await fs.readFile(filePath, 'utf-8');
  const parsed = JSON.parse(content) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('invalid_payload');
  }
  return parsed as Record<string, unknown>;
}

export async function GET() {
  try {
    const payload = await readStrategyDashboard();
    return NextResponse.json(payload, { status: 200 });
  } catch (error) {
    const code = (error as NodeJS.ErrnoException | null)?.code;
    const status = code === 'ENOENT' ? 404 : 500;
    const message =
      status === 404
        ? 'Strategy dashboard SSOT missing. Run: bash scripts/refresh_state.sh'
        : 'Strategy dashboard SSOT unreadable. Run: bash scripts/refresh_state.sh';
    return NextResponse.json(
      {
        ok: false,
        message,
      },
      { status },
    );
  }
}
