import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { confirmPasswordReset } from '../../services/authService';
import { useMessage } from '../../contexts/MessageContext';

const PasswordResetConfirm = () => {
  const [newPassword1, setNewPassword1] = useState('');
  const [newPassword2, setNewPassword2] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isValidLink, setIsValidLink] = useState(true);
  const { addMessage } = useMessage();

  const { uid, token } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    if (!uid || !token) {
      setIsValidLink(false);
    }
  }, [uid, token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');
    setError('');

    if (newPassword1 !== newPassword2) {
      setError("Passwords don't match.");
      setIsLoading(false);
      return;
    }

    try {
      const response = await confirmPasswordReset(uid, token, newPassword1, newPassword2);
      setMessage(response.message);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err) {
      setError(err.message);
      if (err.message === 'Invalid reset link.') {
        setIsValidLink(false);
      } else {
        addMessage({ tags: 'error', content: 'Failed to reset your password. Try again later or contact our support.' });
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!isValidLink) {
    return (
      <>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
          Invalid Reset Link
        </h2>
        <p className="mt-2 text-center text-sm text-gray-400">
          The password reset link is invalid or has expired.
          <Link to="/password-reset" className="font-medium text-indigo-300 hover:text-indigo-200 ml-1">
            Request a new one here.
          </Link>
        </p>
      </>
    );
  }
  
  return (
    <>
      <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
        Update your password
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
              <label htmlFor="new_password1" className="block text-sm font-medium text-gray-300">
                New Password
              </label>
              <input
                id="new_password1"
                name="new_password1"
                type="password"
                maxLength={128}
                required
                className="form-fields"
                value={newPassword1}
                onChange={(e) => setNewPassword1(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="new_password2" className="block text-sm font-medium text-gray-300">
                Confirm New Password
              </label>
              <input
                id="new_password2"
                name="new_password2"
                type="password"
                maxLength={128}
                required
                className="form-fields"
                value={newPassword2}
                onChange={(e) => setNewPassword2(e.target.value)}
              />
            </div>
  
            {message && <div className="text-green-400">{message}</div>}
            {error && <div className="text-red-400">{error}</div>}
  
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-indigo-400 hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              {isLoading ? 'Resetting...' : 'Reset password'}
            </button>
          </form>
        </div>
      </div>
    </>
  );
  
};

export default PasswordResetConfirm;
