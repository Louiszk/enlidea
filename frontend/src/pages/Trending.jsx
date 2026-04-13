import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchTrendingData } from '../services/fetchService';
import TrendingSection from '../components/TrendingSection';
import { ShimmerSection } from '../components/ShimmerSection';
import { plural } from '../services/constants';
import Error from '../components/Error';

const Trending = () => {
  const { data: trendingData, isPending, isError, error } = useQuery({
    queryKey: ['trending'],
    queryFn: fetchTrendingData,
    staleTime: 1000 * 60,
    gcTime: 1000 * 60 * 60,
  });
  
  return (
    <div className="container mx-auto px-4 py-8 flex flex-col space-y-6">
      <h1 className="text-2xl md:text-4xl font-bold text-gray-100 mb-8">Trending</h1>
      {isPending ? (
        <>
          <ShimmerSection />
          <ShimmerSection />
          <ShimmerSection />
          <ShimmerSection />
        </>
      ) : isError ? (
        <Error message={error.message} />
      ) : (
        <>
          {Object.entries(trendingData.trendingCombinations).map(([combination, data]) => (
            <TrendingSection 
              key={combination} 
              title={`${data.tag} ${plural(data.type)}`} 
              data={data} 
            />
          ))}

          {Object.entries(trendingData.trendingCategories).map(([categoryTitle, data]) => (
            <TrendingSection 
              key={categoryTitle} 
              title={data.category.title} 
              data={data} 
            />
          ))}
        </>
      )}
    </div>
  );
};

export default Trending;



