import React, { useState, useEffect } from 'react';

const MessageAlert = ({ message, onClose }) => {
  const [show, setShow] = useState(true);

  useEffect(() => {
    if (!show) {
      setTimeout(() => onClose(), 400);
    }
  }, [show, onClose]);


  const getIcon = () => {
    switch (message.tags) {
      case 'success':
        return (
          <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'error':
        return (
          <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      default:
        return (
          <svg className="h-6 w-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  if (!message) return null;

  const getBgColor = () => {
    switch (message.tags) {
      case 'success':
        return 'bg-green-50';
      case 'warning':
        return 'bg-yellow-50';
      case 'error':
        return 'bg-red-50';
      default:
        return 'bg-gray-50';
    }
  };

  const getTextColor = () => {
    switch (message.tags) {
      case 'success':
        return 'text-green-900';
      case 'warning':
        return 'text-yellow-900';
      case 'error':
        return 'text-red-900';
      default:
        return 'text-gray-900';
    }
  };

  return (
    <div
      className={`message-alert ${getBgColor()} rounded-lg shadow-lg overflow-hidden transform transition-all mb-4 hover:scale-105 ${show ? 'opacity-100 scale-100' : 'opacity-0 scale-90'}`}
      role="alert"
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {getIcon()}
          </div>
          <div className="ml-3 w-0 flex-1 pt-0.5">
            <p className={`text-sm font-medium ${getTextColor()}`}>
              {message.content}
            </p>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={() => setShow(false)}
              className={`bg-transparent cursor-pointer rounded-md inline-flex focus:outline-none focus:ring-2 focus:ring-offset-2`}
            >
              <span className="sr-only">Close</span>
              <svg className="h-5 w-5 text-zinc-300" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Messages = ({ message, onClose }) => {
 
  return (
    <div className="fixed top-4 right-4 z-50 max-w-52 sm:max-w-sm w-full">
      <MessageAlert 
        message={message} 
        onClose={onClose} 
      />
    </div>
  );
};

export default Messages;