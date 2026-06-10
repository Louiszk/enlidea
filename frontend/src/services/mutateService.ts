import { apiClient } from './apiClient';
import {
  Agent,
  AgentRequest,
  PatchedAgentRequest,
  AgentDirective,
  AgentDirectiveRequest,
  PeerReviewStatusEnum,
  PeerReview,
} from '../api/generated/api';

export const deletePost = async (id: number): Promise<void> => {
  try {
    await apiClient.delete(`/v1/nodes/${id}/`);
  } catch (error) {
    throw error;
  }
};

export const rotateAgentApiKey = async (agentId: number): Promise<Agent & { api_key: string }> => {
  try {
    const response = await apiClient.post<Agent & { api_key: string }>(`/v1/agents/${agentId}/rotate_api_key/`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const deployAgent = async (agentData: AgentRequest): Promise<Agent & { api_key: string }> => {
  try {
    const response = await apiClient.post<Agent & { api_key: string }>('/v1/agents/', agentData);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const updateAgent = async (id: number, agentData: PatchedAgentRequest): Promise<Agent> => {
  try {
    const response = await apiClient.patch<Agent>(`/v1/agents/${id}/`, agentData);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const createDirective = async (payload: AgentDirectiveRequest): Promise<AgentDirective> => {
  try {
    const response = await apiClient.post<AgentDirective>('/v1/directives/', payload);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const deleteDirective = async (id: number): Promise<void> => {
  try {
    await apiClient.delete(`/v1/directives/${id}/`);
  } catch (error) {
    throw error;
  }
};

export const respondToReview = async ({ id, action }: { id: number; action: PeerReviewStatusEnum }): Promise<PeerReview> => {
  try {
    const response = await apiClient.post(`/v1/reviews/${id}/respond/`, { action });
    return response.data;
  } catch (error) {
    throw error;
  }
};