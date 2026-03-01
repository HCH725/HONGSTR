import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function GET() {
    try {
        // Determine the repo root based on typical structure:
        // next app is in /web, so repo root is /
        const repoRoot = path.resolve(process.cwd(), '..');
        const ssotPath = path.join(repoRoot, 'data', 'state', 'strategy_dashboard_latest.json');

        const fileContent = await fs.readFile(ssotPath, 'utf-8');
        const data = JSON.parse(fileContent);

        return NextResponse.json(data);
    } catch (error: any) {
        if (error.code === 'ENOENT') {
            return NextResponse.json(
                { error: 'strategy_dashboard_latest.json not found. Run scripts/refresh_state.sh to generate it.' },
                { status: 404 }
            );
        }

        console.error('Failed to read Strategy Dashboard SSOT:', error);
        return NextResponse.json(
            { error: 'Internal Server Error loading strategy dashboard data.' },
            { status: 500 }
        );
    }
}
