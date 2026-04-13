import { apiClient } from './apiClient';

export const deletePost = async (id) => {
  try {
    await apiClient.delete(`/v1/nodes/${id}/`);
  } catch (error) {
    throw error;
  }
};

export const rotateAgentApiKey = async (agentId) => {
  try {
    const response = await apiClient.post(`/v1/agents/${agentId}/rotate_api_key/`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const deployAgent = async (agentData) => {
  try {
    const response = await apiClient.post('/v1/agents/', agentData);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const updateAgent = async (id, agentData) => {
  try {
    const response = await apiClient.patch(`/v1/agents/${id}/`, agentData);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const createDirective = async (payload) => {
  try {
    const response = await apiClient.post('/v1/directives/', payload);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const deleteDirective = async (id) => {
  try {
    const response = await apiClient.delete(`/v1/directives/${id}/`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const respondToReview = async ({ id, action }) => {
  try {
    const response = await apiClient.post(`/v1/reviews/${id}/respond/`, { action });
    return response.data;
  } catch (error) {
    throw error;
  }
};