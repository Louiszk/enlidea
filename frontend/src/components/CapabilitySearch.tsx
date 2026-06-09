import React, { useState, useRef } from 'react';
import { useDebounce } from 'use-debounce';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchCapabilitySearch } from '../services/fetchService';
import { SearchIcon } from './Icons';

const CapabilitySearch = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm] = useDebounce(searchTerm, 300);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const { data: results = [] } = useQuery({
    queryKey: ['searchCapabilities', debouncedSearchTerm],
    queryFn: () => fetchCapabilitySearch(debouncedSearchTerm),
    enabled: !!debouncedSearchTerm,
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000 * 24,
  });

  React.useEffect(() => {
    if (debouncedSearchTerm) {
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !(dropdownRef.current as any).contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [debouncedSearchTerm]);

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="flex items-center bg-gray-900 p-2 rounded-lg overflow-hidden shadow-lg">
      <SearchIcon />
        <input
          type="text"
          maxLength={255}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search capabilities..."
          className="w-full px-2 bg-gray-900 text-white rounded-lg focus:outline-none"
        />
      </div>
      {isOpen && results.length > 0 && (
        <ul className="absolute z-10 w-full max-h-60 overflow-y-scroll bg-gray-900 text-white border border-gray-700 mt-1 rounded-lg shadow-lg">
          {results.map((capability) => (
            <li key={capability.id} className="p-2 hover:bg-gray-700 transition duration-200">
              <Link to={`/categories/${capability.slug}`} className="block">
                {capability.title}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default CapabilitySearch;



