import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchCapabilities } from '../services/fetchService';
import CapabilitySearch from '../components/CapabilitySearch';
import { Spinner } from '../components/Icons';
import Error from '../components/Error';

const ArrowIcon = ({ isOpen, onClick }) => (
  <svg
    className={`w-6 h-6 cursor-pointer transition-transform duration-300 ${isOpen ? 'transform rotate-180 text-indigo-400 hover:text-indigo-300' : 'text-zinc-400 hover:text-zinc-300'}`}
    onClick={onClick}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="10" />
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const CategoryTree = ({ categories, level = 0 }) => {
  const [openCategories, setOpenCategories] = useState({});

  const toggleCategory = (category) => {
    setOpenCategories(prev => ({
      ...prev,
      [category.slug]: !prev[category.slug]
    }));
  };

  return (
    <ul className={`list-none ${level > 0 ? `ml-${level * 4} sm:ml-${level * 6} md:ml-${level * 8}` : ''}`}>
      {categories.map((category) => (
        <li key={category.slug} className="my-4">
          <div className="flex items-center space-x-2">
            <Link
              to={`/categories/${category.slug}`}
              className="text-zinc-200 hover:text-zinc-100 font-semibold transition-colors duration-300 text-lg"
            >
              {category.title}
            </Link>
            {category.has_children && (
              <ArrowIcon
                isOpen={openCategories[category.slug]}
                onClick={() => toggleCategory(category)}
              />
            )}
          </div>
          {openCategories[category.slug] && category.has_children && (
            <ChildCategories slug={category.slug} level={level + 1} />
          )}
        </li>
      ))}
    </ul>
  );
};

const ChildCategories = ({ slug, level }) => {
  const { data: childCategories, isLoading, error } = useQuery({
    queryKey: ['categories', slug],
    queryFn: () => fetchCapabilities(slug),
    staleTime: 1000 * 60 * 60 * 2, 
    gcTime: 1000 * 60 * 60 * 24, 
  });

  if (isLoading) return <div className="text-gray-400 ml-4">Loading...</div>;
  if (error) return <div className="text-red-400 ml-4">Error loading sub-capabilities</div>;

  return <CategoryTree categories={childCategories} level={level} />;
};

const CapabilityList = () => {
  const { data: categories, isLoading, error } = useQuery({
    queryKey: ['categories', 'top'],
    queryFn: () => fetchCapabilities('top'),
    staleTime: 1000 * 60 * 60 * 2, 
    gcTime: 1000 * 60 * 60 * 24, 
  });

  if (isLoading) return <Spinner />;
  if (error) return <Error message="Failed to fetch capabilities. Please try again later." />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 bg-gray-900 min-h-screen">
      <h1 className="text-4xl font-bold text-gray-100 mb-8 text-center">Browse Capabilities</h1>
      <div className="bg-gray-800 rounded-lg shadow-lg p-6">
        <div className='flex justify-end w-full px-4'><CapabilitySearch /></div>
        <CategoryTree categories={categories} />
      </div>
    </div>
  );
};

export default CapabilityList;

