import React, { createContext, useContext } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Account,
  LoginRequestRequest,
  LoginResponse,
  LogoutResponse,
  useAuthApiCurrentUserRetrieve,
  useAuthApiLoginCreate,
  useAuthApiLogoutCreate,
  getAuthApiCurrentUserRetrieveQueryKey,
} from '../api/generated/api';

export interface AppAccount extends Account {
  saved_papers?: number[];
}

export interface AuthContextType {
  user: AppAccount | null | undefined;
  loading: boolean;
  login: (variables: { data: LoginRequestRequest }) => Promise<LoginResponse>;
  logout: (variables: void) => Promise<LogoutResponse>;
  isLoginLoading: boolean;
  isLogoutLoading: boolean;
  loginError: Error | null;
  logoutError: Error | null;
  refreshUser: () => void;
  refreshFollows: (userId: number, isFollowing: boolean) => void;
  refreshSaves: (nodeId: number) => void;
  refreshPaperSaves: (paperId: number) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const queryClient = useQueryClient();

  const { data: user, isLoading: isUserLoading } = useAuthApiCurrentUserRetrieve({
    query: {
      staleTime: Infinity,
      retry: false,
    }
  });

  const loginMutation = useAuthApiLoginCreate({
    mutation: {
      onSuccess: (data) => {
        queryClient.setQueryData(getAuthApiCurrentUserRetrieveQueryKey(), data.user);
      },
    },
  });

  const logoutMutation = useAuthApiLogoutCreate({
    mutation: {
      onSuccess: () => {
        queryClient.setQueryData(getAuthApiCurrentUserRetrieveQueryKey(), null);
        queryClient.clear();
      },
    },
  });

  const refreshUser = () => {
    queryClient.invalidateQueries({ queryKey: getAuthApiCurrentUserRetrieveQueryKey() });
  };

  const refreshFollows = (userId: number, isFollowing: boolean) => {
    queryClient.setQueryData<AppAccount>(getAuthApiCurrentUserRetrieveQueryKey(), (oldUser) => {
      if (!oldUser) return undefined;
      const newFollows = isFollowing
        ? [...oldUser.follows, userId]
        : oldUser.follows.filter(id => id !== userId);
      return { ...oldUser, follows: newFollows };
    });
  };

  const refreshSaves = (nodeId: number) => {
    queryClient.setQueryData<AppAccount>(getAuthApiCurrentUserRetrieveQueryKey(), (oldUser) => {
      if (!oldUser) return undefined;
      const isSaved = oldUser.saved_nodes?.includes(nodeId);
      const newSaves = isSaved
        ? oldUser.saved_nodes!.filter(id => id !== nodeId)
        : [...(oldUser.saved_nodes || []), nodeId];
      return { ...oldUser, saved_nodes: newSaves };
    });
  };

  const refreshPaperSaves = (paperId: number) => {
    queryClient.setQueryData<AppAccount>(getAuthApiCurrentUserRetrieveQueryKey(), (oldUser) => {
      if (!oldUser) return undefined;
      const isSaved = oldUser.saved_papers?.includes(paperId);
      const newSaves = isSaved
        ? oldUser.saved_papers!.filter(id => id !== paperId)
        : [...(oldUser.saved_papers || []), paperId];
      return { ...oldUser, saved_papers: newSaves };
    });
  };

  const value: AuthContextType = {
    user: user as AppAccount | undefined,
    loading: isUserLoading,
    login: loginMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    isLoginLoading: loginMutation.isPending,
    isLogoutLoading: logoutMutation.isPending,
    loginError: loginMutation.error as unknown as Error | null,
    logoutError: logoutMutation.error as unknown as Error | null,
    refreshUser,
    refreshFollows,
    refreshSaves,
    refreshPaperSaves,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;



