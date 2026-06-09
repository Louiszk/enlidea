// AccountDeletion.jsx
import React, { useState } from 'react';
import settingsService from '../../services/settingsService';
import { useAuth } from '../../contexts/AuthContext';
import { useMessage } from '../../contexts/MessageContext';

const AccountDeletion = () => {
  const { logout } = useAuth();
  const { addMessage } = useMessage();
  const [showForm, setShowForm] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleToggleForm = () => {
    setShowForm(!showForm);
    setError('');
    setPassword('');
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      await settingsService.deleteAccount(password);
      addMessage({
        tags: 'success',
        content: 'Your account has been successfully deleted.'
      });
      logout();
    } catch (error) {
      const err = error as any;
      setError(err.message || 'An error occurred while deleting the account');
      addMessage({
        tags: 'error',
        content: typeof err.error === 'object' && err.error !== null 
          ? Object.values(err.error)[0] || 'Something went wrong :(' 
          : err.error || 'Something went wrong :('
      });
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-gray-800 rounded-lg shadow-md w-full">
      <h2 className="text-2xl font-semibold mb-6 text-white">Account Deletion</h2>
      {error && <div className="mb-4 p-3 bg-red-100 text-red-700 font-semibold rounded">{error}</div>}
      <div className='flex justify-center'>
        <button
            onClick={handleToggleForm}
            className="max-w-content bg-red-500 text-white font-semibold py-2 px-4 rounded-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 transition duration-200"
        >
            Permanently Delete Account
        </button>
      </div>
      {showForm && (
        <form onSubmit={handleDeleteAccount} className="mt-4 space-y-4">
          <div className='flex flex-col gap-2 text-zinc-200 font-semibold'>
            <span>Are you sure? This action will delete all your posts too.</span>
            <label htmlFor="password" className="block text-sm mb-1">
              Confirm your password:
            </label>
            <input
              type="password"
              id="password"
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="form-fields"
            />
          </div>
          <div className='flex justify-center'>
            <button
                type="submit"
                className="max-w-content bg-red-500 text-white font-semibold py-2 px-4 rounded-md hover:bg-red-400 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 transition duration-200"
            >
                Confirm Deletion
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default AccountDeletion;
