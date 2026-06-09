import { baseApiClient } from '../../services/apiClient';

export const customInstance = async (config) => {
  const response = await baseApiClient(config);
  return response.data;
};

export default customInstance;
