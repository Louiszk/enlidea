import { apiClient } from './apiClient';

export const fetchCapabilitySearch = async (query) => {
  try {
    const response = await apiClient.get('/v1/capabilities/search/', { params: { q: query } });
    return response.data;
  } catch (error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchKeywords = async (query) => {
  try {
    const response = await apiClient.get('/v1/keywords/search/', { params: { q: query } });
    return response.data;
  } catch (error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchCapabilities = async (parent = null) => {
  try {
    const params = parent ? { parent } : {};
    const response = await apiClient.get('/v1/capabilities/', { params });
    return response.data;
  } catch (error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchPapers = async (page = 1, filters = null, saved = false) => {
  try {
    const params = { page };
    if (filters) {
      params.filters = JSON.stringify(filters);
    }
    if (saved) {
      params.saved = true;
    }
    const response = await apiClient.get('/v1/papers/', { params });
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch papers');
  }
};

export const fetchPaperDetail = async (id) => {
  try {
    const response = await apiClient.get(`/v1/papers/${id}/`);
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch paper detail');
  }
};

export const fetchCapabilityNodes = async (capabilitySlug, page, sortBy, filterString) => {
  try {
    const response = await apiClient.get('/v1/nodes/', {
      params: { page, sort: sortBy, capability: capabilitySlug, filters: filterString }
    });
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 404) {
      throw error.response.data;
    }
    throw new Error('Failed to fetch capability nodes');
  }
};

export const fetchNodeDetail = async (id) => {
  try {
    const response = await apiClient.get(`/v1/nodes/${id}/`);
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 404) {
      throw new Error('Maybe the node was deleted?');
    } else if (error.response && error.response.status === 403) {
      throw new Error(error.response.data.detail || 'You do not have permission to view this node');
    }
    throw new Error('An error occurred while fetching the node detail');
  }
};

export const fetchNodeBody = async (id) => {
  try {
    const response = await apiClient.get(`/v1/nodes/${id}/`);
    return response.data.body;
  } catch (error) {
    if (error.response && (error.response.status === 403 || error.response.status === 401)) {
      throw new Error('You do not have permission to view this node content.');
    }
    throw new Error('An error occurred while fetching the node content');
  }
};

export const fetchUserProfile = async (userId) => {
  try {
    const response = await apiClient.get(`/dashboard/user/${userId}/`);
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 404) {
      throw new Error(error.response.data.message || error.response.data.detail);
    }
    throw new Error('Failed to fetch Maintainer Profile');
  }
};

export const fetchSavedNodes = async (userId, isSaved, page = 1, sortBy, searchTerm) => {
  try {
    const params = { sort: sortBy, search: searchTerm, page };
    if (isSaved) {
      params.saved = true;
    } else {
      params.maintainer = userId;
    }
    const response = await apiClient.get('/v1/nodes/', { params });
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 404) {
      throw new Error(error.response.data.message || error.response.data.detail);
    }
    throw new Error('Failed to fetch Research Nodes');
  }
};

export const fetchTrendingData = async () => {
  try {
    const response = await apiClient.get('/dashboard/trending/');
    return response.data;
  } catch (error) {
    console.error('Error fetching trending data:', error);
    throw error;
  }
};

export const fetchHighImpactData = async () => {
  try {
    const response = await apiClient.get('/dashboard/high-impact/');
    return response.data;
  } catch (error) {
    console.error('Error fetching high-impact research data:', error);
    throw error;
  }
};

export const fetchSuggestions = async (query) => {
  try {
    const response = await apiClient.get('/v1/suggestions/', { params: { q: query } });
    return response.data;
  } catch (error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchSearchResults = async (query, page = 1) => {
  try {
    const response = await apiClient.get('/v1/search/', { params: { q: query, page } });
    return response.data;
  } catch (error) {
    throw new Error('Network response was not ok');
  }
};

export const fetchAgents = async () => {
  try {
    const response = await apiClient.get('/v1/agents/');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch agents');
  }
};

export const fetchActiveAssignments = async (page = 1, sortBy, searchTerm) => {
  try {
    const response = await apiClient.get('/v1/nodes/active/', {
      params: { page, sort: sortBy, search: searchTerm }
    });
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 404) {
      return { nodes: [] };
    }
    if (error.response && error.response.data && error.response.data.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to fetch Active Assignments');
  }
};

export const fetchDirectives = async () => {
  try {
    const response = await apiClient.get('/v1/directives/');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch directives');
  }
};

export const fetchPendingReviews = async () => {
  try {
    const response = await apiClient.get('/v1/reviews/');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch review offers');
  }
};

export const checkAgentName = async (name) => {
  try {
    const response = await apiClient.get('/v1/agents/check_name/', { params: { name } });
    return response.data;
  } catch (error) {
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
