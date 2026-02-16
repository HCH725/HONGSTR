'use client';

import { useState, useEffect } from 'react';

// Types mirror the API response
interface DashboardData {
  ok: boolean;
  status: {
    executionMode: string;
    offlineMode: string;
    portfolioId: string;
  };
  selection: {
    schema_version: string;
    portfolio_id: string;
    timestamp_gmt8: string;
    selection: {
      BULL: string[];
      BEAR: string[];
      NEUTRAL: string[];
    };
    metadata?: {
      git_commit: string;
    };
  } | null;
  regime: {
    current_regime: string;
    timestamp: string;
  } | null;
  timestamp: string;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error('Network response was not ok');
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch system status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // 10s polling
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) return <div className="p-8 text-center">Loading HONGSTR Dashboard...</div>;
  if (error && !data) return <div className="p-8 text-center text-red-500">Error: {error}</div>;

  if (!data) return null;

  const isOffline = data.status.offlineMode === 'true' || data.status.offlineMode === '1';
  const statusColor = isOffline ? 'bg-red-500' : 'bg-green-600';

  return (
    <main className="min-h-screen bg-gray-900 text-white p-4 md:p-8">
      <header className="mb-8 flex flex-col md:flex-row justify-between items-center bg-gray-800 p-6 rounded-lg shadow-lg">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">HONGSTR Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            Last Updated: {new Date(data.timestamp).toLocaleTimeString()}
          </p>
        </div>
        <div className={`mt-4 md:mt-0 px-4 py-2 rounded font-bold ${statusColor}`}>
          {isOffline ? 'OFFLINE MODE' : `LIVE (${data.status.executionMode})`}
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* Card 1: System Status */}
        <section className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">System Status</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400">Portfolio ID</span>
              <span className="font-mono text-yellow-500">{data.status.portfolioId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Execution Mode</span>
              <span className="font-mono">{data.status.executionMode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Offline Check</span>
              <span className={`font-mono ${isOffline ? 'text-red-400' : 'text-green-400'}`}>
                {data.status.offlineMode}
              </span>
            </div>
          </div>
        </section>

        {/* Card 2: Current Regime */}
        <section className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Market Regime</h2>
          {data.regime ? (
            <div className="text-center py-4">
              <span className="text-4xl font-black text-blue-400">{data.regime.current_regime}</span>
              <p className="text-xs text-gray-500 mt-2">Detected at: {data.regime.timestamp}</p>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 italic">No Regime Data (Determined by Selection)</div>
          )}
        </section>

        {/* Card 3: Selection Artifact */}
        <section className="bg-gray-800 p-6 rounded-lg border border-gray-700 md:col-span-2 xl:col-span-1">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Strategy Selection</h2>
          {data.selection ? (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-bold text-green-400">BULL</h3>
                <div className="flex flex-wrap gap-2 mt-1">
                  {data.selection.selection.BULL.length > 0 ?
                    data.selection.selection.BULL.map(s => <span key={s} className="bg-green-900/50 px-2 py-1 rounded text-xs">{s}</span>)
                    : <span className="text-gray-600 text-xs">None</span>}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-bold text-red-400">BEAR</h3>
                <div className="flex flex-wrap gap-2 mt-1">
                  {data.selection.selection.BEAR.length > 0 ?
                    data.selection.selection.BEAR.map(s => <span key={s} className="bg-red-900/50 px-2 py-1 rounded text-xs">{s}</span>)
                    : <span className="text-gray-600 text-xs">None</span>}
                </div>
              </div>
              <div className="pt-2 border-t border-gray-700">
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Ver: {data.selection.schema_version}</span>
                  <span>Commit: {data.selection.metadata?.git_commit || 'N/A'}</span>
                </div>
                <div className="text-xs text-gray-500 text-right mt-1">
                  {data.selection.timestamp_gmt8}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-red-400">Missing Selection Artifact</div>
          )}
        </section>

        {/* Card 4: Equity Curve Stub */}
        <section className="bg-gray-800 p-6 rounded-lg border border-gray-700 md:col-span-2 xl:col-span-3">
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Performance (Stub)</h2>
          <div className="bg-gray-900 h-64 rounded flex items-center justify-center border border-gray-800">
            <div className="text-center">
              <p className="text-gray-600 mb-2">Equity Curve Placeholder</p>
              <div className="w-full text-xs text-gray-700">
                [ Chart would go here: BTC Buy&Hold vs HONG Equity ]
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
