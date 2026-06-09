import { socialApiClient as apiClient } from './apiClient';
import {
  AppreciatePaperResponse,
  SaveNodeResponse,
  SavePaperResponse,
  FollowUserResponse,
  UnfollowUserResponse,
  HomeFeedResponse,
  Follow,
  Notification,
  LeaderboardResponse,
  ReportContentRequestRequest,
  ReportContentCreatedResponse,
  SubmitComplaintRequestRequest,
  SubmitComplaintCreatedResponse,
} from '../api/generated/api';

export const appreciatePaper = async (paperId: number | string, vote: number): Promise<AppreciatePaperResponse> => {
  try {
    const response = await apiClient.post<AppreciatePaperResponse>(`/papers/${paperId}/appreciate/`, { vote });
    return response.data;
  } catch (error) {
    console.error('Error appreciating paper:', error);
    throw error;
  }
};

export const saveNode = async (nodeId: number | string): Promise<SaveNodeResponse> => {
  try {
    const response = await apiClient.post<SaveNodeResponse>(`/nodes/${nodeId}/save/`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const savePaper = async (paperId: number | string): Promise<SavePaperResponse> => {
  try {
    const response = await apiClient.post<SavePaperResponse>(`/papers/${paperId}/save/`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const followUser = async (userId: number | string): Promise<FollowUserResponse> => {
  try {
    const response = await apiClient.post<FollowUserResponse>(`/follow/${userId}/`);
    return response.data;
  } catch (error) {
    console.error('Error following user:', error);
    throw error;
  }
};

export const unfollowUser = async (userId: number | string): Promise<UnfollowUserResponse> => {
  try {
    const response = await apiClient.post<UnfollowUserResponse>(`/unfollow/${userId}/`);
    return response.data;
  } catch (error) {
    console.error('Error unfollowing user:', error);
    throw error;
  }
};

export const getHomeFeed = async (userId: string = '0', page: number = 1): Promise<HomeFeedResponse> => {
  try {
    const response = await apiClient.get<HomeFeedResponse>(`/home-feed/${userId}`, { params: { page } });
    return response.data;
  } catch (error) {
    console.error('Error fetching home feed:', error);
    throw error;
  }
};

export const getFollows = async (): Promise<Follow[]> => {
  try {
    const response = await apiClient.get<Follow[]>('/follows/');
    return response.data;
  } catch (error) {
    console.error('Error fetching follows:', error);
    throw error;
  }
};

export const getNotifications = async (): Promise<Notification[]> => {
  try {
    const response = await apiClient.get<Notification[]>('/notifications/');
    return response.data;
  } catch (error) {
    console.error('Error fetching notifications:', error);
    throw error;
  }
};

export const markNotificationsAsRead = async (): Promise<void> => {
  try {
    await apiClient.post('/notifications/mark-read/');
  } catch (error) {
    console.error('Error marking notifications as read:', error);
    throw error;
  }
};

export const fetchLeaderboard = async (page: number = 1): Promise<LeaderboardResponse> => {
  try {
    const response = await apiClient.get<LeaderboardResponse>('/leaderboard', { params: { page } });
    return response.data;
  } catch (error) {
    console.error('Error fetching leaderboard:', error);
    throw error;
  }
};

export const submitReport = async (reportData: ReportContentRequestRequest): Promise<ReportContentCreatedResponse> => {
  try {
    const response = await apiClient.post<ReportContentCreatedResponse>('/report/', reportData);
    return response.data;
  } catch (error) {
    console.error('Error submitting report:', error);
    throw error;
  }
};

export const submitComplaint = async (complaintData: SubmitComplaintRequestRequest): Promise<SubmitComplaintCreatedResponse> => {
  try {
    const response = await apiClient.post<SubmitComplaintCreatedResponse>('/complaint/', complaintData);
    return response.data;
  } catch (error) {
    console.error('Error submitting complaint:', error);
    throw error;
  }
};
