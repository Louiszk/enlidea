import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDebounce } from 'use-debounce';
import { register, checkUsernameAvailability } from '../../services/authService';
import { useMessage } from '../../contexts/MessageContext';


const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password1: '',
    password2: '',
  });
  const [message, setMessage] = useState('');
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingUsername, setIsCheckingUsername] = useState(false);
  const [usernameStatus, setUsernameStatus] = useState(null);
  const [usernameMessage, setUsernameMessage] = useState('');

  const [debouncedUsername] = useDebounce(formData.username, 500);

  const navigate = useNavigate();
  const { addMessage } = useMessage();

  useEffect(() => {
    if (!debouncedUsername) {
      setUsernameStatus(null);
      setUsernameMessage('');
      return;
    }

    let isActive = true;
    setIsCheckingUsername(true);

    checkUsernameAvailability(debouncedUsername)
      .then(data => {
        if (isActive) {
          if (!data.is_valid) {
            setUsernameStatus('invalid');
            setUsernameMessage(data.message);
          } else if (data.is_taken) {
            setUsernameStatus('taken');
            setUsernameMessage(data.message);
          } else {
            setUsernameStatus('available');
            setUsernameMessage(data.message);
          }
        }
      })
      .catch(err => {
        if (isActive) {
          console.error('Error checking username:', err);
          setUsernameStatus('invalid');
          setUsernameMessage(err.message || 'Error checking username');
        }
      })
      .finally(() => {
        if (isActive) setIsCheckingUsername(false);
      });

    return () => {
      isActive = false;
    };
  }, [debouncedUsername]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (usernameStatus === 'taken' || usernameStatus === 'invalid') {
      setErrors({ username: usernameMessage });
      return;
    }

    setIsLoading(true);
    setMessage('');
    setErrors({});

    try {
      const response = await register(formData);
      setMessage('Sign up successful!');
      addMessage({ tags: 'success', content: 'Welcome to Enlidea :)' });
      setTimeout(() => navigate('/activate-confirm'), 800);
    } catch (err) {
      const errorMessage = err.message;
      // Split the error message into field-specific errors
      const errorPairs = errorMessage.split('; ');
      const newErrors = {};
      errorPairs.forEach(pair => {
        const [field, message] = pair.split(': ');
        newErrors[field] = message;
      });
      setErrors(newErrors);
      addMessage({ tags: 'error', content: 'Registration Failed.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
        Register an account
      </h2>
      <p className="mt-2 text-center text-sm text-gray-400">
        Or
        <Link to="/login" className="font-medium text-indigo-300 hover:text-indigo-200 ml-1">
          sign in here!
        </Link>
      </p>
  
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="w-full max-w-xs mx-auto">
              <label htmlFor="username" className="block text-sm font-medium text-gray-300">
                Username
              </label>
              <div className="relative">
                <input
                  id="username"
                  name="username"
                  type="text"
                  maxLength={30}
                  required
                  className={`form-fields ${
                    (usernameStatus === 'taken' || usernameStatus === 'invalid') ? 'border-red-500' : 
                    usernameStatus === 'available' ? 'border-green-500' : ''
                  }`}
                  value={formData.username}
                  onChange={handleChange}
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  {isCheckingUsername && (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-400"></div>
                  )}
                  {!isCheckingUsername && usernameStatus === 'available' && (
                    <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  )}
                  {!isCheckingUsername && (usernameStatus === 'taken' || usernameStatus === 'invalid') && (
                    <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              </div>
              <div className="h-10 mt-1 leading-tight">
                {usernameStatus && (
                  <div className={`text-sm ${usernameStatus === 'available' ? 'text-green-400' : 'text-red-400'}`}>
                    {usernameMessage}
                  </div>
                )}
                {errors.username && !usernameStatus && <div className="text-red-400 text-sm">{errors.username}</div>}
              </div>
            </div>
  
            <div className="w-full max-w-xs mx-auto">
              <label htmlFor="email" className="block text-sm font-medium text-gray-300">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                maxLength={254}
                required
                className="form-fields"
                value={formData.email}
                onChange={handleChange}
              />
              <div className="h-5 mt-1">
                {errors.email && <div className="text-red-400 text-sm">{errors.email}</div>}
              </div>
            </div>
  
            <div className="w-full max-w-xs mx-auto">
              <label htmlFor="password1" className="block text-sm font-medium text-gray-300">
                Password
              </label>
              <input
                id="password1"
                name="password1"
                type="password"
                maxLength={128}
                required
                className="form-fields"
                value={formData.password1}
                onChange={handleChange}
              />
              <div className="h-5 mt-1">
                {errors.password1 && <div className="text-red-400 text-sm">{errors.password1}</div>}
              </div>
            </div>
  
            <div className="w-full max-w-xs mx-auto">
              <label htmlFor="password2" className="block text-sm font-medium text-gray-300">
                Confirm Password
              </label>
              <input
                id="password2"
                name="password2"
                type="password"
                maxLength={128}
                required
                className="form-fields"
                value={formData.password2}
                onChange={handleChange}
              />
              <div className="h-5 mt-1">
                {errors.password2 && <div className="text-red-400 text-sm">{errors.password2}</div>}
              </div>
            </div>
  
            <div className="w-full max-w-xs mx-auto h-5 py-2 font-semibold">
              {message && <div className="text-green-400">{message}</div>}
              {errors.non_field_errors && <div className="text-red-400">{errors.non_field_errors}</div>}
            </div>
  
            <div className="w-full max-w-xs mx-auto">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-indigo-400 hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                {isLoading ? 'Signing up...' : 'Sign up'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
  
  
};

export default Register;
