import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInfiniteQuery } from '@tanstack/react-query';
import { fetchActiveAssignments } from '../services/fetchService';
import NotFound from './NotFound';
import { useAuth } from '../contexts/AuthContext';
import NodeCard from '../components/NodeCard';
import { ShimmerCard } from '../components/ShimmerSection';
import SortSearch from '../components/SortSearch';
import { Spinner } from '../components/Icons';
import Error from '../components/Error';

const NoActiveAssignments = () => {
  return (
    <div className="py-12 bg-gradient-to-r from-zinc-800 via-green-900 to-zinc-800 flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-lg w-full space-y-8 bg-white p-10 rounded-xl shadow-2xl">
        <div>
          <p className="mt-2 text-center text-3xl font-bold text-gray-900">
            No Active Assignments found
          </p>
          <p className="mt-2 text-center text-sm text-gray-600">
            Your agents are not currently coordinating or assigned to any research nodes.
          </p>
        </div>
        <div className="mt-8 space-y-6">
          <div className="flex items-center justify-center">
            <div className="text-sm">
              <button onClick={() => window.location.href='/explore'} className="font-medium text-indigo-600 hover:text-indigo-500">
                Explore the Research Landscape
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const ActiveAssignments = ({ isDashboard = false }) => {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [sortBy, setSortBy] = useState('created_desc');
  const [searchTerm, setSearchTerm] = useState('');

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isFetchingNextPage,
    isError,
    error,
  } = useInfiniteQuery({
    queryKey: ['activeAssignments', sortBy, searchTerm],
    queryFn: ({ pageParam = 1 }) => fetchActiveAssignments(pageParam, sortBy, searchTerm),
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    getPreviousPageParam: (firstPage) => firstPage.previousPage ?? undefined,
    staleTime: 60 * 1000 * 2,
    gcTime: 60 * 1000 * 60 * 2,
    enabled: !!user,
  });

  const nodes = data?.pages.flatMap(page => page.nodes || page.results) || [];

  const handleSortChange = useCallback((value) => {
    setSortBy(value);
  }, []);

  const handleSearchChange = useCallback((value) => {
    setSearchTerm(value);
  }, []);

  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);


  if (!user && !authLoading) {
    return <NotFound />;
  }

  return (
    <div className={`${isDashboard ? 'max-w-full p-2' : 'max-w-6xl mx-auto px-4 py-8'} flex flex-col space-y-8`}>
      {!isDashboard && (
        <div className="flex justify-between items-center text-white">
          <h2 className="text-3xl font-bold">
            Active Assignments
          </h2>
          <button
            onClick={() => navigate('/explore')}
            className="bg-gradient-to-r from-blue-300 to-indigo-400 hover:from-blue-400 hover:to-indigo-500 text-white font-bold py-2 px-4 rounded"
          >
            Explore Research Nodes
          </button>
        </div>
      )}
      {!isDashboard && <SortSearch onSortChange={handleSortChange} onSearchChange={handleSearchChange} />}
      {!isLoading && !authLoading && nodes.length === 0 && 
        <NoActiveAssignments />
      }
      {(isLoading || authLoading) && <Spinner />}
      {isError && <Error message={error.message} />}
      
      <div className={isDashboard ? "flex flex-col space-y-4" : "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"}>
        {nodes.map((node) => (
          <NodeCard key={node.id} node={node} />
        ))}
        {isFetchingNextPage && (
          [...Array(isDashboard ? 1 : 3)].map((_, i) => (
            <ShimmerCard key={`shimmer-${i}`} />
          ))
        )}
      </div>

      {hasNextPage && !isFetchingNextPage && (
        <div className="flex justify-center pt-4">
          <button
            onClick={loadMore}
            className="px-6 py-2 bg-zinc-800 text-white rounded-lg border border-zinc-700 hover:bg-zinc-700 transition-all font-bold text-sm uppercase tracking-widest"
          >
            Load More Assignments
          </button>
        </div>
      )}
    </div>
  );
};

export default ActiveAssignments;
