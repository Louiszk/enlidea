import React from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AuthContext from '../contexts/AuthContext';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

export function renderWithProviders(
  ui,
  {
    route = '/',
    authValue = { user: { id: 1, username: 'testuser', follows: [] }, loading: false },
    ...renderOptions
  } = {}
) {
  const testQueryClient = createTestQueryClient();

  function Wrapper({ children }) {
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
