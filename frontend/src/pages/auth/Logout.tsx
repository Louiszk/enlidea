import React, { useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useMessage } from '../../contexts/MessageContext';
import { Link } from 'react-router-dom';
import { SadFace, Spinner } from '../../components/Icons';

const Logout = () => {
  const { logout, isLogoutLoading, logoutError } = useAuth();
  const { addMessage } = useMessage();

  useEffect(() => {
    const performLogout = async () => {
      try{
      await logout();
        addMessage({ content: 'Success!', tags: 'success' });
      } catch (error) {
        addMessage({ content: 'An error occurred during logout.', tags: 'error' });
      }};

    performLogout();
  }, [logout, addMessage]);

  if (isLogoutLoading) return <Spinner />
  if (logoutError) return <div className='bg-gray-800 h-96 flex items-center justify-center'><SadFace /></div>

  return (
    <>
      <div className="inline-block align-bottom bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-sm sm:w-full sm:p-6" role="dialog" aria-modal="true" aria-labelledby="modal-headline">
        <div>
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-900">
            <svg className="h-6 w-6 text-green-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div className="mt-3 text-center sm:mt-5">
            <h3 className="text-lg leading-6 font-medium text-white" id="modal-headline">
              Logged out
            </h3>
            <div className="mt-2">
              <p className="text-sm text-gray-400">
                Your account has been logged out.
              </p>
              <p className="text-sm text-gray-400 mt-2">
                Hope you'll be back soon!
              </p>
            </div>
          </div>
        </div>
        <div className="mt-5 sm:mt-6">
          <Link to="/login" className="inline-flex justify-center w-full rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-400 text-base font-semibold text-white hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-300 sm:text-sm">
            Sign In again
          </Link>
        </div>
        <div className="mt-5 sm:mt-6">
          <Link to="/" className="inline-flex justify-center w-full rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-400 text-base font-semibold text-white hover:bg-indigo-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-300 sm:text-sm">
            Go to the home page
          </Link>
        </div>
      </div>
    </>
  ); 
};

export default Logout;

