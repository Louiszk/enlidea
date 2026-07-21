import React from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchCapabilityNodes } from '../services/fetchService';
import NotFound from './NotFound';
import { useMessage } from '../contexts/MessageContext';
import Messages from '../components/AlertMessage';
import NodeCard from '../components/NodeCard';
import Pagination from '../components/Pagination';
import SortFilter from '../components/SortFilter';
import { plural } from '../services/constants';
import { Spinner } from '../components/Icons';

const NoNodes = ( {path}: {path: {slug: string; title: string}[]} ) => {
    return (
      <div className="py-12 flex items-center justify-center px-4 sm:px-6 lg:px-8">
        <div className="max-w-lg w-full space-y-8 bg-gradient-to-r from-zinc-100 to-zinc-200 p-10 rounded-xl shadow-2xl">
        <div className='font-semibold text-zinc-800'>
            {path.map((cat: {slug: string; title: string}, index: number) => (
              <span key={cat.slug}>
                <Link className="hover:underline" to={`/categories/${cat.slug}`}>{cat.title}</Link>
                {index < path.length - 1 && " > "}
              </span>
            ))}
          </div>
          <div>
            <p className="mt-2 text-center text-3xl font-bold text-gray-900">
              No Nodes found
            </p>
            <p className="mt-2 text-center text-sm text-gray-600">
              For this capability and filter no public available nodes could be found.
            </p>
          </div>
          <div className="mt-8 space-y-6">
            <div className="flex items-center justify-center">
              <div className="text-sm">
                <Link to="/categories" className="font-medium text-indigo-600 hover:text-indigo-500">
                  Go back to capabilities
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };
  
  const CapabilityNodes = () => {
    const { slug } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const { message, removeMessage } = useMessage();
  
    // Parse query parameters
    const queryParams = new URLSearchParams(location.search);
    const page = parseInt(queryParams.get('page') || '1', 10);
    const sortBy = queryParams.get('sort') || 'trending';
    const filters = queryParams.get('filters') || '{}';
    const filterObj = JSON.parse(decodeURIComponent(filters));
  
    const { data, error, isLoading } = useQuery({
      queryKey: ['capabilityNodes', slug, page, sortBy, filters],
      queryFn: () => fetchCapabilityNodes(slug!, page, sortBy, filters),
      staleTime: 60 * 1000 * 2,
      gcTime: 60 * 1000 * 60 * 2,
    });
  
    const nodes = data?.nodes || [];
    const path = data?.category_path || [];
    const totalPages = data?.total_pages || 0;
  
    const handlePageChange = (pageNumber: number) => {
      if (slug) {
        navigate(`/categories/${slug}?sort=${sortBy}&filters=${filters}&page=${pageNumber}`);
      } else {
        navigate(`/explore?sort=${sortBy}&filters=${filters}&page=${pageNumber}`);
      }
    };
  
    const apiError = error as { detail?: string; message?: string; category_path?: {slug: string; title: string}[] } | null;
    if (apiError && apiError.detail && apiError.detail.includes('No Category matches')) {
      return <NotFound />;
    }
  
    return (
      <div className="max-w-6xl mx-auto px-2 sm:px-4 py-8">
        {message && <Messages message={message} onClose={removeMessage} />}
        <div className="flex flex-col gap-4 mb-6">
          <h2 className="text-3xl font-bold text-zinc-400">
            {slug && path.length > 0 ? (slug !== 'undefined' ? path[path.length - 1].title : "All capabilities") : (filterObj.types ? `Explore ${filterObj.tags} ${plural(filterObj.types)}` : "Explore All Nodes")}
          </h2>
          <div className='flex flex-row justify-between font-semibold text-zinc-300'>
            <div>
              {path.map((cat, index) => (
                <span key={cat.slug}>
                  <Link className="hover:underline" to={`/categories/${cat.slug}`}>{cat.title}</Link>
                  {index < path.length - 1 && " > "}
                </span>
              ))}
            </div>
          </div>
        </div>
        <SortFilter
          sortBy={sortBy}
          tags={filterObj.tags ? filterObj.tags.split(',') : (slug ? [slug] : [])}
          status={filterObj.status ? filterObj.status.split(',') : []}
          slug={slug}
        />
        {isLoading ? (
          <Spinner />
        ) : (nodes.length === 0 || (apiError && apiError.message && apiError.message.includes('No nodes found'))) ? (
          <NoNodes path={(apiError && apiError.category_path) || path || []} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {nodes.map(node => (
              <NodeCard key={node.id} node={node} />
            ))}
          </div>
        )}
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          loading={isLoading}
        />
      </div>
    );
  };
  
  export default CapabilityNodes;
