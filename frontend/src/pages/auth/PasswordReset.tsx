import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { requestPasswordReset } from '../../services/authService';
import { useMessage } from '../../contexts/MessageContext';

const PasswordReset = () => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { addMessage } = useMessage();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');
    setError('');

    try {
      const response = await requestPasswordReset(email);
      setMessage(response.message);
      addMessage({ tags: 'success', content: 'Please check your emails' });
    } catch (error) {
      const err = error as any;
      setError(err.message);
      addMessage({ tags: 'error', content: 'Failed to send the reset email.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
        Reset password
      </h2>
      <p className="mt-2 text-center text-sm text-gray-400 max-w">
        Or
        <Link to="/login" className="font-medium text-indigo-300 hover:text-indigo-200 ml-1">
          sign in here!
        </Link>
      </p>
  
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                maxLength={254}
                required
                className="form-fields"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
  
            {message && <div className="text-green-400">{message}</div>}
            {error && <div className="text-red-400">{error}</div>}
  
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-indigo-400 hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              {isLoading ? 'Sending...' : 'Request password reset'}
            </button>
          </form>
        </div>
      </div>
    </>
  );
  
};

export default PasswordReset;
