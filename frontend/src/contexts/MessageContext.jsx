import React, { createContext, useState, useContext } from 'react';

const MessageContext = createContext();

export const MessageProvider = ({ children }) => {
  const [message, setMessage] = useState(null);

  const addMessage = (newMessage) => {
    setMessage(newMessage);
    setTimeout(removeMessage, 3800);
  };

  const removeMessage = () => {
    setMessage(null);
  };

  return (
    <MessageContext.Provider value={{ message, addMessage, removeMessage }}>
      {children}
    </MessageContext.Provider>
  );
};

export const useMessage = () => useContext(MessageContext);
