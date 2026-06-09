import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import AccountSettings from './AccountSettings';
import Preferences from './Preferences';
import PrivacySettings from './PrivacySettings';
import ProfileSettings from './ProfileSettings';
import { useAuth } from '../../contexts/AuthContext';
import BaseAuth from '../auth/BaseAuth';

const Settings = () => {
  const [activeSection, setActiveSection] = useState('profileSettings');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { user, loading } = useAuth();

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'profileSettings':
        return <ProfileSettings />;
      case 'accountSettings':
        return <AccountSettings />;
      case 'preferences':
        return <Preferences />;
      case 'privacySettings':
        return <PrivacySettings />;
      default:
        return <ProfileSettings />;
    }
  };

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  if (loading) {
    return <div className="flex justify-center items-center h-screen text-white">Loading...</div>;
  }

  if (!user) {
    return (
      <BaseAuth>
        <div className="bg-gray-800 p-4 rounded-lg shadow-md text-center w-full">
          <h2 className="text-xl font-bold mb-4 text-white">You are not logged in</h2>
          <p className="mb-4 text-gray-300">Please sign in to access your settings.</p>
          <Link
            to="/login"
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded transition duration-300"
          >
            Sign In
          </Link>
        </div>
      </BaseAuth>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-4">
      {/* Mobile Menu Button */}
      <button
        onClick={toggleMenu}
        className="md:hidden bg-gray-800 text-white font-semibold p-2 rounded-md mb-4"
      >
        {isMenuOpen ? 'Close Menu' : 'Open Menu'}
      </button>

      <div className="flex flex-col md:flex-row max-w-7xl mx-auto pt-8">
        {/* Sidebar / Mobile Menu */}
        <div className={`${isMenuOpen ? 'block' : 'hidden'} md:block md:w-64 bg-gray-800 shadow-md rounded-md mb-4 md:mb-0 md:mr-4`}>
          <div className="p-4">
            <h2 className="text-xl font-black mb-4 text-white tracking-tighter">ACCOUNT SETTINGS</h2>
            <nav>
              <ul className="space-y-2">
                {[
                  { id: 'profileSettings', label: 'Public Profile' },
                  { id: 'accountSettings', label: 'Account Security' },
                  { id: 'privacySettings', label: 'Privacy' },
                  { id: 'preferences', label: 'Preferences' },
                ].map((section) => (
                  <li key={section.id}>
                    <button
                      onClick={() => {
                        setActiveSection(section.id);
                        setIsMenuOpen(false);
                      }}
                      className={`w-full text-left py-2 px-4 rounded transition-all duration-200 ${
                        activeSection === section.id
                          ? 'bg-indigo-600 text-white font-bold shadow-lg shadow-indigo-600/20'
                          : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                      }`}
                    >
                      {section.label}
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </div>

        {/* Main Content */}
        <div className='flex-1 bg-gray-800 p-4 rounded-md shadow-2xl border border-gray-700/50'>
          <BaseAuth showLogo={false}>
            {renderActiveSection()}
          </BaseAuth>
        </div>
      </div>
    </div>
  );
};

export default Settings;



