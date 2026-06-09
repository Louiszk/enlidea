import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchHighImpactData, fetchPapers } from '../services/fetchService';
import TrendingSection from '../components/TrendingSection';
import { ShimmerSection } from '../components/ShimmerSection';
import Error from '../components/Error';

const ResearchLandscape = () => {
  const [view, setView] = useState('bounties');

  const { data: highImpactData, isPending: isHighImpactLoading, isError: isHighImpactError, error: highImpactError } = useQuery({
    queryKey: ['highImpact'],
    queryFn: fetchHighImpactData,
    staleTime: 1000 * 60 * 2, 
    gcTime: 1000 * 60 * 60 * 2,
    enabled: view === 'bounties'
  });

  const { data: papersData, isPending: isPapersLoading, isError: isPapersError, error: papersError } = useQuery({
    queryKey: ['landscapePapers'],
    queryFn: () => fetchPapers(1),
    staleTime: 1000 * 60 * 5,
    enabled: view === 'papers'
  });

  const isLoading = view === 'bounties' ? isHighImpactLoading : isPapersLoading;
  const isError = view === 'bounties' ? isHighImpactError : isPapersError;
  const error = view === 'bounties' ? highImpactError : papersError;

  return (
    <div className="container mx-auto px-4 py-8 flex flex-col space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
            <h1 className="text-4xl text-white font-extrabold mb-2 tracking-tight">Research Landscape</h1>
            <p className="text-zinc-400 text-lg">Explore the current state of autonomous research.</p>
        </div>

        <div className="bg-zinc-800 p-1 rounded-xl flex border border-zinc-700">
            <button 
                onClick={() => setView('bounties')}
                className={`px-6 py-2 rounded-lg font-black text-sm transition-all ${view === 'bounties' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'text-zinc-400 hover:text-zinc-200'}`}
            >
                Active Bounties
            </button>
            <button 
                onClick={() => setView('papers')}
                className={`px-6 py-2 rounded-lg font-black text-sm transition-all ${view === 'papers' ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20' : 'text-zinc-400 hover:text-zinc-200'}`}
            >
                Published Papers
            </button>
        </div>
      </div>

      {isLoading ? (
        <>
          <ShimmerSection />
          <ShimmerSection />
        </>
      ) : isError ? (
        <Error message={error.message} />
      ) : (
        <>
          {view === 'bounties' && highImpactData?.map((data, index) => (
            <TrendingSection 
              key={`trending-${index}`}
              highImpact={data.slug}
              title={data.title} 
              data={data}
            />
          ))}

          {view === 'papers' && papersData && (
            <TrendingSection 
                title="Latest Published Papers"
                data={papersData}
                isPapers={true}
            />
          )}
        </>
      )}
    </div>
  );
};

export default ResearchLandscape;
;
