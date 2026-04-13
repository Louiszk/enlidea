import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchPendingReviews } from '../services/fetchService';
import { Spinner } from './Icons';
import { Link } from 'react-router-dom';

const ReviewOffers = () => {
  const { data: reviews = [], isLoading } = useQuery({
    queryKey: ['pending-reviews'],
    queryFn: fetchPendingReviews,
    refetchInterval: 10000,
  });

  // Filter for pending offers only for the broadcast view
  const pendingOffers = reviews.filter(r => r.status === 'pending');

  if (isLoading) return <div className="p-4 flex justify-center"><Spinner /></div>;
  if (pendingOffers.length === 0) return null;

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-lg overflow-hidden flex flex-col font-mono text-sm mb-4 shadow-xl">
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-2 flex items-center justify-between">
        <div className="text-zinc-300 font-bold tracking-wider flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
          REVIEW OFFERS
        </div>
        <div className="text-zinc-500 text-xs">
          {pendingOffers.length} PENDING
        </div>
      </div>
      
      <div className="p-2 max-h-48 overflow-y-auto space-y-2">
        {pendingOffers.map((review) => (
          <div key={review.id} className="bg-zinc-900/50 border border-zinc-800 p-3 rounded flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Link to={`/user/${review.assigned_reviewer_detail?.maintainer_id}`} className="text-indigo-400 hover:text-indigo-300 font-bold transition-colors">
                  @{review.assigned_reviewer_detail?.name}
                </Link>
                <span className="text-zinc-600 text-xs">Round {review.round_number}</span>
                {review.research_node_detail?.escalated_to_counsel && (
                   <span className="text-purple-400 text-[10px] border border-purple-900 px-1 rounded font-bold">HIGHER COUNSEL</span>
                )}
              </div>
              <div className="text-zinc-200 font-medium line-clamp-1">
                {review.research_node_detail?.title}
              </div>
              <div className="text-zinc-500 text-xs flex gap-3 mt-1">
                <span>Bounty: {Math.floor(review.research_node_detail?.bounty_amount || 0)} ✧</span>
                <span>Type: {review.research_node_detail?.type?.name || review.research_node_detail?.type}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReviewOffers;
