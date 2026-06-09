import React from 'react';
import { RatedIcon } from './Icons';

const ViewFullRating = ({ soundness, significance, novelty, clarity }: { soundness?: number; significance?: number; novelty?: number; clarity?: number }) => {
  const ratingItems = [
    { label: 'Soundness', value: soundness },
    { label: 'Significance', value: significance },
    { label: 'Novelty', value: novelty },
    { label: 'Clarity', value: clarity },
  ];

  return (
    <div className="relative">
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 rounded-lg shadow-xl whitespace-nowrap">
        <div className="absolute right-full top-1/2 transform -translate-y-1/2">
          <svg width="8" height="16" viewBox="0 0 8 16" fill="currentColor">
            <path d="M0 8L8 0V16L0 8Z" />
          </svg>
        </div>
        {ratingItems.map(({ label, value }) => (
          <div key={label} className="flex items-center mb-2 last:mb-0">
            <span className="font-semibold mr-2">{label}:</span>
            <div className="flex items-center">
              <span className="mr-1">{Number(value || 0).toFixed(1)}</span>
              <RatedIcon className="w-5 h-5 text-yellow-400" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ViewFullRating;

