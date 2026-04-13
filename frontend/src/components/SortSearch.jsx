import React, { useState, useCallback } from 'react';
import { useDebounce } from 'use-debounce';
import { SearchIcon } from './Icons';

const SortSearch = ({ onSortChange, onSearchChange, noAdded }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm] = useDebounce(searchTerm, 300);

  const handleSearchChange = useCallback((value) => {
    setSearchTerm(value);
  }, []);

  React.useEffect(() => {
    onSearchChange(debouncedSearchTerm);
  }, [debouncedSearchTerm, onSearchChange]);

  return (
    <div className="flex flex-col sm:flex-row gap-4 lg:gap-16 max-w-fit rounded-md border-2 border-gray-600 p-2">
      <div className="flex flex-col sm:flex-row gap-2 text-zinc-200">
        <label htmlFor="sort" className="block font-semibold">Sort by:</label>
        <select
          id="sort"
          onChange={(e) => onSortChange(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {!noAdded && <option value="added_desc">Added (Newest First)</option>}
          {!noAdded && <option value="added_asc">Added (Oldest First)</option>}
          <option value="created_desc">Created At (Newest First)</option>
          <option value="created_asc">Created At (Oldest First)</option>
        </select>
      </div>
      <div className="relative flex-grow">
        <div className="flex items-center bg-gray-900 p-2 rounded-lg overflow-hidden shadow-lg">
          <SearchIcon />
          <input
            type="text"
            maxLength={255}
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search Posts..."
            className="w-full px-2 bg-gray-900 text-white rounded-lg focus:outline-none"
          />
        </div>
      </div>
    </div>
  );
};

export default SortSearch;


