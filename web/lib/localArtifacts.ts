import fs from 'fs/promises';
import path from 'path';

export const REPO_ROOT = path.resolve(process.cwd(), '..');

// Adjust path if process.cwd() is inside web/ or root
export function getRepoRoot() {
  const cwd = process.cwd();
  if (cwd.endsWith('web')) {
    return path.resolve(cwd, '..');
  }
  return cwd;
}

export async function readJsonArtifact<T>(relativePath: string): Promise<T | null> {
  try {
    const root = getRepoRoot();
    const filePath = path.join(root, relativePath);
    const data = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(data) as T;
  } catch (error) {
    console.warn(`Failed to read artifact at ${relativePath}:`, error);
    return null;
  }
}

export interface SelectionArtifact {
  schema_version: string;
  portfolio_id: string;
  timestamp_gmt8: string;
  selection: {
    BULL: string[];
    BEAR: string[];
    NEUTRAL: string[];
  };
  policy?: {
    enabled_regimes: string[];
    top_n_per_regime: number;
  };
  metadata?: {
    git_commit: string;
  };
}

export interface RegimeArtifact {
  current_regime: string;
  timestamp: string;
  // TODO: Add full schema
}
