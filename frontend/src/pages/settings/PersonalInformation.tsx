import React, { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import settingsService from '../../services/settingsService';
import { useAuth } from'../../contexts/AuthContext'; 
import { useMessage } from '../../contexts/MessageContext';
import { Spinner } from '../../components/Icons';

const PersonalInformation = () => {
  const queryClient = useQueryClient();
  const { user, loading, refreshUser } = useAuth();
  const { addMessage } = useMessage();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    newPassword: '',
    currentPassword: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (user) {
      setFormData(prevData => ({
        ...prevData,
        username: user.username || '',
        email: user.email || ''
      }));
    }
  }, [user]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const result = await settingsService.updatePersonalInfo(
        {
          username: formData.username,
          email: formData.email,
          new_password: formData.newPassword
        },
        formData.currentPassword
      );
      setSuccess(result.message || 'Personal information updated successfully');
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: ['profile', user.id] });
      }
      setTimeout(refreshUser, 4000);
    } catch (error) {
      const err = error as any;
      setError(err.message || 'An error occurred while updating personal information');
      addMessage({
        tags: 'error',
        content: typeof err.error === 'object' && err.error !== null 
          ? Object.values(err.error)[0] || 'Something went wrong :(' 
          : err.error || 'Something went wrong :('
      });
    }
  };

  if (loading) {
    return <Spinner />;
  }

  return (
    <div className="max-w-2xl mx-auto p-6 bg-gray-800 rounded-lg shadow-md w-full">
      <h2 className="text-2xl font-semibold mb-6 text-white">Personal Information</h2>
      {error && <div className="mb-4 p-3 bg-red-900 text-red-300 font-semibold rounded">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-900 text-green-300 font-semibold rounded">{success}</div>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-1">
            Username:
          </label>
          <input
            type="text"
            id="username"
            name="username"
            maxLength={30}
            value={formData.username}
            onChange={handleChange}
            className="form-fields"
          />
        </div>
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
            Email Address:
          </label>
          <input
            type="email"
            id="email"
            name="email"
            maxLength={254}
            value={formData.email}
            onChange={handleChange}
            className="form-fields"
          />
        </div>
        <div>
          <label htmlFor="newPassword" className="block text-sm font-medium text-gray-300 mb-1">
            New Password <span className="text-xs text-gray-400">(optional)</span>:
          </label>
          <input
            type="password"
            id="newPassword"
            name="newPassword"
            maxLength={128}
            value={formData.newPassword}
            onChange={handleChange}
            className="form-fields"
          />
        </div>
        <div>
          <label htmlFor="currentPassword" className="block text-sm font-medium text-gray-300 mb-1">
            Current Password:
          </label>
          <input
            type="password"
            id="currentPassword"
            name="currentPassword"
            maxLength={128}
            value={formData.currentPassword}
            onChange={handleChange}
            required
            className="form-fields"
          />
        </div>
        <div className='flex justify-center'>
          <button
            type="submit"
            className="max-w-content bg-indigo-400 text-white font-semibold py-2 px-4 rounded-md hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 transition duration-200"
          >
            Save Changes
          </button>
        </div>
      </form>
    </div>
  );
  
};

export default PersonalInformation;
