import React, { useCallback } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useLocation, Link } from 'react-router-dom';
import { fetchSearchResults } from '../services/fetchService';
import { UserIcon, NodeIcon, CapabilityIcon, SearchIcon, Spinner, SadFace, RatedIcon } from '../components/Icons';
import VirtualizedList from '../components/VirtualizedList';
import NodeCard from '../components/NodeCard';
import PaperCard from '../components/PaperCard';
import { ShimmerCard } from '../components/ShimmerSection';
import Error from '../components/Error';

import {
  Account,
  Capability,
  ResearchNodeCard,
  Paper,
  SearchResultItem,
} from '../api/generated/api';

interface NoResultsProps {
  query: string | null;
}

const NoResults: React.FC<NoResultsProps> = ({ query }) => {
    return (
      <div className="py-12 bg-slate-900 flex items-center justify-center px-4 sm:px-6 lg:px-8">
        <div className="max-w-lg w-full space-y-8 bg-slate-800 p-10 rounded-xl shadow-2xl border border-slate-700">
          <div>
            <p className="mt-2 text-center text-3xl font-bold text-slate-100">
              Nothing matched your search: "{query}"
            </p>
            <p className="mt-2 text-center font-semibold text-sm text-slate-400">
            Try adjusting your query
            </p>
          </div>
          <div className="mt-4 space-y-6">
            <div className="flex items-center justify-center text-slate-600">
              <SadFace />
            </div>
          </div>
        </div>
      </div>
    );
  };

const SearchResults = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const query = searchParams.get('q');

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isError
  } = useInfiniteQuery({
    queryKey: ['searchResults', query],
    queryFn: ({ pageParam = 1 }) => fetchSearchResults(query, pageParam as number),
    initialPageParam: 1,
    getNextPageParam: (lastPage: SearchResultItem[], allPages) => {
      const nodesResult = lastPage.find(result => result.type === 'nodes');
      return nodesResult && nodesResult.hasNext ? allPages.length + 1 : undefined;
    },
    enabled: !!query && query.length >= 3,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 60
  });

  const allResults = data ? data.pages.flatMap(page => page) : [];
  const users = (allResults.find(result => result.type === 'users')?.results || []) as Account[];
  const capabilities = (allResults.find(result => result.type === 'capabilities')?.results || []) as Capability[];
  const nodes = (allResults.flatMap(result => (result.type === 'nodes') ? result.results : []) || []) as ResearchNodeCard[];
  const papers = (allResults.find(result => result.type === 'papers')?.results || []) as Paper[];

  const getIcon = (type: string) => {
    switch (type) {
      case 'user':
        return <UserIcon />;
      case 'node':
        return <NodeIcon />;
      case 'paper':
        return <RatedIcon />;
      default:
        return <CapabilityIcon />;
    }
  };

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

  const renderCard = useCallback((item: Account | Capability, index: number) => {
    const slug = 'slug' in item ? item.slug : undefined;
    const id = 'id' in item ? item.id : undefined;
    const username = 'username' in item ? item.username : undefined;
    const title = 'title' in item ? item.title : undefined;

    return (
    <Link to={slug ? `/capabilities/${slug}` : `/user/${id}`} key={id || index} className="bg-slate-800 hover:bg-slate-700 transition-colors border border-slate-700 p-4 rounded-xl shadow flex items-center gap-3 group">
        <div className="text-indigo-400 group-hover:scale-110 transition-transform">
          {getIcon(slug ? 'capability' : 'user')}
        </div>
        <span className="font-bold text-slate-200 truncate">{title || username}</span>
    </Link>
    );
  }, []);

  const loadMore = useCallback(() => {
    if (hasNextPage && !isLoading) {
      fetchNextPage();
    }
  }, [hasNextPage, isLoading, fetchNextPage]);

  if (isLoading) return (
    <div className="flex justify-center items-center h-screen bg-slate-950">
      <Spinner />
    </div>
  );
  if (isError) return <Error message="Error fetching search results" />;

  
  if (!query || query.length < 3) {
      return (
          <div className="flex flex-col items-center justify-center h-screen bg-slate-950 text-slate-300 p-4">
        <div className="bg-slate-900 p-12 rounded-2xl border border-slate-800 shadow-2xl flex flex-col items-center max-w-lg">
          <SearchIcon className="w-20 h-20 text-indigo-500 mb-6 animate-pulse" />
          <h2 className="text-3xl font-extrabold mb-4 text-white">Start Searching</h2>
          <p className="text-center text-slate-400 leading-relaxed">
            Enter at least 3 characters to search across the Enlidea network. You can discover <span className="text-indigo-400 font-bold">Maintainers</span>, explorer <span className="text-green-400 font-bold">Capabilities</span>, track <span className="text-yellow-400 font-bold">Research Nodes</span>, and read published <span className="text-purple-400 font-bold">Papers</span>.
          </p>
        </div>
      </div>
    );
  }

  if (users.length === 0 && capabilities.length === 0 && nodes.length === 0 && papers.length === 0) {
    return <NoResults query={query} />;
  }

  return (
    <div className="p-4 pt-12 max-w-6xl mx-auto text-slate-300 min-h-screen">
      <div className="mb-12">
        <h1 className="text-4xl font-black text-white mb-2 tracking-tight">Search Results</h1>
        <p className="text-slate-500 font-bold uppercase tracking-widest text-sm">Query: "{query}"</p>
      </div>
      
      {capabilities.length > 0 && (
        <div className="mb-12">
          <h2 className="text-2xl font-black text-white mb-6 flex items-center gap-2">
            <CapabilityIcon className="text-green-400" /> Capabilities
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {capabilities.map((capability, index) => renderCard(capability, index))}
          </div>
        </div>
      )}

      {users.length > 0 && (
        <div className="mb-12">
          <h2 className="text-2xl font-black text-white mb-6 flex items-center gap-2">
            <UserIcon className="text-indigo-400" /> Maintainers
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {users.map((user, index) => renderCard(user, index))}
          </div>
        </div>
      )}

      {papers.length > 0 && (
        <div className="mb-12">
          <h2 className="text-2xl font-black text-white mb-6 flex items-center gap-2">
            <RatedIcon className="text-purple-400" /> Published Papers
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        </div>
      )}

      {nodes.length > 0 && (
      <div className="mb-12">
        <h2 className="text-2xl font-black text-white mb-6 flex items-center gap-2">
          <NodeIcon className="text-yellow-400" /> Work in Progress
        </h2>
        <VirtualizedList
          items={nodes}
          renderItem={renderItem}
          itemHeight={356}
          loadMore={loadMore}
          hasMore={hasNextPage}
        />
      </div>
      )}
    </div>
  );
};

export default SearchResults;
