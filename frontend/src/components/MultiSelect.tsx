import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useDebounce } from 'use-debounce';

const MultiSelect = ({ onChange, value, _prefilled, fetchSearch, placeholder = "Search...", maxItems = 3, labelField = "title" }: { onChange: (value: any[]) => void; value?: any[]; _prefilled?: any[]; fetchSearch: (term: string) => Promise<any[]>; placeholder?: string; maxItems?: number; labelField?: string; }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [debouncedSearchTerm] = useDebounce(searchTerm, 300);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedOptions, setSelectedOptions] = useState(value || []);
  const dropdownRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const data = await fetchSearch(debouncedSearchTerm);
      setResults(data);
    } catch (error) {
      console.error('Error fetching search results:', error);
    }
  }, [debouncedSearchTerm, fetchSearch]);

  useEffect(() => {
    if (debouncedSearchTerm) {
      fetchData();
    } else {
      setResults([]);
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
  }, [debouncedSearchTerm, fetchData]);

  const handleSelect = (option: any) => {
    let newSelectedOptions;
    if (selectedOptions.some(item => item.id === option.id)) {
      newSelectedOptions = selectedOptions.filter((item) => item.id !== option.id);
    } else if (selectedOptions.length < maxItems) {
      newSelectedOptions = [...selectedOptions, option];
    } else {
      return;
    }
    setSelectedOptions(newSelectedOptions);
    setSearchTerm('');
    onChange(newSelectedOptions);
  };

  const removeOption = (optionId: any) => {
    const newSelectedOptions = selectedOptions.filter((item) => item.id !== optionId);
    setSelectedOptions(newSelectedOptions);
    onChange(newSelectedOptions);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="flex flex-wrap items-center bg-gray-800 text-xs sm:text-sm rounded-lg overflow-hidden shadow-lg p-2">
        {selectedOptions.map((option) => (
          <div key={`s${option.id}`} className="flex items-center bg-indigo-700 text-indigo-200 rounded-full px-3 py-1 m-1">
            <span className="text-white mr-2">{option[labelField]}</span>
            <button
              onClick={() => removeOption(option.id)}
              className="text-gray-400 hover:text-white focus:outline-none"
            >
              &times;
            </button>
          </div>
        ))}
        {selectedOptions.length < maxItems && <input
          type="text"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setIsOpen(true);
          }}
          placeholder={placeholder}
          className="flex-grow p-2 bg-gray-900 text-white rounded-lg focus:outline-none"
        />}
      </div>
      {isOpen && results.length > 0 && selectedOptions.length < maxItems && (
        <ul className="absolute z-10 w-full max-h-60 overflow-y-scroll bg-gray-900 text-white border border-gray-700 mt-1 rounded-lg shadow-lg">
          {results.map((item) => (
            <li
              key={item.id}
              className={`p-2 hover:bg-gray-700 transition duration-200 cursor-pointer ${
                selectedOptions.some(selected => selected.id === item.id) ? 'bg-gray-700' : ''
              }`}
              onClick={() => handleSelect(item)}
            >
              {item[labelField]}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default MultiSelect;
