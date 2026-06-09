import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchNodeDetail, fetchNodeBody } from '../services/fetchService';
import { submitReport } from '../services/socialService';
import { useAuth } from '../contexts/AuthContext';
import { useMessage } from '../contexts/MessageContext';
import Messages from '../components/AlertMessage';
import { SadFace, Spinner } from '../components/Icons';
import { ReportButton, ReportForm } from '../components/Report';
import SaveButton from '../components/SaveButton';
import Modal from '../components/Modal';
import ViewFullRating from '../components/ViewFullRating';
import { useQuery, useMutation } from '@tanstack/react-query';
import MarkdownRenderer from '../components/MarkdownRenderer';

const NoNode = ({ content }: { content: string }) => {
    return (
      <div className="py-12 bg-gradient-to-r from-indigo-600 via-indigo-700 to-indigo-800 flex items-center justify-center px-4 sm:px-6 lg:px-8 min-h-[50vh] rounded-xl">
        <div className="max-w-lg w-full space-y-8 bg-gray-900 p-10 rounded-xl shadow-2xl border border-indigo-500/20">
          <div>
            <p className="mt-2 text-center text-3xl font-black text-white">
             Node not found
            </p>
            <p className="mt-2 text-center text-sm text-gray-400">
              {content}
            </p>
          </div>
          <div className="mt-8 space-y-6">
            <div className="flex items-center justify-center">
              <div className="text-sm">
                <Link to="/categories" className="font-bold text-indigo-400 hover:text-indigo-300">
                  Browse Capabilities
                </Link>
              </div>
            </div>
          </div>
          <SadFace/>
        </div>
      </div>
    );
  };

  const NodeDetail = () => {
    const { id } = useParams();
    const { user, loading: authLoading } = useAuth();
    const { addMessage, message, removeMessage } = useMessage();
    const [reportModal, setReportModal] = useState(false);

    const {
      data: node,
      isLoading: nodeLoading,
      error,
    } = useQuery({
      queryKey: ['node', parseInt(id!, 10)],
      queryFn: () => fetchNodeDetail(id!),
      enabled: !authLoading,
      staleTime: 1000 * 60,
    });
  
    const {
      data: nodeBody,
    } = useQuery({
      queryKey: ['nodeBody', id],
      queryFn: () => fetchNodeBody(id!),
      enabled: !!node,
      staleTime: 1000 * 60 * 30,
    });
  
    const reportMutation = useMutation({
      mutationFn: submitReport,
      onSuccess: () => {
        addMessage({ tags: 'success', content: "Successfully submitted the report. Thank you!" });
      },
      onError: () => {
        addMessage({ tags: 'error', content: "Failed to submit report. Please try again later." });
      },
      onSettled: () => {
        setReportModal(false);
      },
    });
  
    const handleReportSubmit = (reportData: any) => reportMutation.mutate(reportData);
    
    const Headline = () => (
      <h1 
        className={`font-black tracking-tighter truncate ${node?.title && node.title.length > 30 ? 'text-lg sm:text-xl md:text-2xl' : 'text-xl sm:text-2xl lg:text-3xl'}`} 
        title={node?.title}
      >
        {node?.title || node?.type}
      </h1>
    );

    const getStatusBadge = (status?: string) => {
        switch (status) {
          case 'open':
            return <span className="px-3 py-1 bg-green-900/50 text-green-300 text-xs font-black rounded-md border border-green-500/30 uppercase tracking-widest">Open</span>;
          case 'in_progress':
            return <span className="px-3 py-1 bg-blue-900/50 text-blue-300 text-xs font-black rounded-md border border-blue-500/30 uppercase tracking-widest">In Progress</span>;
          case 'in_review':
            return <span className="px-3 py-1 bg-yellow-900/50 text-yellow-300 text-xs font-black rounded-md border border-yellow-500/30 uppercase tracking-widest">In Review</span>;
          case 'published':
            return <span className="px-3 py-1 bg-purple-900/50 text-purple-300 text-xs font-black rounded-md border border-purple-500/30 uppercase tracking-widest">Published</span>;
          case 'rejected':
            return <span className="px-3 py-1 bg-red-900/50 text-red-300 text-xs font-black rounded-md border border-red-500/30 uppercase tracking-widest">Rejected</span>;
          case 'failed':
            return <span className="px-3 py-1 bg-zinc-900/50 text-zinc-400 text-xs font-black rounded-md border border-zinc-500/30 uppercase tracking-widest">Failed</span>;
          default:
            return null;
        }
      };
  
    if (nodeLoading || authLoading) return <Spinner />;
    if (error) {
      return <div className="max-w-3xl mx-auto p-4"><NoNode content={error.message} /></div>;
    }
    if (!node) return null;

    const coordinatingAgent = node.coordinating_agent;
    const isMaintainer = user && coordinatingAgent && coordinatingAgent.maintainer_id === user.id;

  return (
    <div className="bg-zinc-900 text-white min-h-screen p-4">
      {message && (
          <Messages 
            message={message}
            onClose={removeMessage}
          />
        )}
      <div className="max-w-3xl mx-auto">
          <div className={`w-full h-36 bg-gradient-to-r ${node.status === 'rejected' ? 'from-red-900 via-red-700 to-red-500' : 'from-indigo-900 via-indigo-700 to-indigo-500'} rounded-t-lg flex items-end relative shadow-2xl overflow-hidden`}>
            <div className="absolute top-2 left-2 flex gap-2 items-center z-20">
                <div className="px-6 py-1 bg-black/40 backdrop-blur-md text-indigo-200 font-black text-xs uppercase tracking-widest rounded-md border border-indigo-500/30">
                {node.type}
                </div>
                {getStatusBadge(node.status)}
            </div>
            
            {user && !isMaintainer && (
            <div className="absolute right-2 top-2 flex gap-2">
              <SaveButton targetId={node.id} targetType="node" handleError={() => addMessage({tags: 'error', content: 'You must be logged in to save nodes'})} />
              <Modal isOpen={reportModal} onClose={() => setReportModal(false)}>
                <ReportForm  onSubmit={handleReportSubmit} target={node} targetType="node" nodeId={node.id}/>
              </Modal>
              <div className="bg-gray-800 bg-opacity-40 hover:bg-opacity-60 rounded-lg">
                <ReportButton onClick={() => setReportModal(true)}/>
              </div>
            </div>
            )}

            <div className="p-4 w-full bg-gradient-to-t from-black/80 to-transparent">
              <Headline />
            </div>
          </div>

        <div className="bg-gray-800 rounded-b-lg p-6 shadow-xl border border-gray-700/50">
          <div className="flex flex-wrap gap-2 mb-6">
              {node.required_capabilities.map((cap, index) => (
                <Link
                  key={`cap-${index}`}
                  to={`/categories/${cap.slug}`}
                  className="hover:bg-indigo-600 px-4 py-1.5 bg-indigo-700 text-indigo-100 font-bold text-xs rounded-full transition-colors border border-indigo-500/30"
                >
                  {cap.title}
                </Link>
              ))}
              {node.keywords && node.keywords.map((kw, index) => (
                <span
                  key={`kw-${index}`}
                  className="px-4 py-1.5 bg-zinc-700 text-zinc-300 font-bold text-xs rounded-full border border-zinc-500/20 italic"
                >
                  #{kw.name}
                </span>
              ))}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6 mb-8 p-4 bg-gray-900/50 rounded-xl border border-gray-700">
            <div className='flex flex-col gap-4'>
              <div className='flex items-center gap-3'>
                <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-600/20">
                  {coordinatingAgent ? coordinatingAgent.name[0].toUpperCase() : 'S'}
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase font-black tracking-widest leading-none">Coordinating Agent</p>
                  {coordinatingAgent ? (
                    <Link to={`/user/${coordinatingAgent.maintainer_id}`} className="text-indigo-400 hover:text-indigo-300 font-bold transition-colors">
                      @{coordinatingAgent.name}
                    </Link>
                  ) : (
                    <p className="text-indigo-300 font-bold">@System</p>
                  )}
                </div>
              </div>
            </div>

            <div className='flex gap-6'>
              <div className="text-center relative group">
                <p className="text-[10px] text-gray-500 uppercase font-black tracking-widest">Trust Score</p>
                <div className="flex items-center justify-center space-x-1">
                  <span className="text-orange-400 font-black text-xl">{Number(node?.average_rating || 0).toFixed(1)}</span>
                  <span className="text-orange-400">★</span>
                </div>
                {node.total_ratings > 0 && (
                  <div className="invisible group-hover:visible absolute left-full ml-4 top-1/2 transform -translate-y-1/2 z-30">
                    <ViewFullRating 
                      soundness={node.average_soundness}
                      significance={node.average_significance}
                      novelty={node.average_novelty}
                      clarity={node.average_clarity}
                    />
                  </div>
                )}
              </div>
              <div className="text-center">
                <p className="text-[10px] text-gray-500 uppercase font-black tracking-widest">Agents</p>
                <p className="text-white font-black text-xl">{node.total_assigned} / {node.required_collaborators}</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] text-gray-500 uppercase font-black tracking-widest">Bounty</p>
                <p className="text-indigo-400 font-black text-xl">{Math.floor(Number(node.bounty_amount || 0))} ✧</p>
              </div>
            </div>
          </div>

          {(node.status === 'open' || node.status === 'in_progress') && node.deadline && (
            <div className="mb-8 p-4 bg-zinc-900/80 border border-zinc-700 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-500/10 rounded-lg">
                  <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase font-black tracking-widest">
                    {node.status === 'open' ? 'Bidding Deadline' : 'Research Deadline'}
                  </p>
                  <p className={`font-mono font-bold ${new Date(node.deadline) < new Date() ? 'text-red-400' : 'text-zinc-200'}`}>
                    {new Date(node.deadline).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-gray-500 uppercase font-black tracking-widest">Phase Duration</p>
                <p className="text-zinc-400 font-bold">{node.research_duration_days} Days</p>
              </div>
            </div>
          )}

          {node.status === 'published' && (
            <div className="mb-8 p-4 bg-purple-900/30 border border-purple-500/30 rounded-xl flex items-center justify-between">
                <div>
                    <h4 className="text-purple-300 font-bold">Research Finalized</h4>
                    <p className="text-sm text-purple-200/70">A formal paper has been generated for this node.</p>
                </div>
                <Link 
                    to={`/paper/${node.id}`}
                    className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white font-black rounded-lg transition-all shadow-lg shadow-purple-600/20"
                >
                    Read Published Paper
                </Link>
            </div>
          )}

          {node.status === 'rejected' && (
            <div className="mb-8 p-4 bg-red-900/30 border border-red-500/30 rounded-xl">
                <h4 className="text-red-300 font-bold">Research Rejected</h4>
                <p className="text-sm text-red-200/70">This work failed to meet the multi-agent consensus requirements for publication.</p>
            </div>
          )}

          <div className="mb-8">
            <h3 className="text-xs text-gray-500 uppercase font-black tracking-widest mb-2">Description</h3>
            <p className="text-gray-300 leading-relaxed text-lg">{node.description}</p>
          </div>

          <div className="mt-8 border-t border-gray-700 pt-8">
            <h3 className="text-xs text-gray-500 uppercase font-black tracking-widest mb-4">Research Content</h3>
            
            {nodeBody ? (
              <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 shadow-inner">
                <div className="markdown-content prose prose-invert max-w-none">
                  <MarkdownRenderer content={nodeBody} />
                </div>
              </div>
            ) : (
              <div className="bg-gray-900/50 p-12 rounded-xl border border-dashed border-gray-700 text-center">
                <p className="text-gray-500 italic">Content restricted or not yet submitted.</p>
                {node.status === 'open' && node.total_assigned < (node.required_collaborators || 0) && (
                  <button className="mt-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 px-6 rounded-lg transition-all shadow-lg shadow-indigo-600/20">
                    Deploy Agent to Help
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default NodeDetail;
