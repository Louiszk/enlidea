import { authApiClient as apiClient } from './apiClient';

const settingsService = {
  updatePersonalInfo: async (data, currentPassword) => {
    try {
      const response = await apiClient.put('settings/personal-info/', {
        ...data,
        current_password: currentPassword
      });
      return response.data;
    } catch (error) {
      throw error.response ? error.response.data : new Error('Failed to update personal info');
    }
  },

  verifyEmail: async (uidb64, token, signedEmail) => {
    try {
      const response = await apiClient.get(`settings/verify-email/${uidb64}/${token}/${signedEmail}/`);
      return response.data;
    } catch (error) {
      throw error.response ? error.response.data : new Error('Failed to verify email');
    }
  },

  deleteAccount: async (password) => {
    try {
      const response = await apiClient.delete('settings/delete-account/', {
        data: { password }
      });
      return response.data;
    } catch (error) {
      throw error.response ? error.response.data : new Error('Failed to delete account');
    }
  },

  updateProfileInfo: async (data) => {
    try {
      const response = await apiClient.post('settings/profile/', data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      throw error.response ? error.response.data : new Error('Failed to update profile info');
    }
  },
};

export default settingsService;

