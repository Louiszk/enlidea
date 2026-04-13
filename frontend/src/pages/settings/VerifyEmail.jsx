import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import settingsService from '../../services/settingsService';
import { Spinner } from '../../components/Icons';

const VerifyEmail = () => {
  const { uidb64, token, signedEmail } = useParams();
  const [status, setStatus] = useState('verifying');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      try {
        const data = await settingsService.verifyEmail(uidb64, token, signedEmail);
        setStatus('success');
        setMessage(data.message || 'Your email has been successfully changed.');
      } catch (error) {
        setStatus('error');
        setMessage('An error occurred while verifying your email.');
      }
    };

    verifyEmail();
  }, [uidb64, token, signedEmail]);

  const renderContent = () => {
    switch (status) {
      case 'verifying':
        return <Spinner />;
      case 'success':
        return (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Success!</strong>
            <span className="block sm:inline"> {message}</span>
          </div>
        );
      case 'error':
        return (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Error!</strong>
            <span className="block sm:inline"> {message}</span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-xl">
      <h2 className="text-2xl font-bold mb-4">Email Verification</h2>
      {renderContent()}
    </div>
  );
};

export default VerifyEmail;
