import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Search from '../components/Search';
import Dropdown from '../components/Dropdown';
import logo from '../assets/images/logo-enlidea.png';
import { Link } from 'react-router-dom';
import Notifications from '../components/Notifications';

const Header = () => {
  const { user, loading } = useAuth();

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLinkClick = (_event) => {
    setIsMobileMenuOpen(false);
  };

  const dropdownElements = [
    { name: 'Dashboard', route: '/dashboard' },
    { name: 'Library', route: '/library'},
    { name: 'Active Assignments', route: '/active-assignments' },
    { name: 'Messages ', route: '/messages'},
    { name: 'Settings', route: '/settings' },
    { name: 'Statistics', route: '/statistics' },
    { name: 'Logout', route: '/logout' },
  ];

  return (
    <header className="bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-3">
        <div className="flex flex-row items-center justify-between">
          <Link to={"/"} className="flex-shrink-0 p-2">
            <img src={logo} alt="Logo" className="h-12 w-auto" />
          </Link>
          
          <div className="hidden lg:block flex-grow mx-4">
            <Search />
          </div>
          
          <nav className="flex flex-col sm:flex-row items-center gap-2 sm:gap-6">
            {user && 
            <div className="flex flex-row items-center gap-4">
              <Notifications />
            </div>
            }
            {loading ? (
              <div className="animate-pulse h-16 font-semibold">Loading...</div>
            ) : user ? (
              <div className="h-16">
              <Dropdown user={user} elements={[...[{ name: 'Profile', route: `/user/${user.id}`}], ...dropdownElements]} />
              </div>
            ) : (
              <div className="flex flex-row items-center gap-2 h-16 font-semibold">
                <Link to="/login" className="hover:text-gray-300">Log in</Link>
                <div>|</div>
                <Link to="/register" className="hover:text-gray-300">Register</Link>
              </div>
            )}
          </nav>
        </div>
        
        <div className="lg:hidden mt-4">
          <Search />
        </div>
      </div>
      
      {/* navigation */}
      <div className="bg-gray-800">
        <div ref={menuRef} className="container mx-auto px-4 py-2">
          <div className="flex justify-start items-center">
            <div className="sm:hidden">
              <button onClick={toggleMobileMenu} className="text-white focus:outline-none">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16m-7 6h7"></path>
                </svg>
              </button>
            </div>
            
            {/* Full menu for larger screens */}
            <div className="hidden sm:flex space-x-8 whitespace-nowrap font-semibold justify-start md:justify-end md:pr-48 text-sm uppercase tracking-wide">
            <Link to="/explore" className="text-zinc-400 hover:text-white transition-colors">Explore</Link>
              <Link to="/research-landscape" className="text-zinc-400 hover:text-white transition-colors">Landscape</Link>
              <Link to="/trending" className="text-zinc-400 hover:text-white transition-colors">Trending</Link>
              <Link to="/categories" className="text-zinc-400 hover:text-white transition-colors">Capabilities</Link>
              <Link to="/leaderboard" className="text-zinc-400 hover:text-white transition-colors">Agents</Link>
              {user && (
                <>
                  <Link to="/home-feed" className="text-zinc-400 hover:text-white transition-colors">Feed</Link>
                  <Link to="/dashboard" className="text-indigo-400 hover:text-indigo-300 font-bold transition-colors">Dashboard</Link>
                </>
              )}
            </div>
          </div>
          
          {/* Collapsible menu for small screens */}
          <div className={`sm:hidden font-semibold ${isMobileMenuOpen ? 'block' : 'hidden'} mt-2`}>
            <Link to="/explore" className="block text-zinc-400 hover:text-white py-2" onClick={handleLinkClick}>Explore</Link>
            <Link to="/research-landscape" className="block text-zinc-400 hover:text-white py-2" onClick={handleLinkClick}>Landscape</Link>
            <Link to="/trending" className="block text-zinc-400 hover:text-white py-2" onClick={handleLinkClick}>Trending</Link>
            <Link to="/categories" className="block text-zinc-400 hover:text-white py-2" onClick={handleLinkClick}>Capabilities</Link>
            <Link to="/leaderboard" className="block text-zinc-400 hover:text-white py-2" onClick={handleLinkClick}>Agents</Link>
            {user && (
              <>
                <Link to="/home-feed" className="block text-zinc-400 hover:text-white py-2" onClick={handleLinkClick}>Feed</Link>
                <Link to="/dashboard" className="block text-indigo-400 hover:text-indigo-300 py-2 font-bold" onClick={handleLinkClick}>Dashboard</Link>
              </>
            )}
          </div>
        </div>
      </div>

    </header>
  );
};

export default Header;



