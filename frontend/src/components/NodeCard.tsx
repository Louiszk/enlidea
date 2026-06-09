import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ShimmerCard } from './ShimmerSection';
import { ResearchNodeCard, ResearchNodeStatusEnum } from '../api/generated/api';

export interface NodeCardProps {
  node: ResearchNodeCard;
}

const NodeCard: React.FC<NodeCardProps> = React.memo(({ node }) => {
  const { loading } = useAuth();

  if (loading) {
    return <ShimmerCard />;
  }

  const coordinatingAgent = node.coordinating_agent;
  const capabilities = node.required_capabilities || [];
  const keywords = node.keywords || [];
  const minTrust = Number(node.min_trust_required || 0);

  const getStatusBadge = (status?: ResearchNodeStatusEnum) => {
    switch (status) {
      case 'open':
        return <span className="px-2 py-0.5 bg-green-900/50 text-green-300 text-[10px] font-bold rounded border border-green-500/30 uppercase">Open</span>;
      case 'in_progress':
        return <span className="px-2 py-0.5 bg-blue-900/50 text-blue-300 text-[10px] font-bold rounded border border-blue-500/30 uppercase">In Progress</span>;
      case 'in_review':
        return <span className="px-2 py-0.5 bg-yellow-900/50 text-yellow-300 text-[10px] font-bold rounded border border-yellow-500/30 uppercase">In Review</span>;
      case 'published':
        return <span className="px-2 py-0.5 bg-purple-900/50 text-purple-300 text-[10px] font-bold rounded border border-purple-500/30 uppercase">Published</span>;
      case 'rejected':
        return <span className="px-2 py-0.5 bg-red-900/50 text-red-300 text-[10px] font-bold rounded border border-red-500/30 uppercase">Rejected</span>;
      case 'failed':
        return <span className="px-2 py-0.5 bg-zinc-900/50 text-zinc-400 text-[10px] font-bold rounded border border-zinc-500/30 uppercase">Failed</span>;
      default:
        return null;
    }
  };

  const isWarningStatus = node.status && (node.status === 'rejected' || node.status === 'failed');

  return (
    <Link
      key={node.id}
      to={`/node/${node.id}`}
      className={`block w-full max-w-md mx-auto select-none flex flex-col bg-gray-800 rounded-xl border ${isWarningStatus ? 'border-red-500/50' : 'border-indigo-500/50'} shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1`}
    >
      <div className="p-4 w-full relative">
        <div className="absolute left-2 top-2">
            {getStatusBadge(node.status)}
        </div>
        <div className='flex justify-center'>
          <span className="px-6 py-1 my-2 bg-indigo-900/50 text-indigo-200 text-sm font-bold rounded-md border border-indigo-500/30">
             {node.type}
          </span>
        </div>
        <div className="flex items-center mb-4 py-2 h-16 overflow-hidden">
          <h3 className={`font-bold text-white two-line-truncate ${node.title.length > 20 ? "text-xl" : "text-2xl"}`}>
            {node.title}
          </h3>
        </div>
        <p className="text-gray-300 mb-4 line-clamp-2">{node.description}</p>
        
        {(capabilities.length > 0 || keywords.length > 0) && (
          <div className="flex flex-wrap gap-2 mb-4">
            {capabilities.map((cap, index) => (
              <span
                key={`cap-${index}`}
                className="px-3 py-1 bg-gray-700 text-indigo-300 text-xs font-medium rounded-full border border-indigo-500/20"
              >
                {cap}
              </span>
            ))}
            {keywords.map((kw, index) => (
              <span
                key={`kw-${index}`}
                className="px-3 py-1 bg-zinc-700 text-zinc-300 text-xs font-medium rounded-full border border-zinc-500/20 italic"
              >
                #{kw.name}
              </span>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-4 w-full mt-4">
          <div className="flex text-sm text-gray-400 items-center">
            <span>Coordinated by</span>
            <span className="font-semibold ml-1 text-indigo-400">
              {coordinatingAgent ? `@${coordinatingAgent.name}` : 'System'}
            </span>
          </div>
          <div className='flex justify-between items-center p-2 bg-black/20 rounded-lg'>
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 uppercase font-bold tracking-tighter">Bounty</span>
              <span className="text-indigo-400 font-black text-lg leading-tight">{Math.floor(Number(node.bounty_amount || 0))} {'\u2727'}</span>
            </div>

            <div className="flex items-center space-x-4">
              {minTrust > 0 && (
                <div className="flex flex-col items-center">
                   <span className="text-[10px] text-gray-500 uppercase font-bold">Req. Trust</span>
                   <div className="flex items-center space-x-1">
                    <span className="text-orange-400 font-bold">{Number(minTrust).toFixed(1)}</span>
                    <span className="text-orange-400 text-xs">★</span>
                   </div>
                </div>
              )}
              <div className="flex flex-col items-center">
                <span className="text-[10px] text-gray-500 uppercase font-bold">Agents</span>
                <span className="text-gray-300 font-bold">{node.total_assigned || 0} / {node.required_collaborators || 1}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
});

export default NodeCard;
