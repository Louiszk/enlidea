import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from 'use-debounce';
import { fetchSuggestions } from '../services/fetchService';
import { UserIcon, NodeTypeIcon, CategoryIcon, SearchIcon, RatedIcon } from './Icons';

const Search = () => {
  const [query, setQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const navigate = useNavigate();
  const inputRef = useRef(null);

  // Debounce the query value
  const [debouncedQuery] = useDebounce(query, 300);

  const { data: suggestions = [], isLoading, isError } = useQuery({
    queryKey: ['suggestions', debouncedQuery],
    queryFn: () => fetchSuggestions(debouncedQuery),
    enabled: debouncedQuery.length > 1,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 60
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setShowSuggestions(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSearch = () => {
    if (query.trim().length >= 3) {
      navigate(`/search?q=${encodeURIComponent(query)}`);
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion: any) => {
    if (suggestion.type == 'user'){
      navigate(`/user/${suggestion.id}`);
    } else if (suggestion.type == 'node') {
      navigate(`/node/${suggestion.id}`);
    } else if (suggestion.type == 'category') {
      navigate(`/categories/${suggestion.slug}`);
    } else if (suggestion.type == 'tag') {
      navigate(`/categories/undefined?filters={"tags"%3A"${suggestion.value}"}&page=1`);
    }
    setShowSuggestions(false);
  };

  const handleClickOutside = (e: MouseEvent) => {
    if (inputRef.current && !(inputRef.current as any).contains(e.target)) {
      setShowSuggestions(false);
    }
  };

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const getIcon = (type: string) => {
    switch (type) {
      case 'user':
        return <UserIcon/>;
      case 'node':
        return <NodeTypeIcon/>;
      case 'tag':
        return <RatedIcon/>;
      default:
        return <CategoryIcon/>;
    }
  };

  return (
    <div className="flex-grow mx-4">
      <div className="relative" ref={inputRef}>
        <input
          type="text"
          placeholder="Search"
          maxLength={255}
          className="w-3/4 bg-gray-800 text-white rounded-full py-2 px-4 pl-10 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
        />
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <SearchIcon />
        </div>
        {showSuggestions && debouncedQuery.length > 1 && (
          <div className="absolute z-40 w-3/4 mt-1 bg-gray-700 max-h-64 overflow-y-scroll rounded-md shadow-lg">
            {isLoading && <div className="px-4 py-2 text-white">Loading...</div>}
            {isError && <div className="px-4 py-2 text-red-400">Error fetching suggestions</div>}
            {!isLoading && !isError && (
              <>
              {query.length >= 3 && <div
              className="px-4 py-2 hover:bg-gray-600 cursor-pointer text-white flex items-center gap-2"
              onClick={handleSearch}
            >
              <SearchIcon />
              <span>Search for {query} ...</span>
            </div>}
              {suggestions.map((suggestion: any, index: number) => (
              <div
                key={index}
                className="px-4 py-2 hover:bg-gray-600 cursor-pointer text-white flex items-center gap-2"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {getIcon(suggestion.type)}
                <span>{suggestion.value}</span>
              </div>
              
            ))}</>)}
          </div>
        )}
      </div>
    </div>
  );
};

export default Search;



