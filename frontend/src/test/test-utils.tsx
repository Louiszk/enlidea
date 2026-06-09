import React from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AuthContext, { AuthContextType } from '../contexts/AuthContext';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

export function renderWithProviders(
  ui: React.ReactElement,
  {
    route = '/',
    authValue = {
      user: {
        id: 1,
        username: 'testuser',
        follows: [],
        date_joined: '',
        last_login: '',
        is_active: true,
        balance_blue_stars: '0.00',
        balance_orange_stars: '0.00',
        agents: [],
      },
      loading: false,
    } as unknown as AuthContextType,
    ...renderOptions
  }: {
    route?: string;
    authValue?: AuthContextType;
    [key: string]: any;
  } = {}
) {
  const testQueryClient = createTestQueryClient();

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={testQueryClient}>
        <AuthContext.Provider value={authValue}>
          <MemoryRouter initialEntries={[route]}>
            {children}
          </MemoryRouter>
        </AuthContext.Provider>
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient: testQueryClient,
  };
}
