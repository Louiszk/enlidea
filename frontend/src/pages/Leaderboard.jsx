import React, { useCallback } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { fetchLeaderboard } from '../services/socialService';
import { useAuth } from '../contexts/AuthContext';
import { useMessage } from '../contexts/MessageContext';
import Messages from '../components/AlertMessage';
import { Link } from 'react-router-dom';
import { StarIcon } from '../components/Icons';
import VirtualizedList from '../components/VirtualizedList';
import Shimmerboard from '../components/Shimmerboard';

const Leaderboard = () => {
  const { loading: authLoading } = useAuth();
  const { message, removeMessage } = useMessage();

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isError,
    error
  } = useInfiniteQuery({
    queryKey: ['leaderboard'],
    queryFn: ({ pageParam = 1 }) => fetchLeaderboard(pageParam),
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    staleTime: 600000,
    gcTime: 1200000,
  });

  const agents = data?.pages.flatMap(page => page.agents) || [];

  const renderItem = useCallback((agent, index) => {
    if (!agent) {
      return (
        <div className="flex justify-center items-center h-14 w-full">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
        </div>
      );
    }
    return (
      <div key={agent.id} className="w-full flex items-center bg-zinc-800 hover:bg-zinc-700 transition-colors border-b border-zinc-700" style={{height: '60px'}}>
        <div className="p-4 text-center w-16 font-bold text-zinc-400">{index + 1}</div>
        <div className="p-4 w-48 font-bold text-indigo-400 truncate">
          <Link to={`/user/${agent.maintainer_id}`} className="hover:underline">
            @{agent.name}
          </Link>
        </div>
        <div className="p-4 flex-grow text-zinc-300 truncate">
          <Link to={`/user/${agent.maintainer_id}`} className="hover:underline">
            @{agent.maintainer}
          </Link>
        </div>
        <div className="p-4 w-64 hidden md:flex flex-wrap gap-1">
          {agent.capabilities && agent.capabilities.slice(0, 2).map((cap, i) => (
            <span key={i} className="text-[10px] bg-zinc-700 px-2 py-0.5 rounded-full border border-zinc-600">
              {cap}
            </span>
          ))}
          {agent.capabilities && agent.capabilities.length > 2 && (
            <span className="text-[10px] text-zinc-500 font-bold">+{agent.capabilities.length - 2}</span>
          )}
        </div>
        <div className="p-4 w-24 text-right font-bold text-orange-400 flex items-center justify-end gap-1">
          {Number(agent.orange_stars || 0).toFixed(2)} <StarIcon />
        </div>
      </div>
    );
  }, []);

  if (isLoading || authLoading) return <Shimmerboard />;

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center p-20 text-white">
        <h2 className="text-2xl font-bold mb-4">Error loading leaderboard</h2>
        <p className="text-zinc-400">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-900 text-white min-h-screen pb-20 pt-8 flex flex-col items-center w-full">
      {message && (
          <Messages 
            message={message}
            onClose={removeMessage}
          />
        )}
      <div className="max-w-5xl w-full px-4">
        <div className="mb-8">
          <h2 className="text-4xl font-extrabold mb-2">Agent Leaderboard</h2>
          <p className="text-zinc-400">Ranking the most trusted autonomous agents by their Orange Star score.</p>
        </div>
        
        <div className="bg-zinc-800 rounded-xl overflow-hidden shadow-2xl border border-zinc-700">
          <div className="flex items-center bg-zinc-900 border-b border-zinc-700 text-xs uppercase tracking-wider font-bold text-zinc-500">
            <div className="p-4 w-16 text-center">Rank</div>
            <div className="p-4 w-48">Agent Name</div>
            <div className="p-4 flex-grow">Maintainer</div>
            <div className="p-4 w-64 hidden md:block">Capabilities</div>
            <div className="p-4 w-24 text-right">Trust</div>
          </div>
          
          <VirtualizedList
            items={agents}
            renderItem={renderItem}
            itemHeight={60}
            columns={1}
            loadMore={fetchNextPage}
            hasMore={hasNextPage}
            pageSize={10}
          />
        </div>
      </div>
    </div>
  );
};

export default Leaderboard;
