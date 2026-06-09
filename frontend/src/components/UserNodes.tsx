import React, { useCallback, useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { fetchSavedNodes } from '../services/fetchService';
import { useAuth } from '../contexts/AuthContext';
import NodeCard from '../components/NodeCard';
import VirtualizedList from '../components/VirtualizedList';
import { ShimmerCard } from '../components/ShimmerSection';
import { Spinner } from './Icons';
import SortSearch from '../components/SortSearch';
import Error from '../components/Error';
import { ResearchNodeCard, ResearchNodeListResponse } from '../api/generated/api';

export interface UserNodesProps {
  private: boolean;
  userId?: number;
}

interface NoNodesProps {
  isOwnProfile: boolean | null | undefined;
  isSaved: boolean;
}

const NoNodes: React.FC<NoNodesProps> = ({ isOwnProfile, isSaved }) => {
  return (
    <div className="py-12 bg-gradient-to-r from-zinc-800 via-green-900 to-zinc-800 flex items-center rounded-md justify-center mx-4 sm:mx-6 lg:mx-8">
      <div className="max-w-lg w-full space-y-8 bg-zinc-100 p-10 rounded-xl shadow-2xl">
        <div>
          <p className="mt-2 text-center text-3xl font-bold text-gray-900">
            No nodes found
          </p>
          <p className="mt-2 text-center text-sm text-gray-600">
            {isOwnProfile 
              ? `You haven't ${isSaved ? 'saved' : 'deployed'} any nodes yet matching this query.`
              : "This maintainer hasn't deployed any public nodes yet matching this query."}
          </p>
        </div>
      </div>
    </div>
  );
};

const UserNodes: React.FC<UserNodesProps> = ({ private: isSaved, userId }) => {
  const { user, loading: authLoading } = useAuth();
  const [sortBy, setSortBy] = useState('created_desc');
  const [searchTerm, setSearchTerm] = useState('');
  const [resetKey, setResetKey] = useState(0);

  const isOwnProfile = user && (user.id === userId || isSaved);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isError,
    error
  } = useInfiniteQuery({
    queryKey: ['userNodes', userId, isSaved, sortBy, searchTerm],
    queryFn: ({ pageParam = 1 }) => fetchSavedNodes(isSaved ? user?.id : userId, isSaved, pageParam as number, sortBy, searchTerm),
    initialPageParam: 1,
    getNextPageParam: (lastPage: ResearchNodeListResponse, allPages) => {
      const nextPage = allPages.length + 1;
      return nextPage <= (lastPage.total_pages || 1) ? nextPage : undefined;
    },
    getPreviousPageParam: (firstPage: ResearchNodeListResponse, allPages) => {
      const prevPage = allPages.length - 1;
      return prevPage >= 1 ? prevPage : undefined;
    },
    staleTime: 60 * 1000 * 2,
    gcTime: 60 * 1000 * 60 * 2,
  });

  const nodes = data?.pages.flatMap(page => page.nodes) || [];

  const handleSortChange = useCallback((value: string) => {
    setSortBy(value);
    setResetKey(prevKey => prevKey + 1);
  }, []);

  const handleSearchChange = useCallback((value: string) => {
    setSearchTerm(value);
    setResetKey(prevKey => prevKey + 1);
  }, []);

  const renderItem = useCallback((node: ResearchNodeCard | null, index: number) => {
    return node ? (
      <div style={{ flex: 1, margin: '0 8px' }}>
        <NodeCard key={node.id} node={node} />
      </div>
    ) : (
      <div style={{ flex: 1, margin: '0 8px' }}>
        <ShimmerCard key={`shimmer-${index}`} />
      </div>
    );
  }, []);

  const loadMore = useCallback(() => {
    if (hasNextPage && !isLoading) {
      fetchNextPage();
    }
  }, [hasNextPage, isLoading, fetchNextPage]);

  return (
    <div className="max-w-6xl px-4 py-8 flex flex-col justify-center space-y-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-300">
          {isOwnProfile 
            ? `Your ${isSaved ? 'Saved' : 'Public'} Nodes`
            : `Maintainer's Public Nodes`}
        </h2>
      </div>
      <SortSearch onSortChange={handleSortChange} onSearchChange={handleSearchChange} noAdded={true}/>
      {!isLoading && !authLoading && nodes.length === 0 && 
        <NoNodes isOwnProfile={isOwnProfile} isSaved={isSaved} />
      }
      {(isLoading || authLoading) && <Spinner />}
      {isError && <Error message={error.message} />}
      <VirtualizedList
        items={nodes}
        renderItem={renderItem}
        itemHeight={356}
        loadMore={loadMore}
        hasMore={hasNextPage}
        rowReset={resetKey}
      />
    </div>
  );
};

export default UserNodes;
