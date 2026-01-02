// Base API client with error handling
import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import type { ApiResponse, ApiError } from '../types/api';

// Use environment variables with fallback to Docker service names or localhost
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.DEV ? 'http://localhost:8000' : 'http://backend-mcp:8000');
const MOCK_SALESFORCE_URL = import.meta.env.VITE_MOCK_SALESFORCE_URL || 
  (import.meta.env.DEV ? 'http://localhost:8001' : 'http://mock-salesforce:8001');
const LANGGRAPH_URL = import.meta.env.VITE_LANGGRAPH_URL || 
  (import.meta.env.DEV ? 'http://localhost:8002' : 'http://backend-langgraph:8002');

// Create axios instances for different services
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes for long-running workflows
});

export const mockSalesforceClient: AxiosInstance = axios.create({
  baseURL: MOCK_SALESFORCE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

export const langgraphClient: AxiosInstance = axios.create({
  baseURL: LANGGRAPH_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes for OCR processing
});

// Error handler
export function handleApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ error?: ApiError; message?: string }>;
    
    if (axiosError.response) {
      // Server responded with error
      const errorData = axiosError.response.data;
      if (errorData?.error) {
        return errorData.error;
      }
      return {
        code: `HTTP_${axiosError.response.status}`,
        message: errorData?.message || axiosError.message || 'An error occurred',
        details: errorData,
      };
    } else if (axiosError.request) {
      // Request made but no response
      return {
        code: 'NETWORK_ERROR',
        message: 'No response from server. Please check your connection.',
      };
    }
  }
  
  // Unknown error
  return {
    code: 'UNKNOWN_ERROR',
    message: error instanceof Error ? error.message : 'An unknown error occurred',
  };
}

// Helper to extract data from API response
export function extractApiData<T>(response: ApiResponse<T>): T {
  if (response.status === 'error') {
    throw new Error(response.error?.message || 'API error');
  }
  if (!response.data) {
    throw new Error('No data in response');
  }
  return response.data;
}

