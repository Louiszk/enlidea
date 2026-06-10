import axios from 'axios';
import { apiClient } from './apiClient';
import {
  Capability,
  ResearchKeyword,
  Paper,
  PaperListResponse,
  ResearchNode,
  ResearchNodeListResponse,
  Agent,
  AgentDirective,
  PeerReview,
  CheckAgentNameResponse,
  SearchResultItem,
  TrendingResponse,
  HighImpactCategory,
} from '../api/generated/api';
import { UserProfile } from '../types';
import { Suggestion } from '../components/Search';

export const fetchCapabilitySearch = async (query: string): Promise<Capability[]> => {
  try {
    const response = await apiClient.get<Capability[]>('/v1/capabilities/search/', { params: { q: query } });
    return response.data;
  } catch (_error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchKeywords = async (query: string): Promise<ResearchKeyword[]> => {
  try {
    const response = await apiClient.get<ResearchKeyword[]>('/v1/keywords/search/', { params: { q: query } });
    return response.data;
  } catch (_error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchCapabilities = async (parent: number | string | null = null): Promise<Capability[]> => {
  try {
    const params = parent ? { parent } : {};
    const response = await apiClient.get<Capability[]>('/v1/capabilities/', { params });
    return response.data;
  } catch (_error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchPapers = async (page: number = 1, filters: Record<string, unknown> | null = null, saved: boolean = false): Promise<PaperListResponse> => {
  try {
    const params: { page: number; filters?: string; saved?: boolean } = { page };
    if (filters) {
      params.filters = JSON.stringify(filters);
    }
    if (saved) {
      params.saved = true;
    }
    const response = await apiClient.get<PaperListResponse>('/v1/papers/', { params });
    return response.data;
  } catch (_error) {
    throw new Error('Failed to fetch papers');
  }
};

export const fetchPaperDetail = async (id: number | string): Promise<Paper> => {
  try {
    const response = await apiClient.get<Paper>(`/v1/papers/${id}/`);
    return response.data;
  } catch (_error) {
    throw new Error('Failed to fetch paper detail');
  }
};

export const fetchCapabilityNodes = async (capabilitySlug: string, page: number, sortBy: string, filterString?: string): Promise<ResearchNodeListResponse> => {
  try {
    const response = await apiClient.get<ResearchNodeListResponse>('/v1/nodes/', {
      params: { page, sort: sortBy, capability: capabilitySlug, filters: filterString }
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
      throw error.response.data;
    }
    throw new Error('Failed to fetch capability nodes');
  }
};

export const fetchNodeDetail = async (id: number | string): Promise<ResearchNode> => {
  try {
    const response = await apiClient.get<ResearchNode>(`/v1/nodes/${id}/`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
      throw new Error('Maybe the node was deleted?');
    } else if (axios.isAxiosError(error) && error.response && error.response.status === 403) {
      throw new Error(error.response.data.detail || 'You do not have permission to view this node');
    }
    throw new Error('An error occurred while fetching the node detail');
  }
};

export const fetchNodeBody = async (id: number | string): Promise<string> => {
  try {
    const response = await apiClient.get<ResearchNode>(`/v1/nodes/${id}/`);
    return response.data.body;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && (error.response.status === 403 || error.response.status === 401)) {
      throw new Error('You do not have permission to view this node content.');
    }
    throw new Error('An error occurred while fetching the node content');
  }
};

export const fetchUserProfile = async (userId: number | string): Promise<UserProfile> => {
  try {
    const response = await apiClient.get(`/dashboard/user/${userId}/`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
      throw new Error(error.response.data.message || error.response.data.detail);
    }
    throw new Error('Failed to fetch Maintainer Profile');
  }
};

export const fetchSavedNodes = async (userId: number | string | undefined, isSaved: boolean, page: number = 1, sortBy?: string, searchTerm?: string): Promise<ResearchNodeListResponse> => {
  try {
    const params: { sort?: string; search?: string; page: number; saved?: boolean; maintainer?: number | string } = { sort: sortBy, search: searchTerm, page };
    if (isSaved) {
      params.saved = true;
    } else if (userId !== undefined) {
      params.maintainer = userId;
    }
    const response = await apiClient.get<ResearchNodeListResponse>('/v1/nodes/', { params });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
      throw new Error(error.response.data.message || error.response.data.detail);
    }
    throw new Error('Failed to fetch Research Nodes');
  }
};

export const fetchTrendingData = async (): Promise<TrendingResponse> => {
  try {
    const response = await apiClient.get<TrendingResponse>('/dashboard/trending/');
    return response.data;
  } catch (error) {
    console.error('Error fetching trending data:', error);
    throw error;
  }
};

export const fetchHighImpactData = async (): Promise<HighImpactCategory[]> => {
  try {
    const response = await apiClient.get<HighImpactCategory[]>('/dashboard/high-impact/');
    return response.data;
  } catch (error) {
    console.error('Error fetching high-impact research data:', error);
    throw error;
  }
};

export const fetchSuggestions = async (query: string): Promise<Suggestion[]> => {
  try {
    const response = await apiClient.get('/v1/suggestions/', { params: { q: query } });
    return response.data;
  } catch (_error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchSearchResults = async (query: string | null, page: number = 1): Promise<SearchResultItem[]> => {
  try {
    const response = await apiClient.get<SearchResultItem[]>('/v1/search/', { params: { q: query, page } });
    return response.data;
  } catch (_error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchAgents = async (): Promise<Agent[]> => {
  try {
    const response = await apiClient.get<Agent[]>('/v1/agents/');
    return response.data;
  } catch (_error) {
    throw new Error('Failed to fetch agents');
  }
};

export const fetchActiveAssignments = async (page: number = 1, sortBy?: string, searchTerm?: string): Promise<ResearchNodeListResponse> => {
  try {
    const response = await apiClient.get<ResearchNodeListResponse>('/v1/nodes/active/', {
      params: { page, sort: sortBy, search: searchTerm }
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
      return { nodes: [], total_pages: 1 } as unknown as ResearchNodeListResponse;
    }
    if (axios.isAxiosError(error) && error.response && error.response.data && error.response.data.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to fetch Active Assignments');
  }
};

export const fetchDirectives = async (): Promise<AgentDirective[]> => {
  try {
    const response = await apiClient.get<AgentDirective[]>('/v1/directives/');
    return response.data;
  } catch (_error) {
    throw new Error('Failed to fetch directives');
  }
};

export const fetchPendingReviews = async (): Promise<PeerReview[]> => {
  try {
    const response = await apiClient.get<PeerReview[]>('/v1/reviews/');
    return response.data;
  } catch (_error) {
    throw new Error('Failed to fetch review offers');
  }
};

export const checkAgentName = async (name: string): Promise<CheckAgentNameResponse> => {
  try {
    const response = await apiClient.get<CheckAgentNameResponse>('/v1/agents/check_name/', { params: { name } });
    return response.data;
  } catch (_error) {
    throw new Error('Failed to check agent name availability');
  }
};

export default {
  fetchCapabilitySearch,
  fetchCapabilities,
  fetchCapabilityNodes,
  fetchNodeDetail,
  fetchNodeBody,
  fetchUserProfile,
  fetchSavedNodes,
  fetchTrendingData,
  fetchHighImpactData,
  fetchSuggestions,
  fetchSearchResults,
  fetchAgents,
  fetchActiveAssignments,
  fetchDirectives,
  checkAgentName,
};
