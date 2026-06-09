import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import authService from '../../services/authService';

const ActivateAccount = () => {
  const { uidb64, token } = useParams();
  const [activationStatus, setActivationStatus] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const activateAccount = async () => {
      try {
        setIsLoading(true);
        const result = await authService.activateAccount(uidb64, token);
        setActivationStatus(result.message);
        if (result.message === "Account activated successfully." || result.message.includes('already activated')) {
          setTimeout(() => navigate('/login'), 3000);
        }
      } catch (error) {
        setActivationStatus(error.message || 'Account activation failed. Please try again or contact support.');
      } finally {
        setIsLoading(false);
      }
    };

    activateAccount();
  }, [uidb64, token, navigate]);

  return (
    <>
      <div className="flex justify-center mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="inline-block align-bottom bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-sm sm:w-full sm:p-6" role="dialog" aria-modal="true" aria-labelledby="modal-headline">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-700">
            {isLoading ? (
              <svg className="h-6 w-6 text-gray-400 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v4m0 8v4m8-8h-4m-8 0H4" />
              </svg>
            ) : activationStatus.includes('successfully') || activationStatus.includes('already activated') ? (
              <svg className="h-6 w-6 text-green-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="h-6 w-6 text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
          </div>
          <div className="mt-3 text-center sm:mt-5">
            <h3 className="text-lg leading-6 font-medium text-white" id="modal-headline">
              {isLoading ? "Activating your account..." : activationStatus.includes('successfully') || activationStatus.includes('already activated') ? "Request completed" : "Request denied"}
            </h3>
            {!isLoading && (
              <div className="mt-2">
                <p className="text-sm text-gray-400">
                  {activationStatus.includes('successfully') ? "Your account has been activated :)" : (activationStatus.includes('already activated') ? "Your account is already activated :)": "The activation link is invalid or expired.")}
                </p>
              </div>
            )}
          </div>
          {!isLoading && (
            <div className="mt-5 sm:mt-6">
              <Link to="/login" className="inline-flex justify-center w-full rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-400 text-base font-medium text-white hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:text-sm">
                Go back to sign in
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
  
};

export default ActivateAccount;
