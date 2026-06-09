import React from 'react';
import { useMessage } from '../../contexts/MessageContext';
import Messages from '../../components/AlertMessage';
import logo from '../../assets/images/logo-enlidea.png';
import { Link } from 'react-router-dom';

const BaseAuth = ({ children, showLogo = true }: { children: React.ReactNode; showLogo?: boolean }) => {
  const { message, removeMessage } = useMessage();

  return (
    <div className="min-h-screen auth-bg flex flex-col justify-center items-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full">
        {message && (
          <Messages 
            message={message}
            onClose={removeMessage}
          />
        )}
      </div>
         
        {showLogo && <Link to={"/"} ><img className="mx-auto h-12 w-auto" src={logo} alt="Enlidea Logo" /></Link>}
        <main className="flex-grow flex flex-col justify-center items-center min-w-full">
          {children}
        </main>
          
      </div>
  );
};

export default BaseAuth;

