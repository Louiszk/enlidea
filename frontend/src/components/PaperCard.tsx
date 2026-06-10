import React from 'react';
import { Paper } from '../api/generated/api';
import { Link } from 'react-router-dom';
import { BookmarkIcon } from './Icons';

const PaperCard = ({ paper }: { paper: Paper }) => {
  const publishedDate = new Date(paper.published_date).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <Link
      to={`/paper/${paper.research_node}`}
      className="block w-full max-w-md mx-auto bg-slate-700 rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1 overflow-hidden border border-slate-500"
    >
      <div className="p-6">
        <div className="flex justify-between items-start mb-4">
          <span className="px-3 py-1 bg-purple-900/40 text-purple-300 text-[10px] font-black rounded uppercase tracking-widest border border-purple-700/50">
             Published Paper
          </span>
          <span className="text-slate-400 text-xs font-medium">{publishedDate}</span>
        </div>
        
        <h3 className="text-xl font-bold text-slate-100 mb-6 line-clamp-2 leading-tight">
          {paper.title}
        </h3>
        
        <div className="flex justify-between items-end pt-4 border-t border-slate-700">
          <div className="flex flex-col gap-2">
            <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Authors</span>
            <div className="flex flex-wrap gap-2">
              {paper.authors.map((author, index: number) => (
                <span key={index} className="text-sm font-bold text-indigo-400">
                  @{author.name}{index < paper.authors.length - 1 ? ',' : ''}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1 text-slate-400">
            <BookmarkIcon />
            <span className="text-xs font-bold">{paper.saves || 0}</span>
          </div>
        </div>
      </div>
    </Link>
  );
};

export default PaperCard;
