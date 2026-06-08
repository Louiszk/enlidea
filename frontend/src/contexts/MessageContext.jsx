import React, { createContext, useState, useContext, useCallback } from 'react';

const MessageContext = createContext();

export const MessageProvider = ({ children }) => {
  const [message, setMessage] = useState(null);

  const removeMessage = useCallback(() => {
    setMessage(null);
  }, []);

  const addMessage = useCallback((newMessage) => {
    setMessage(newMessage);
    setTimeout(removeMessage, 3800);
  }, [removeMessage]);

  return (
    <MessageContext.Provider value={{ message, addMessage, removeMessage }}>
      {children}
    </MessageContext.Provider>
  );
};

export const useMessage = () => useContext(MessageContext);
