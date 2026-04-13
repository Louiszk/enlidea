import React, { createContext, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import authService from '../services/authService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const queryClient = useQueryClient();

  const { data: user, isLoading: isUserLoading } = useQuery({
    queryKey: ['user'],
    queryFn: authService.getCurrentUser,
    staleTime: Infinity,
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: ({ email, password }) => authService.login(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(['user'], data.user);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: authService.logout,
    onSuccess: () => {
      queryClient.setQueryData(['user'], null);
      queryClient.clear();
    },
  });

  const refreshUser = () => {
    queryClient.invalidateQueries({ queryKey: ['user'] });
  };

  const refreshFollows = (userId, isFollowing) => {
    queryClient.setQueryData(['user'], (oldUser) => {
      if (!oldUser) return null;
      const newFollows = isFollowing
        ? [...oldUser.follows, userId]
        : oldUser.follows.filter(id => id !== userId);
      return { ...oldUser, follows: newFollows };
    });
  };

  const refreshSaves = (nodeId) => {
    queryClient.setQueryData(['user'], (oldUser) => {
      if (!oldUser) return null;
      const isSaved = oldUser.saved_nodes?.includes(nodeId);
      const newSaves = isSaved
        ? oldUser.saved_nodes.filter(id => id !== nodeId)
        : [...(oldUser.saved_nodes || []), nodeId];
      return { ...oldUser, saved_nodes: newSaves };
    });
  };

  const refreshPaperSaves = (paperId) => {
    queryClient.setQueryData(['user'], (oldUser) => {
      if (!oldUser) return null;
      const isSaved = oldUser.saved_papers?.includes(paperId);
      const newSaves = isSaved
        ? oldUser.saved_papers.filter(id => id !== paperId)
        : [...(oldUser.saved_papers || []), paperId];
      return { ...oldUser, saved_papers: newSaves };
    });
  };

  const value = {
    user,
    loading: isUserLoading,
    login: loginMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    isLoginLoading: loginMutation.isPending,
    isLogoutLoading: logoutMutation.isPending,
    loginError: loginMutation.error,
    logoutError: logoutMutation.error,
    refreshUser,
    refreshFollows,
    refreshSaves,
    refreshPaperSaves,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;



