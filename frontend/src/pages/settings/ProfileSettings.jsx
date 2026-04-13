import React, { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import settingsService from '../../services/settingsService';
import { useAuth } from '../../contexts/AuthContext';
import { useMessage } from '../../contexts/MessageContext';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '../../components/Icons';
import { getMediaUrl } from '../../services/apiClient';

const ProfileSettings = () => {
  const queryClient = useQueryClient();
  const { user, loading, refreshUser } = useAuth();
  const { addMessage } = useMessage();
  const [formData, setFormData] = useState({
    avatar: null,
    biography: '',
  });
  const [previewUrl, setPreviewUrl] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      setFormData(prevData => ({
        ...prevData,
        biography: user.biography || '',
      }));
      setPreviewUrl(getMediaUrl(user.avatar));
    }
  }, [user]);

  const handleChange = (e) => {
    if (e.target.name === 'avatar') {
      const file = e.target.files[0];
      setFormData({ ...formData, avatar: file });
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setFormData({ ...formData, [e.target.name]: e.target.value });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (formData.biography.length > 2000) {
        setError('Biography must be under 2000 characters.');
        return;
    }

    if (formData.avatar && formData.avatar.size > 60 * 1024) {
        setError('Avatar must be under 60KB.');
        return;
    }

    const data = new FormData();
    data.append('biography', formData.biography);
    if (formData.avatar) {
        data.append('avatar', formData.avatar);
    }

    try {
        const result = await settingsService.updateProfileInfo(data);
        setSuccess(result.message || 'Profile information updated successfully');
        addMessage({
            tags: 'success',
            content: 'Profile updated successfully. Redirecting...'
        });
        refreshUser();
        queryClient.invalidateQueries({ queryKey: ['profile', user.id] });
        setTimeout(() => navigate(`/user/${user.id}`), 4000);
    } catch (err) {
        setError(err.message || 'An error occurred while updating profile information');
        addMessage({
            tags: 'error',
            content: typeof err === 'object' && err !== null 
                ? Object.values(err)[0] || 'Something went wrong :(' 
                : err || 'Something went wrong :('
        });
    }
};

  if (loading) {
    return <Spinner />;
  }

  return (
    <div className="max-w-2xl mx-auto p-6 bg-gray-800 rounded-lg shadow-md w-full flex flex-col gap-4">
      <h2 className="text-2xl font-semibold mb-2 text-white">Profile Settings</h2>
      <h3 className='text-xl font-semibold text-gray-200'> @{user.username} </h3>
      {error && <div className="mb-4 p-3 bg-red-900 text-red-300 font-semibold rounded">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-900 text-green-300 font-semibold rounded">{success}</div>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="avatar" className="block text-sm font-medium text-gray-200 mb-1">
            Profile Picture:
          </label>
          <div className="flex items-center space-x-4">
            <img
              src={previewUrl || '/default-account.svg'}
              alt="Profile"
              className="w-20 h-20 rounded-full object-cover"
            />
            <input
              type="file"
              id="avatar"
              name="avatar"
              onChange={handleChange}
              accept="image/*"
              className="cursor-pointer w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-400 file:text-indigo-50 hover:file:bg-indigo-300"
            />
          </div>
        </div>
        <div>
          <label htmlFor="biography" className="block text-sm font-medium text-gray-300 mb-1">
            Biography:
          </label>
          <textarea
            id="biography"
            name="biography"
            value={formData.biography}
            onChange={handleChange}
            rows="4"
            maxLength={2000}
            className="form-fields"
          ></textarea>
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

export default ProfileSettings;
