import React, { useCallback } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { fetchPapers } from '../services/fetchService';
import { useAuth } from '../contexts/AuthContext';
import PaperCard from '../components/PaperCard';
import VirtualizedList from '../components/VirtualizedList';
import { ShimmerCard } from '../components/ShimmerSection';
import { Spinner } from './Icons';
import Error from '../components/Error';

const NoPapers = () => {
  return (
    <div className="py-12 bg-gradient-to-r from-zinc-800 via-purple-900 to-zinc-800 flex items-center rounded-md justify-center mx-4 sm:mx-6 lg:mx-8">
      <div className="max-w-lg w-full space-y-8 bg-zinc-100 p-10 rounded-xl shadow-2xl border border-purple-500/20">
        <div>
          <p className="mt-2 text-center text-3xl font-bold text-gray-900">
            No papers found
          </p>
          <p className="mt-2 text-center text-sm text-gray-600">
            You haven't saved any research papers to your library yet.
          </p>
        </div>
      </div>
    </div>
  );
};

const UserPapers = () => {
  const { loading: authLoading } = useAuth();

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isError,
    error
  } = useInfiniteQuery({
    queryKey: ['userSavedPapers'],
    queryFn: ({ pageParam = 1 }) => fetchPapers(pageParam, null, true),
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    getPreviousPageParam: (firstPage) => firstPage.previousPage ?? undefined,
    staleTime: 60 * 1000 * 2,
    gcTime: 60 * 1000 * 60 * 2,
  });

  const papers = data?.pages.flatMap(page => page.results || page.papers || []) || [];

  const renderItem = useCallback((paper, index) => {
    return paper ? (
      <div style={{ flex: 1, margin: '0 8px' }}>
        <PaperCard key={paper.id} paper={paper} />
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
          Your Saved Papers
        </h2>
      </div>
      
      {!isLoading && !authLoading && papers.length === 0 && 
        <NoPapers />
      }
      {(isLoading || authLoading) && <Spinner />}
      {isError && <Error message={error.message} />}
      <VirtualizedList
        items={papers}
        renderItem={renderItem}
        itemHeight={300} 
        loadMore={loadMore}
        hasMore={hasNextPage}
      />
    </div>
  );
};

export default UserPapers;
