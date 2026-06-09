import type { AxiosRequestConfig } from 'axios';
import { baseApiClient } from '../../services/apiClient';

export const customInstance = async <T>(
  config: AxiosRequestConfig,
): Promise<T> => {
  const response = await baseApiClient.request<T>(config);
  return response.data;
};

export default customInstance;
