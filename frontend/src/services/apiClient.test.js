import { describe, it, expect, vi } from 'vitest';
import { getMediaUrl, API_BASE_URL } from './apiClient';

describe('apiClient utilities', () => {
  describe('getMediaUrl', () => {
    it('should return null if no path is provided', () => {
      expect(getMediaUrl(null)).toBeNull();
      expect(getMediaUrl(undefined)).toBeNull();
      expect(getMediaUrl('')).toBeNull();
    });

    it('should return the path as-is if it starts with http', () => {
      const fullUrl = 'https://example.com/image.jpg';
      expect(getMediaUrl(fullUrl)).toBe(fullUrl);
    });

    it('should prepend API_BASE_URL to relative paths', () => {
      const path = '/media/avatar.png';
      // Use exported API_BASE_URL
      expect(getMediaUrl(path)).toBe(`${API_BASE_URL}${path}`);
    });
  });
});
