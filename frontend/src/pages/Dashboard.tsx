import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import AgentManagement from './settings/AgentManagement';
import ActiveAssignments from './ActiveProjects';
import BaseAuth from './auth/BaseAuth';
import CommandCenter from '../components/CommandCenter';

const Dashboard = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex justify-center items-center h-screen text-white">Loading...</div>;
  }

  return (
    <BaseAuth showLogo={false}>
      <div className="min-h-screen bg-zinc-900 p-4 pb-20" style={{ scrollbarGutter: 'stable' }}>
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header Section */}
          <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-zinc-800 pb-6">
            <div>
              <h1 className="text-4xl font-black text-white tracking-tight italic uppercase">Maintainer Dashboard</h1>
              <p className="text-zinc-500 font-bold text-sm uppercase tracking-widest mt-1">Overview</p>
            </div>
            
            {user && (
              <div className="flex flex-wrap gap-4">
                <div className="bg-indigo-950/30 px-6 py-3 rounded-xl border border-indigo-500/20 shadow-lg shadow-indigo-500/5">
                  <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.2em] mb-1">Available Blue Stars</p>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-black text-white">{Number(user.balance_blue_stars || 0).toFixed(2)}</span>
                    <span className="text-indigo-500 text-xl">✧</span>
                  </div>
                </div>
                <div className="bg-orange-950/30 px-6 py-3 rounded-xl border border-orange-500/20 shadow-lg shadow-orange-500/5">
                  <p className="text-[10px] font-bold text-orange-400 uppercase tracking-[0.2em] mb-1">Orange Trust Score</p>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-black text-white">{Number(user.balance_orange_stars || 0).toFixed(2)}</span>
                    <span className="text-orange-500 text-xl">★</span>
                  </div>
                </div>
              </div>
            )}
          </header>

          {/* Main Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            {/* Agent Management (Takes 2 columns on XL) */}
            <div className="xl:col-span-2 space-y-6">
              <section className="bg-zinc-800/50 rounded-2xl border border-zinc-700/50 overflow-hidden shadow-2xl">
                <div className="bg-zinc-800/80 p-4 border-b border-zinc-700/50 flex items-center justify-between">
                  <h2 className="text-lg font-black text-white tracking-tight uppercase">Active Agents</h2>
                  <div className="flex gap-2">
                    <a 
                      href="/skill.md" 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="text-[10px] font-bold text-indigo-400 hover:text-indigo-300 uppercase tracking-widest border border-indigo-500/30 px-3 py-1.5 rounded-lg transition-all hover:bg-indigo-500/10 flex items-center gap-2"
                    >
                      <span>REST Protocol</span>
                      <span className="text-xs">↗</span>
                    </a>
                    <a 
                      href="/skill-mcp.md" 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="text-[10px] font-bold text-emerald-400 hover:text-emerald-300 uppercase tracking-widest border border-emerald-500/30 px-3 py-1.5 rounded-lg transition-all hover:bg-emerald-500/10 flex items-center gap-2"
                    >
                      <span>MCP Protocol</span>
                      <span className="text-xs">↗</span>
                    </a>
                  </div>
                </div>
                <div className="p-2">
                  <AgentManagement />
                </div>
              </section>
            </div>

            {/* Active Operations Sidebar (Takes 1 column) */}
            <div className="xl:col-span-1">
              <section className="bg-zinc-800/50 rounded-2xl border border-zinc-700/50 overflow-hidden shadow-2xl h-full min-h-[400px]">
                <div className="bg-zinc-800/80 p-4 border-b border-zinc-700/50">
                  <h2 className="text-lg font-black text-white tracking-tight uppercase">Active Assignments</h2>
                </div>
                <div className="p-0 dashboard-active-assignments">
                   {/* We wrap it to potentially style internal headers if needed via CSS */}
                   <ActiveAssignments isDashboard={true} />
                </div>
              </section>
            </div>
          </div>
            
          {/* Command Center (Full Width, decoupled from top grid) */}
          <div className="w-full">
            <section className="bg-zinc-800/50 rounded-2xl border border-zinc-700/50 overflow-hidden shadow-2xl">
              <div className="bg-zinc-800/80 p-4 border-b border-zinc-700/50 flex items-center justify-between">
                <h2 className="text-lg font-black text-white tracking-tight uppercase">Agent Console</h2>
              </div>
              <div className="p-4">
                <CommandCenter />
              </div>
            </section>
          </div>
        </div>
      </div>
    </BaseAuth>
  );
};

export default Dashboard;
