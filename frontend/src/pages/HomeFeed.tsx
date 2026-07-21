import React, { useState, useCallback } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { getHomeFeed, getFollows } from '../services/socialService';

import NodeCard from '../components/NodeCard';
import PaperCard from '../components/PaperCard';
import { ShimmerCard } from '../components/ShimmerSection';
import { useAuth } from '../contexts/AuthContext';
import NotFound from './NotFound';
import { Link, useNavigate } from 'react-router-dom';
import VirtualizedList from '../components/VirtualizedList';
import { Spinner } from '../components/Icons';
import Error from '../components/Error';
import { getMediaUrl } from '../services/apiClient';
import { HomeFeedResponse, PaperListResponse, ResearchNodeCard, Paper } from '../api/generated/api';


const HomeFeed = () => {
  const [selectedUser, setSelectedUser] = useState(0);
  const [feedType, setFeedType] = useState('bounties');
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const {
    data: followsData = [],
    isLoading: isFollowsLoading,
    error: followsError
  } = useQuery({
    queryKey: ['follows'],
    queryFn: getFollows,
    staleTime: 1000 * 60 * 4, 
    gcTime: 1000 * 60 * 60 * 2,
    enabled: !!user
  });
  
  const {
    data: nodeData,
    fetchNextPage: fetchNextNodes,
    hasNextPage: hasNextNodes,
    isLoading: isNodesLoading,
    isError: isNodesError
  } = useInfiniteQuery({
    queryKey: ['homeFeed', selectedUser, 'bounties'],
    queryFn: ({ pageParam = 1 }) => getHomeFeed(String(selectedUser), pageParam as number, 'bounties'),
    initialPageParam: 1,
    getNextPageParam: (lastPage: HomeFeedResponse | PaperListResponse) => lastPage.nextPage ?? undefined,
    enabled: !!user && feedType === 'bounties'
  });

  const {
    data: paperData,
    fetchNextPage: fetchNextPapers,
    hasNextPage: hasNextPapers,
    isLoading: isPapersLoading,
    isError: isPapersError
  } = useInfiniteQuery({
    queryKey: ['homeFeed', selectedUser, 'papers'],
    queryFn: ({ pageParam = 1 }) => getHomeFeed(String(selectedUser), pageParam as number, 'papers'),
    initialPageParam: 1,
    getNextPageParam: (lastPage: HomeFeedResponse | PaperListResponse) => lastPage.nextPage ?? undefined,
    enabled: !!user && feedType === 'papers'
  });

  const handleUserClick = (userId: number) => {
    if (selectedUser === userId && userId !== 0 && userId !== -1) {
      navigate(`/user/${userId}`);
    } else {
      setSelectedUser(userId);
    }
  };

  const items = feedType === 'bounties' 
    ? (nodeData?.pages.flatMap(page => ('nodes' in page ? page.nodes : [])) || [])
    : (paperData?.pages.flatMap(page => ('papers' in page ? (page.papers || []) : [])) || []);

  const renderItem = useCallback((item: ResearchNodeCard | Paper | null, index: number) => {
    if (!item) {
        return (
            <div key={`shimmer-${index}`} style={{ flex: 1, margin: '0 8px' }}>
              <ShimmerCard />
            </div>
          );
    }

    return feedType === 'bounties' ? (
      <div key={`node-${item.id}`} style={{ flex: 1, margin: '0 8px' }}>
        <NodeCard node={item as ResearchNodeCard} />
      </div>
    ) : (
      <div key={`paper-${item.id}`} style={{ flex: 1, margin: '0 8px' }}>
        <PaperCard paper={item as Paper} />
      </div>
    );
  }, [feedType]);

  const loadMore = useCallback(() => {
    if (feedType === 'bounties' && hasNextNodes && !isNodesLoading) {
        fetchNextNodes();
    } else if (feedType === 'papers' && hasNextPapers && !isPapersLoading) {
        fetchNextPapers();
    }
  }, [feedType, hasNextNodes, isNodesLoading, fetchNextNodes, hasNextPapers, isPapersLoading, fetchNextPapers]);

  if (authLoading) {
    return <Spinner />;
  }

  if (!user) {
    return <NotFound />;
  }

  if (followsError) {
    return <Error message={followsError?.message} />;
  }

  return (
    <div className="container mx-auto px-4 lg:px-16 pt-8 min-h-screen">
      <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
            <h1 className="text-4xl text-white font-extrabold mb-2 tracking-tight">Research Feed</h1>
            <p className="text-zinc-400 text-lg">Real-time updates from the Enlidea network.</p>
        </div>

        <div className="bg-zinc-800 p-1 rounded-xl flex border border-zinc-700">
            <button 
                onClick={() => setFeedType('bounties')}
                className={`px-6 py-2 rounded-lg font-black text-sm transition-all ${feedType === 'bounties' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'text-zinc-400 hover:text-zinc-200'}`}
            >
                Active Bounties
            </button>
            <button 
                onClick={() => setFeedType('papers')}
                className={`px-6 py-2 rounded-lg font-black text-sm transition-all ${feedType === 'papers' ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20' : 'text-zinc-400 hover:text-zinc-200'}`}
            >
                Published Papers
            </button>
        </div>
      </div>
      
      {/* Scope and Follows filter row for both Bounties and Papers */}
      <div className="mb-8 overflow-x-auto whitespace-nowrap pb-4 flex items-center gap-4 no-scrollbar">
        <button 
          onClick={() => handleUserClick(-1)} 
          className={`flex-shrink-0 px-6 py-3 rounded-xl font-bold border-2 transition-all duration-200 ${selectedUser === -1 ? 'bg-indigo-600 border-indigo-400 text-white shadow-lg shadow-indigo-500/20' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'}`}
        >
          Global
        </button>
        <button 
          onClick={() => handleUserClick(0)} 
          className={`flex-shrink-0 px-6 py-3 rounded-xl font-bold border-2 transition-all duration-200 ${selectedUser === 0 ? 'bg-indigo-600 border-indigo-400 text-white shadow-lg shadow-indigo-500/20' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'}`}
        >
          Following
        </button>
        {followsData?.map(follow => (
          <button
            key={follow.id}
            onClick={() => handleUserClick(follow.id)}
            className={`flex-shrink-0 flex items-center gap-3 px-5 py-2.5 rounded-xl font-bold border-2 transition-all duration-200 ${selectedUser === follow.id ? 'bg-indigo-600 border-indigo-400 text-white shadow-lg shadow-indigo-500/20' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'}`}
          >
            <img 
              src={getMediaUrl(follow.avatar) || '/default-account.svg'} 
              alt={follow.username} 
              className="w-8 h-8 rounded-full border border-white/10"
            />
            <span>{follow.username}</span>
          </button>
        ))}
      </div>

      {(isNodesLoading || isPapersLoading || isFollowsLoading) ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => <ShimmerCard key={i} />)}
        </div>
      ) : (items.length === 0 || isNodesError || isPapersError) ? (
        <div className="flex flex-col items-center justify-center py-20 bg-zinc-800/50 rounded-2xl border border-dashed border-zinc-700">
          <p className='font-bold text-2xl text-zinc-300 mb-2'>
            {selectedUser === 0 && followsData.length === 0 
              ? "You aren't following anyone yet." 
              : selectedUser === -1
              ? "No global updates found."
              : "No updates found."}
          </p>
          <p className='text-zinc-500 mb-6 text-center max-w-md'>
            {selectedUser === 0 && followsData.length === 0 
              ? `You are viewing your Following feed, but don't follow any maintainers yet. Switch to Global or explore the network!`
              : selectedUser === -1
              ? `There are currently no ${feedType === 'bounties' ? 'active bounties' : 'published papers'} across the global Enlidea network right now.`
              : `No ${feedType === 'bounties' ? 'active bounties' : 'published papers'} found for this scope at the moment.`}
          </p>
          {selectedUser === 0 && followsData.length === 0 ? (
            <div className="flex gap-4">
              <button onClick={() => setSelectedUser(-1)} className='bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-lg font-bold transition-all'>
                Switch to Global
              </button>
              <Link to="/leaderboard" className='bg-zinc-700 hover:bg-zinc-600 text-white px-6 py-2.5 rounded-lg font-bold transition-all'>
                Explore Network
              </Link>
            </div>
          ) : (
            <Link to="/leaderboard" className='bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-lg font-bold transition-all'>
              Explore Network
            </Link>
          )}
        </div>
      ) : (
        <VirtualizedList
          items={items}
          renderItem={renderItem}
          itemHeight={feedType === 'bounties' ? 356 : 280}
          loadMore={loadMore}
          hasMore={feedType === 'bounties' ? hasNextNodes : hasNextPapers}
        />
      )}
    </div>
  );
};

export default HomeFeed;
