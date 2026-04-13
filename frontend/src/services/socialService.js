import { socialApiClient as apiClient } from './apiClient';

export const appreciatePaper = async (paperId, vote) => {
  try {
    const response = await apiClient.post(`/papers/${paperId}/appreciate/`, { vote });
    return response.data;
  } catch (error) {
    console.error('Error appreciating paper:', error);
    throw error;
  }
};

export const saveNode = async (nodeId) => {
  try {
    const response = await apiClient.post(`/nodes/${nodeId}/save/`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const savePaper = async (paperId) => {
  try {
    const response = await apiClient.post(`/papers/${paperId}/save/`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const followUser = async (userId) => {
  try {
    const response = await apiClient.post(`/follow/${userId}/`);
    return response.data;
  } catch (error) {
    console.error('Error following user:', error);
    throw error;
  }
};

export const unfollowUser = async (userId) => {
  try {
    const response = await apiClient.post(`/unfollow/${userId}/`);
    return response.data;
  } catch (error) {
    console.error('Error unfollowing user:', error);
    throw error;
  }
};

export const getHomeFeed = async (userId = '0', page = 1) => {
  try {
    const response = await apiClient.get(`/home-feed/${userId}`, { params: { page } });
    return response.data;
  } catch (error) {
    console.error('Error fetching home feed:', error);
    throw error;
  }
};

export const getFollows = async () => {
  try {
    const response = await apiClient.get('/follows/');
    return response.data;
  } catch (error) {
    console.error('Error fetching follows:', error);
    throw error;
  }
};

export const getNotifications = async () => {
  try {
    const response = await apiClient.get('/notifications/');
    return response.data;
  } catch (error) {
    console.error('Error fetching notifications:', error);
    throw error;
  }
};

export const markNotificationsAsRead = async () => {
  try {
    await apiClient.post('/notifications/mark-read/');
  } catch (error) {
    console.error('Error marking notifications as read:', error);
    throw error;
  }
};

export const fetchLeaderboard = async (page = 1) => {
  try {
    const response = await apiClient.get('/leaderboard', { params: { page } });
    return response.data;
  } catch (error) {
    console.error('Error fetching leaderboard:', error);
    throw error;
  }
};

export const submitReport = async (reportData) => {
  try {
    const response = await apiClient.post('/report/', reportData);
    return response.data;
  } catch (error) {
    console.error('Error submitting report:', error);
    throw error;
  }
};

export const submitComplaint = async (complaintData) => {
  try {
    const response = await apiClient.post('/complaint/', complaintData);
    return response.data;
  } catch (error) {
    console.error('Error submitting complaint:', error);
    throw error;
  }
};
