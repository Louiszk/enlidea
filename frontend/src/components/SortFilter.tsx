import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { allTags, allTypes } from '../services/constants';

export interface SortFilterProps {
  sortBy: string;
  tags?: string[];
  types?: string[];
  status?: string[];
  slug?: string;
}

const SortFilter: React.FC<SortFilterProps> = ({ sortBy, tags, types, status, slug }) => {
  const navigate = useNavigate();
  const [localSortBy, setLocalSortBy] = useState(sortBy || 'created_desc');
  const [localStatus, setLocalStatus] = useState<string[]>(status || []);
  const [localSelectedTags, setLocalSelectedTags] = useState<string[]>(tags ? tags : (slug ? [slug] : []));
  const [localSelectedTypes, setLocalSelectedTypes] = useState<string[]>(types || []);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const [showTagsDropdown, setShowTagsDropdown] = useState(false);
  const [showTypesDropdown, setShowTypesDropdown] = useState(false);

  const statusOptions = [
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'in_review', label: 'In Review' },
    { value: 'published', label: 'Published' },
    { value: 'failed', label: 'Failed' }
  ];

  const handleSortChange = (newSortBy: string) => {
    setLocalSortBy(newSortBy);
    applyFilters(newSortBy, localStatus, localSelectedTags, localSelectedTypes);
  };

  const handleApplyFilters = () => {
    applyFilters(localSortBy, localStatus, localSelectedTags, localSelectedTypes);
  };

  const applyFilters = (currentSortBy: string, currentStatus: string[], currentTags: string[], currentTypes: string[]) => {
    const filters: { status?: string; tags?: string; types?: string } = {};
    if (currentStatus.length > 0) filters.status = currentStatus.join(',');
    if (currentTags.length > 0) filters.tags = currentTags.join(',');
    if (currentTypes.length > 0) filters.types = currentTypes.join(',');

    const filterString = encodeURIComponent(JSON.stringify(filters));
    navigate(`?sort=${currentSortBy}&filters=${filterString}&page=1`);
  };

  const toggleStatus = (statusVal: string) => {
    setLocalStatus(prev => 
      prev.includes(statusVal) 
        ? prev.filter(s => s !== statusVal)
        : [...prev, statusVal]
    );
  };

  const toggleTag = (tag: string) => {
    setLocalSelectedTags(prev => 
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const toggleType = (type: string) => {
    setLocalSelectedTypes(prev => 
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  return (
    <div className="flex flex-wrap justify-between gap-4 items-center p-4 bg-zinc-900 rounded-lg text-sm font-semibold text-white select-none">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <div className="flex items-center gap-2">
          <label htmlFor="sort" className="whitespace-nowrap">Sort by:</label>
          <select
            id="sort"
            value={localSortBy}
            onChange={(e) => handleSortChange(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="created_desc">Newest Proposals</option>
            <option value="bounty_amount">Highest Bounty</option>
            <option value="collaborative">Most Collaborative</option>
            <option value="rating">Top Rated</option>
            <option value="trending">Trending</option>
          </select>
        </div>

        <div className="relative">
          <button 
            onClick={() => {setShowStatusDropdown(!showStatusDropdown); setShowTagsDropdown(false); setShowTypesDropdown(false);}} 
            className="bg-gray-800 border border-gray-700 rounded-md p-2 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[120px]"
          >
            Status {localStatus.length > 0 && `(${localStatus.length})`}
          </button>
          {showStatusDropdown && (
            <div className="absolute z-20 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-md shadow-lg overflow-hidden">
              {statusOptions.map(option => (
                <label key={option.value} className="flex items-center p-3 hover:bg-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localStatus.includes(option.value)}
                    onChange={() => toggleStatus(option.value)}
                    className="mr-3 h-4 w-4 rounded border-gray-600 text-indigo-500 focus:ring-indigo-500 bg-gray-700"
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="relative">
          <button 
            onClick={() => {setShowTypesDropdown(!showTypesDropdown); setShowStatusDropdown(false); setShowTagsDropdown(false);}} 
            className="bg-gray-800 border border-gray-700 rounded-md p-2 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[120px]"
          >
            Types {localSelectedTypes.length > 0 && `(${localSelectedTypes.length})`}
          </button>
          {showTypesDropdown && (
            <div className="absolute z-20 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-md shadow-lg overflow-hidden">
              {allTypes.filter(t => t !== "All Types").map(type => (
                <label key={type} className="flex items-center p-3 hover:bg-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localSelectedTypes.includes(type)}
                    onChange={() => toggleType(type)}
                    className="mr-3 h-4 w-4 rounded border-gray-600 text-indigo-500 focus:ring-indigo-500 bg-gray-700"
                  />
                  <span>{type}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="relative">
          <button 
            onClick={() => {setShowTagsDropdown(!showTagsDropdown); setShowStatusDropdown(false); setShowTypesDropdown(false);}} 
            className="bg-gray-800 border border-gray-700 rounded-md p-2 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[120px]"
          >
            Capabilities {localSelectedTags.length > 0 && `(${localSelectedTags.length})`}
          </button>
          {showTagsDropdown && (
            <div className="absolute z-20 mt-1 w-64 bg-gray-800 border border-gray-700 rounded-md shadow-lg max-h-60 overflow-y-auto">
              {allTags.map(tag => (
                <label key={tag} className="flex items-center p-3 hover:bg-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localSelectedTags.includes(tag)}
                    onChange={() => toggleTag(tag)}
                    className="mr-3 h-4 w-4 rounded border-gray-600 text-indigo-500 focus:ring-indigo-500 bg-gray-700"
                  />
                  <span>{tag}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      <button 
        onClick={handleApplyFilters} 
        className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-md font-bold transition-colors duration-200"
      >
        Apply Filters
      </button>
    </div>
  );
};

export default SortFilter;
