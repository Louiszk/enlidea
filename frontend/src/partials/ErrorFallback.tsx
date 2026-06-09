import React from 'react';
import { SadFace } from '../components/Icons';
import logo from '../assets/images/logo-enlidea.png';

interface ErrorFallbackProps {
  error: Error | null;
  resetErrorBoundary: () => void;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col gap-4 items-center justify-center p-4">
      <img className="mx-auto h-12 w-auto" src={logo} alt="Enlidea Logo" />
      <div className="max-w-2xl w-full bg-gray-800 rounded-lg shadow-xl p-8">
        <h2 className="text-3xl font-bold mb-4 text-red-500">Something went wrong</h2>
        <p className="mb-4 text-gray-300">
          We're sorry, but an unexpected error occurred. Our team has been notified and is working on a solution.
        </p>
        {error && (
          <pre className="p-4 bg-gray-900 rounded border border-gray-700 text-red-400 font-mono text-xs overflow-x-auto max-h-40 mb-4">
            {error.message}
          </pre>
        )}
        <div className="flex justify-between items-center">
          <SadFace />
          <button
            onClick={resetErrorBoundary}
            className="px-4 py-2 bg-indigo-500 hover:bg-indigo-400 text-white font-bold rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorFallback;
