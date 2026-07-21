import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../test/setup';
import { renderWithProviders } from '../test/test-utils';
import HomeFeed from './HomeFeed';
import { API_BASE_URL } from '../services/apiClient';

// Define MSW handlers for this specific test
const handlers = [
  http.get(`${API_BASE_URL}/social-api/follows/`, () => {
    return HttpResponse.json([
      { id: 2, username: 'creator1', avatar: null }
    ]);
  }),
  http.get(`${API_BASE_URL}/social-api/home-feed/0`, () => {
    return HttpResponse.json({
      nodes: [
        { 
          id: 101, 
          title: 'Quantum Computing Research', 
          description: 'Exploring qubit stability...',
          status: 'open',
          type: 'Standard',
          bounty_amount: 500,
          required_collaborators: 3,
          total_assigned: 1,
          required_capabilities: ['Quantum Computing'],
          keywords: [{ name: 'physics' }]
        }
      ],
      nextPage: null
    });
  }),
];

describe('HomeFeed Integration', () => {
  it('renders the feed with data from the API', async () => {
    server.use(...handlers);

    renderWithProviders(<HomeFeed />);

    // Check for the header
    expect(screen.getByText(/Research Feed/i)).toBeInTheDocument();

    // Wait for the data to appear
    await waitFor(() => {
      expect(screen.getByText('Quantum Computing Research')).toBeInTheDocument();
    });

    expect(screen.getByText(/Exploring qubit stability/i)).toBeInTheDocument();
    
    // Check for follow buttons (creators)
    expect(screen.getByText('creator1')).toBeInTheDocument();
    expect(screen.getByText('Global')).toBeInTheDocument();
    expect(screen.getByText('Following')).toBeInTheDocument();
  });

  it('shows empty state when no nodes are found and no follows exist', async () => {
    server.use(
      http.get(`${API_BASE_URL}/social-api/home-feed/0`, () => {
        return HttpResponse.json({ nodes: [], nextPage: null });
      }),
      http.get(`${API_BASE_URL}/social-api/follows/`, () => {
        return HttpResponse.json([]);
      })
    );

    renderWithProviders(<HomeFeed />);

    await waitFor(() => {
      expect(screen.getByText(/You aren't following anyone yet/i)).toBeInTheDocument();
    });
  });

  it('shows empty state when no nodes are found for existing follows', async () => {
    server.use(
      http.get(`${API_BASE_URL}/social-api/home-feed/0`, () => {
        return HttpResponse.json({ nodes: [], nextPage: null });
      }),
      http.get(`${API_BASE_URL}/social-api/follows/`, () => {
        return HttpResponse.json([{ id: 2, username: 'creator1', avatar: null }]);
      })
    );

    renderWithProviders(<HomeFeed />);

    await waitFor(() => {
      expect(screen.getByText(/No updates found/i)).toBeInTheDocument();
    });
  });
});
