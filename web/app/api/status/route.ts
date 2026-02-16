import { NextResponse } from 'next/server';
import { readJsonArtifact, SelectionArtifact, RegimeArtifact } from '@/lib/localArtifacts';
import path from 'path';
import fs from 'fs/promises';

export const dynamic = 'force-dynamic'; // Ensure no caching

export async function GET() {
    const root = path.resolve(process.cwd(), '..');

    // 1. Read .env (naive parse, do not use process.env to avoid build-time baking if not careful, but better to read file directly for real-time status in dev mode)
    // Actually, in Next.js backend, process.env should work if loaded. 
    // But since we are local dev, we might want to read .env file directly to get changes without restart? 
    // Standard way: process.env.
    // User scope specifically asked to read .env safely.

    let envConfig: Record<string, string> = {};
    try {
        const envPath = path.join(root, '.env');
        const envContent = await fs.readFile(envPath, 'utf-8');
        envContent.split('\n').forEach(line => {
            const parts = line.split('=');
            if (parts.length >= 2) {
                const key = parts[0].trim();
                const val = parts.slice(1).join('=').trim();
                if (['EXECUTION_MODE', 'OFFLINE_MODE', 'PORTFOLIO_ID'].includes(key)) {
                    envConfig[key] = val;
                }
            }
        });
    } catch (e) {
        console.warn("Could not read .env", e);
    }

    // 2. Read Artifacts
    const selection = await readJsonArtifact<SelectionArtifact>('data/selection/hong_selected.json');
    const regime = await readJsonArtifact<RegimeArtifact>('data/state/regime.json');

    return NextResponse.json({
        ok: true,
        status: {
            executionMode: envConfig['EXECUTION_MODE'] || 'UNKNOWN',
            offlineMode: envConfig['OFFLINE_MODE'] || 'UNKNOWN',
            portfolioId: envConfig['PORTFOLIO_ID'] || 'UNKNOWN',
        },
        selection,
        regime,
        timestamp: new Date().toISOString()
    });
}
