import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { API_BASE_URL } from '../services/apiClient';

const MarkdownRenderer = ({ content }: { content: string }) => {
  const urlTransform = (uri: string) => {
    // If it's an internal Docker URL or points to our API base, convert it to a relative path
    // e.g., http://backend:8000/media/... -> /media/...
    try {
      const url = new URL(uri);
      const apiBase = new URL(API_BASE_URL);
      if (url.host === apiBase.host || url.host === 'backend:8000') {
        return url.pathname;
      }
    } catch (_e) {
      // Fallback for malformed URLs or when API_BASE_URL lacks a protocol
      if (uri.includes('backend:8000') || (API_BASE_URL && uri.includes(API_BASE_URL.replace(/^https?:\/\//, '')))) {
        return uri.replace(/^https?:\/\/[^/]+/, '');
      }
    }
    const normalizedUri = uri.trim();

    // Return as-is if it's already an absolute external URL, data URI, mailto, or tel
    if (normalizedUri.startsWith('http://') || normalizedUri.startsWith('https://') || normalizedUri.startsWith('data:') || normalizedUri.startsWith('mailto:') || normalizedUri.startsWith('tel:')) {
      return normalizedUri;
    }

    // Block any other URI that has a protocol/scheme (to prevent javascript:, vbscript:, etc.)
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(normalizedUri)) {
      return "";
    }

    // Relative paths without a scheme are returned as-is
    return normalizedUri;
  };

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      urlTransform={urlTransform}
    >
      {content}
    </ReactMarkdown>
  );
};

export default MarkdownRenderer;
