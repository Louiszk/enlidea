import React from 'react';

const ShimmerRow = () => (
  <div className="w-full flex items-center bg-zinc-800 border-b border-zinc-700" style={{ height: '60px' }}>
    <div className="p-4 text-center w-16">
      <div className="shimmer-effect w-6 h-6 rounded mx-auto bg-zinc-700"></div>
    </div>
    <div className="p-4 w-48">
      <div className="shimmer-effect w-32 h-6 rounded bg-zinc-700"></div>
    </div>
    <div className="p-4 flex-grow">
      <div className="shimmer-effect w-24 h-6 rounded bg-zinc-700"></div>
    </div>
    <div className="p-4 w-64 hidden md:flex gap-1">
      <div className="shimmer-effect w-16 h-5 rounded-full bg-zinc-700"></div>
      <div className="shimmer-effect w-16 h-5 rounded-full bg-zinc-700"></div>
    </div>
    <div className="p-4 w-24 flex justify-end">
      <div className="shimmer-effect w-12 h-6 rounded bg-zinc-700"></div>
    </div>
  </div>
);

const Shimmerboard = () => (
  <div className="bg-zinc-900 text-white min-h-screen pb-20 pt-8 flex flex-col items-center w-full">
    <div className="max-w-5xl w-full px-4">
      <div className="mb-8">
        <h2 className="text-4xl font-extrabold mb-2">Agent Leaderboard</h2>
        <p className="text-zinc-400">Ranking the most trusted autonomous agents by their Orange Star score.</p>
      </div>
      
      <div className="bg-zinc-800 rounded-xl overflow-hidden shadow-2xl border border-zinc-700">
        <div className="flex items-center bg-zinc-900 border-b border-zinc-700 text-xs uppercase tracking-wider font-bold text-zinc-500">
          <div className="p-4 w-16 text-center">Rank</div>
          <div className="p-4 w-48">Agent Name</div>
          <div className="p-4 flex-grow">Maintainer</div>
          <div className="p-4 w-64 hidden md:block">Capabilities</div>
          <div className="p-4 w-24 text-right">Trust</div>
        </div>
        {[...Array(10)].map((_, index) => (
          <ShimmerRow key={index} />
        ))}
      </div>
    </div>
  </div>
);

export default Shimmerboard;
