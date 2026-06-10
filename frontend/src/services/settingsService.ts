
import { authApiClient as apiClient } from './apiClient';

export interface PersonalInfoData {
  email?: string;
  username?: string;
  new_password?: string;
}

const settingsService = {
  updatePersonalInfo: async (data: PersonalInfoData, currentPassword: string) => {
    const response = await apiClient.put('settings/personal-info/', {
      ...data,
      current_password: currentPassword
    });
    return response.data;
  },

  verifyEmail: async (uidb64: string, token: string, signedEmail: string) => {
    const response = await apiClient.get(`settings/verify-email/${uidb64}/${token}/${signedEmail}/`);
    return response.data;
  },

  deleteAccount: async (password: string) => {
    const response = await apiClient.delete('settings/delete-account/', {
      data: { password }
    });
    return response.data;
  },

  updateProfileInfo: async (data: FormData) => {
    const response = await apiClient.post('settings/profile/', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default settingsService;

