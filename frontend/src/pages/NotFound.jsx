import React from 'react';
import { Link } from 'react-router-dom';
import { SadFace } from '../components/Icons';

const NotFound = () => {
  return (
    <div className="py-12 bg-gradient-to-r from-blue-400 via-green-700 to-green-500 flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-lg w-full space-y-8 bg-white p-10 rounded-xl shadow-2xl">
        <div>
          <h2 className="mt-6 text-center text-6xl font-extrabold text-gray-900">
            404
          </h2>
          <p className="mt-2 text-center text-3xl font-bold text-gray-900">
            Page Not Found
          </p>
          <p className="mt-2 text-center text-sm text-gray-600">
            The page you are looking for might have been removed or is temporarily unavailable.
          </p>
        </div>
        <div className="mt-8 space-y-6">
          <div className="flex items-center justify-center">
            <div className="text-sm">
              <Link to="/" className="font-medium text-indigo-600 hover:text-indigo-500">
                Go back to homepage
              </Link>
            </div>
          </div>
        </div>
        <SadFace/>
      </div>
    </div>
  );
};

export default NotFound;
