import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useMessage } from '../../contexts/MessageContext';
import { resendActivationEmail } from '../../services/authService';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isInactive, setIsInactive] = useState(false);
  const { login, isLoginLoading } = useAuth();
  const { addMessage } = useMessage();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ data: { email, password } });
      addMessage({ tags: 'success', content: 'Logged in successfully' });
      setTimeout(() => {
        navigate('/');
      }, 800);
    } catch (error) {
      const err = error as Error;
      if (err.message === "Your email has not been verified.") {
        setIsInactive(true);
      }
      addMessage({ tags: 'error', content: err.message || 'An error occurred. Please try again.' });
    }
  };

  const handleResendActivation = async () => {
    try {
      await resendActivationEmail(email);
      addMessage({ tags: 'success', content: 'Activation email resent.' });
      setTimeout(() => navigate('/activate-confirm'), 800);
    } catch (error) {
      const err = error as Error;
      addMessage({ tags: 'error', content: err.message });
    }
  };

  return (
    <>
      <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
        Sign in to your account
      </h2>
      <p className="mt-2 text-sm text-gray-400 w-full flex flex-row justify-center gap-1">
        Or
        <Link to="/register" className="font-medium text-indigo-300 hover:text-indigo-200">
          register here!
        </Link>
      </p>
  
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="text"
                maxLength={254}
                required
                className="form-fields"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setIsInactive(false);
                }}
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                maxLength={128}
                required
                className="form-fields"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="text-sm">
                <Link to="/password-reset" className="font-medium text-indigo-300 hover:text-indigo-200">
                  Forgot your password?
                </Link>
              </div>
            </div>
            <button
              type="submit"
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-indigo-400 hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              disabled={isLoginLoading}
            >
              {isLoginLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
          {isInactive && (
            <div className="mt-4">
              <p className="text-gray-300">Would you like to resend the activation email?</p>
              <button
                onClick={handleResendActivation}
                className="mt-2 w-1/2 flex justify-center py-1 px-2 border border-transparent rounded-md shadow-sm text-xs font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Resend activation email
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default Login;

