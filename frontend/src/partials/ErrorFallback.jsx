import React from 'react';
import { SadFace } from '../components/Icons';
import logo from '../assets/images/logo-enlidea.png';

const ErrorFallback = ({ error, resetErrorBoundary }) => {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col gap-4 items-center justify-center p-4">
        <img className="mx-auto h-12 w-auto" src={logo} alt="Enlidea Logo" />
        <div className="max-w-2xl w-full bg-gray-800 rounded-lg shadow-xl p-8">
            <h2 className="text-3xl font-bold mb-4 text-red-500">Something went wrong</h2>
            <p className="mb-4 text-gray-300">We're sorry, but an unexpected error occurred. Our team has been notified and is working on a solution.</p>
            
            <SadFace />
            
        </div>
    </div>
  );
};

export default ErrorFallback;
