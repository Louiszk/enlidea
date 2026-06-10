import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchPaperDetail } from '../services/fetchService';
import { appreciatePaper } from '../services/socialService';
import { useAuth } from '../contexts/AuthContext';
import { useMessage } from '../contexts/MessageContext';
import { Spinner } from '../components/Icons';
import SaveButton from '../components/SaveButton';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { Paper, AppreciatePaperResponse } from '../api/generated/api';

const PaperDetail = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const { addMessage } = useMessage();
  const queryClient = useQueryClient();

  const {
    data: paper,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['paper', id],
    queryFn: () => fetchPaperDetail(id!),
    staleTime: 1000 * 60 * 60,
  });

  const appreciateMutation = useMutation<AppreciatePaperResponse, Error, { vote: number }, { previousPaper?: Paper }>({
    mutationFn: ({ vote }) => appreciatePaper(id!, vote),
    onMutate: async ({ vote }) => {
      await queryClient.cancelQueries({ queryKey: ['paper', id] });
      const previousPaper = queryClient.getQueryData<Paper>(['paper', id]);
      
      if (previousPaper) {
        // Optimistic update
        queryClient.setQueryData<Paper>(['paper', id], {
          ...previousPaper,
          user_vote: vote
        });
      }
      
      return { previousPaper };
    },
    onError: (err, variables, context) => {
      if (context?.previousPaper) {
        queryClient.setQueryData(['paper', id], context.previousPaper);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['paper', id] });
    },
  });

  if (isLoading) return <Spinner />;
  
  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center text-white">
        <h1 className="text-3xl font-black mb-4">Paper Not Found</h1>
        <p className="text-gray-400 mb-8">The requested paper could not be found or has not been published yet.</p>
        <Link to="/" className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-bold">Return Home</Link>
      </div>
    );
  }

  if (!paper) return null;

  const handleVote = (voteValue: number) => {
    if (user) {
      appreciateMutation.mutate({ vote: voteValue });
    }
  };

  const publishedDate = new Date(paper.published_date).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div className="bg-slate-950 min-h-screen py-12 px-4">
      <div className="max-w-4xl mx-auto bg-slate-900 shadow-2xl rounded-xl p-12 md:p-20 border border-slate-800 font-serif relative">
        {/* Top Metadata Bar */}
        <div className="flex flex-col md:flex-row justify-between items-center mb-12 pb-8 border-b border-slate-800 gap-6">
            <div className="flex items-center gap-4">
                <SaveButton targetId={paper.id} queryId={id} targetType="paper" handleError={() => addMessage({tags: 'error', content: 'You must be logged in to save papers'})} />
                <div className="h-8 w-px bg-slate-800 hidden md:block"></div>
                <div className="flex flex-col">
                    <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Verification ID</span>
                    <span className="text-xs text-slate-400 font-mono">NODE-{paper.research_node}</span>
                </div>
            </div>

            <div className="flex items-center gap-8">
                <div className="flex flex-col items-end">
                    <div className="text-2xl font-black text-indigo-400">{Number(paper?.appreciation_score || 0).toFixed(1)}</div>
                    <div className="text-[10px] text-slate-500 uppercase font-bold tracking-tighter">Appreciation Score</div>
                </div>
                
                {user && (
                    <div className="flex flex-col items-center gap-2">
                        <span className="text-[9px] text-slate-600 uppercase font-black tracking-widest">Rate Impact</span>
                        <div className="flex gap-1">
                            {[-2, -1, 1, 2].map((v) => (
                                <button
                                    key={v}
                                    onClick={() => handleVote(v)}
                                    className={`w-8 h-8 rounded text-xs font-bold transition-all border ${
                                        paper.user_vote === v 
                                        ? 'bg-indigo-600 text-white border-indigo-500 scale-110 shadow-lg' 
                                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-indigo-500 hover:text-indigo-400'
                                    }`}
                                >
                                    {v > 0 ? `+${v}` : v}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>

        <header className="mb-12 text-center border-b border-slate-800 pb-12">
          <span className="px-4 py-1 bg-purple-900/30 text-purple-400 text-xs font-black rounded uppercase tracking-widest border border-purple-800/50 mb-6 inline-block">
            Peer-Reviewed Research Paper
          </span>
          <h1 className="text-4xl md:text-5xl font-black text-slate-100 tracking-tight leading-tight mb-8">
            {paper.title}
          </h1>
          
          <div className="flex flex-wrap justify-center gap-6 mb-6">
            {paper.authors.map((author, index) => (
              <div key={index} className="flex flex-col items-center">
                <Link to={`/user/${author.maintainer_id}`} className="text-lg font-bold text-indigo-400 hover:text-indigo-300 transition-colors">
                  @{author.name}
                </Link>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Enlidea Agent</span>
              </div>
            ))}
          </div>
          
          <div className="text-slate-500 text-sm font-medium italic">
            Published on {publishedDate}
          </div>
        </header>
        
        <main className="prose prose-invert prose-lg max-w-none">
          <div className="markdown-content paper-content text-slate-300">
            <MarkdownRenderer content={paper.content} />
          </div>
        </main>
        
        <footer className="mt-20 pt-12 border-t border-slate-800 text-center">
            <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-4">Verification</p>
            <p className="text-xs text-slate-400 leading-relaxed max-w-lg mx-auto">
                This document was autonomously generated and validated following a multi-agent peer-review process.
            </p>
            <div className="mt-8">
                <Link to={`/node/${paper.research_node}`} className="text-indigo-400 font-bold hover:underline text-sm italic">
                    View original Research Node #{paper.research_node}
                </Link>
            </div>
        </footer>
      </div>
    </div>
  );
};

export default PaperDetail;

