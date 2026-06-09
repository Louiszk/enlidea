import React, { useState } from 'react';
import UserNodes from '../components/UserNodes';
import UserPapers from '../components/UserPapers';
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';

const Library = () => {
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('nodes');

  if (loading) return null;
  if (!user) return <Navigate to="/login" />;

  return (
    <div className="min-h-screen bg-zinc-800 py-12">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-12">
          <h1 className="text-4xl font-black text-white mb-2">Your Library</h1>
          <p className="text-zinc-400">Manage your saved research nodes and published papers.</p>
        </div>

        <div className="flex space-x-1 bg-zinc-900/50 p-1 rounded-xl mb-8 max-w-md border border-zinc-700/50">
          <button
            onClick={() => setActiveTab('nodes')}
            className={`flex-1 py-3 px-4 rounded-lg font-bold text-sm transition-all duration-200 ${
              activeTab === 'nodes'
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            Saved Nodes
          </button>
          <button
            onClick={() => setActiveTab('papers')}
            className={`flex-1 py-3 px-4 rounded-lg font-bold text-sm transition-all duration-200 ${
              activeTab === 'papers'
                ? 'bg-purple-600 text-white shadow-lg'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            Saved Papers
          </button>
        </div>

        <div className="transition-all duration-300">
          {activeTab === 'nodes' ? (
            <UserNodes private={true} userId={user.id} />
          ) : (
            <UserPapers />
          )}
        </div>
      </div>
    </div>
  );
};

export default Library;
