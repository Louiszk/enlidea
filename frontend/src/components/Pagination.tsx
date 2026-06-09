import React from 'react';

const Pagination = ({ currentPage, totalPages, onPageChange, loading }: { currentPage: number; totalPages: number; onPageChange: (page: number) => void; loading?: boolean; }) => {
  const getPageNumbers = () => {
    let pages = [];
    if (totalPages <= 3) {
      pages = [...Array(totalPages)].map((_, i) => i + 1);
    } else if (currentPage <= 2) {
      pages = [1, 2, 3];
    } else if (currentPage >= totalPages - 1) {
      pages = [totalPages - 2, totalPages - 1, totalPages];
    } else {
      pages = [currentPage - 1, currentPage, currentPage + 1];
    }
    return pages;
  };

  const pageNumbers = getPageNumbers();

  return (
    <div className="flex flex-row justify-center select-none text-white font-semibold items-center mt-6">
      {loading ? (
        <div className="flex justify-center items-center h-12 animate-pulse">
          Loading...
        </div>
      ) : (
        <nav className="flex flex-row items-center border-2 border-zinc-500 bg-zinc-500 rounded-lg">
          <button
            onClick={() => onPageChange(1)}
            disabled={currentPage === 1 || loading}
            title='Navigate to first page'
            className="w-10 aspect-square flex items-center justify-center border border-gray-700 bg-gray-600 rounded-l-lg text-xs font-bold disabled:opacity-50 hover:bg-gray-500"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
            </svg>
          </button>
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1 || loading}
            title='Previous Page'
            className="w-10 aspect-square flex items-center justify-center border border-gray-700 bg-gray-600 text-xs font-bold disabled:opacity-50 hover:bg-gray-500"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          {!(currentPage === 1 || loading) && <div className="w-10 aspect-square flex items-center justify-center border border-gray-700 bg-gray-600 text-xs font-bold">...</div>}
          {pageNumbers.map((number) => (
            <button
              key={number}
              onClick={() => onPageChange(number)}
              disabled={loading}
              className={`w-10 aspect-square flex items-center justify-center ${
                currentPage === number
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
              }`}
            >
              {number}
            </button>
          ))}
          {!(currentPage === totalPages || loading) && <div className="w-10 aspect-square flex items-center justify-center border border-gray-700 bg-gray-600 text-xs font-bold">...</div>}
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages || loading}
            title='Next Page'
            className="w-10 aspect-square flex items-center justify-center border border-gray-700 bg-gray-600 text-xs font-bold disabled:opacity-50 hover:bg-gray-500"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
          <button
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage >= totalPages || loading}
            title='Navigate to last page'
            className="w-10 aspect-square flex items-center justify-center border border-gray-700 rounded-r-lg bg-gray-600 text-xs font-bold disabled:opacity-50 hover:bg-gray-500"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </nav>
      )}
    </div>
  );
};

export default Pagination;


