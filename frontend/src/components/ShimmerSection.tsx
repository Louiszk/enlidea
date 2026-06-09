export const ShimmerCard = () => (
    <div className="block w-full select-none flex flex-col bg-gray-800 rounded-xl border border-indigo-500/50 shadow-lg">
      <div className="p-4 w-full relative">
        <div className='flex justify-center mb-2'>
          <div className="px-6 py-1 my-2 bg-gray-700 rounded-md shimmer-effect" style={{width: '120px', height: '24px'}}></div>
        </div>
        <div className="flex items-center mb-4 py-2 h-16 overflow-hidden">
          <div className="w-3/4 h-8 bg-gray-700 rounded shimmer-effect"></div>
        </div>
        <div className="mb-4">
          <div className="w-full h-4 bg-gray-700 rounded mb-2 shimmer-effect"></div>
          <div className="w-3/4 h-4 bg-gray-700 rounded shimmer-effect"></div>
        </div>
        <div className="flex flex-wrap gap-2 mb-2">
          <div className="px-3 py-1 bg-gray-700 rounded-full shimmer-effect" style={{width: '80px', height: '24px'}}></div>
          <div className="px-3 py-1 bg-gray-700 rounded-full shimmer-effect" style={{width: '100px', height: '24px'}}></div>
        </div>
        <div className="flex flex-col gap-4 w-full">
          <div className="flex">
            <div className="w-1/2 h-4 bg-gray-700 rounded shimmer-effect"></div>
          </div>
          <div className='flex flex-row gap-8'>
            <div className="w-16 h-6 bg-gray-700 rounded-full shimmer-effect"></div>
            <div className="w-24 h-6 bg-gray-700 rounded shimmer-effect"></div>
          </div>
        </div>
      </div>
    </div>
);

export const ShimmerSection = () => (
  <div className="mb-8">
    <div className="w-1/4 h-8 bg-gray-700 rounded mb-4 shimmer-effect"></div>
    <div className="flex space-x-4 overflow-hidden">
    {Array.from({ length: 5 }, () => `key-${Math.random().toString(36).substring(2, 9)}`).map((k) => 
    <div key={k} className="min-w-64 max-w-64 sm:min-w-80 sm:max-w-80 flex-shrink-0"><ShimmerCard /></div>
    )}
    </div>
  </div>
);