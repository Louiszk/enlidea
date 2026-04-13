import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

const Dropdown = ({ user, elements }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const handleClickOutside = (event) => {
    if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
      setIsOpen(false);
    }
  };

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center hover:text-gray-300 font-semibold border-2 p-1 rounded-md border-zinc-700"
      >
        @{user.username}
        <svg 
          className={`ml-1 h-4 w-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24" 
          xmlns="http://www.w3.org/2000/svg"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
        </svg>
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-zinc-800 rounded-md shadow-lg py-1 z-10">
          {elements.map((element, index) => (
            <Link
              key={index}
              to={element.route}
              className="block px-4 py-2 text-sm text-gray-200 hover:bg-zinc-700"
              onClick={() => setIsOpen(false)}
            >
              {element.name}
            </Link>
          ))}
        </div>
      )}
      <div className='flex flex-col gap-1'>
      <span className="text-blue-400 flex justify-end pr-2 font-semibold">{Number(user.balance_blue_stars || 0).toFixed(2)} ✧</span>
      </div>
    </div>
  );
};

export default Dropdown;
