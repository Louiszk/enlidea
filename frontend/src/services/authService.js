import { authApiClient } from './apiClient';

let isRefreshing = false;
let refreshPromise = null;

const authService = {
  login: async (email, password) => {
    try {
      const response = await authApiClient.post('/login/', { email, password });
      return { user: response.data.user };
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Login failed');
    }
  },

  logout: async () => {
    try {
      await authApiClient.post('/logout/');
    } catch (error) {
      console.error('Logout failed', error);
    }
    isRefreshing = false;
    refreshPromise = null;
  },

  refreshToken: async () => {
    if (isRefreshing) {
      return refreshPromise;
    }

    isRefreshing = true;
    refreshPromise = (async () => {
      try {
        const response = await authApiClient.post('/token-refresh/');
        return response.data;
      } catch (error) {
        throw new Error('Failed to refresh token');
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  },

  getCurrentUser: async (retry = true) => {
    try {
      const response = await authApiClient.get('/current-user/');
      return response.data;
    } catch (error) {
      if (error.response && error.response.status === 401 && retry) {
        try {
          await authService.refreshToken();
          return authService.getCurrentUser(false);
        } catch (refreshError) {
          throw new Error('Session expired');
        }
      }
      throw new Error(error.response?.data?.detail || error.response?.data?.error || 'Failed to get current user');
    }
  },

  activateAccount: async (uidb64, token) => {
    try {
      const response = await authApiClient.get(`/activate/${uidb64}/${token}/`);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Activation failed');
    }
  },
};

export const requestPasswordReset = async (email) => {
  try {
    const response = await authApiClient.post('/password-reset/', { email });
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 429) {
      throw new Error('Please wait 10 minutes before requesting another reset.');
    }
    throw new Error(error.response?.data?.error || 'An error occurred while requesting password reset.');
  }
};

export const confirmPasswordReset = async (uidb64, token, new_password1, new_password2) => {
  try {
    const response = await authApiClient.post(`/password-reset-confirm/${uidb64}/${token}/`, {
      new_password1,
      new_password2,
    });
    return response.data;
  } catch (error) {
    const errorData = error.response?.data;
    throw new Error(errorData?.error || errorData?.new_password1 || 'An error occurred while resetting the password.');
  }
};

export const register = async (userData) => {
  try {
    const response = await authApiClient.post('/register/', userData);
    return response.data;
  } catch (error) {
    const data = error.response?.data;
    if (typeof data === 'object' && data !== null) {
      const errorMessages = Object.entries(data)
        .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
        .join('; ');
      throw new Error(errorMessages);
    }
    throw new Error(data?.error || 'Registration failed');
  }
};

export const checkUsernameAvailability = async (username) => {
  try {
    const response = await authApiClient.get(`/check-username/?username=${encodeURIComponent(username)}`);
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 429) {
      throw new Error('Rate limit reached. Please wait a moment.');
    }
    throw new Error(error.response?.data?.error || 'Failed to check username availability');
  }
};

export const resendActivationEmail = async (email) => {
  try {
    const response = await authApiClient.post('/resend-activation/', { email });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to resend activation email');
  }
};

export default authService;
