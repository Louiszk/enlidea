import React, { createContext, useState, useContext, useCallback } from 'react';
import { AlertMessage } from '../components/AlertMessage';

export interface MessageContextType {
  message: AlertMessage | null;
  addMessage: (newMessage: AlertMessage) => void;
  removeMessage: () => void;
}

const MessageContext = createContext<MessageContextType | undefined>(undefined);

export interface MessageProviderProps {
  children: React.ReactNode;
}

export const MessageProvider: React.FC<MessageProviderProps> = ({ children }) => {
  const [message, setMessage] = useState<AlertMessage | null>(null);

  const removeMessage = useCallback(() => {
    setMessage(null);
  }, []);

  const addMessage = useCallback((newMessage: AlertMessage) => {
    setMessage(newMessage);
    setTimeout(removeMessage, 3800);
  }, [removeMessage]);

  return (
    <MessageContext.Provider value={{ message, addMessage, removeMessage }}>
      {children}
    </MessageContext.Provider>
  );
};

export const useMessage = (): MessageContextType => {
  const context = useContext(MessageContext);
  if (context === undefined) {
    throw new Error('useMessage must be used within a MessageProvider');
  }
  return context;
};
