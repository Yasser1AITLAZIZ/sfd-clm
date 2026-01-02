// Health check API service
import { apiClient, mockSalesforceClient, langgraphClient, handleApiError } from './api';

export interface ServiceHealth {
  service: string;
  status: 'healthy' | 'unhealthy' | 'checking';
  responseTime?: number;
  lastChecked?: string;
  error?: string;
  url: string;
}

export interface HealthCheckResponse {
  status: string;
  service?: string;
}

/**
 * Check health of Backend MCP service
 */
export async function checkBackendMCPHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  const url = import.meta.env.VITE_API_BASE_URL || 
    (import.meta.env.DEV ? 'http://localhost:8000' : 'http://backend-mcp:8000');
  
  try {
    const response = await apiClient.get<HealthCheckResponse>('/health', {
      timeout: 5000,
    });
    const responseTime = Date.now() - startTime;
    
    // Check if response has status 'ok' or if it's a successful response
    const isHealthy = response.data?.status === 'ok' || response.status === 200;
    
    return {
      service: 'Backend MCP',
      status: isHealthy ? 'healthy' : 'unhealthy',
      responseTime,
      lastChecked: new Date().toISOString(),
      url,
    };
  } catch (error) {
    const responseTime = Date.now() - startTime;
    const apiError = handleApiError(error);
    
    console.warn('Backend MCP health check failed:', apiError.message);
    
    return {
      service: 'Backend MCP',
      status: 'unhealthy',
      responseTime,
      lastChecked: new Date().toISOString(),
      error: apiError.message,
      url,
    };
  }
}

/**
 * Check health of Backend LangGraph service
 */
export async function checkBackendLangGraphHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  const url = import.meta.env.VITE_LANGGRAPH_URL || 
    (import.meta.env.DEV ? 'http://localhost:8002' : 'http://backend-langgraph:8002');
  
  try {
    const response = await langgraphClient.get<HealthCheckResponse>('/health', {
      timeout: 5000,
    });
    const responseTime = Date.now() - startTime;
    
    // Check if response has status 'ok' or if it's a successful response
    const isHealthy = response.data?.status === 'ok' || response.status === 200;
    
    return {
      service: 'Backend LangGraph',
      status: isHealthy ? 'healthy' : 'unhealthy',
      responseTime,
      lastChecked: new Date().toISOString(),
      url,
    };
  } catch (error) {
    const responseTime = Date.now() - startTime;
    const apiError = handleApiError(error);
    
    console.warn('Backend LangGraph health check failed:', apiError.message);
    
    return {
      service: 'Backend LangGraph',
      status: 'unhealthy',
      responseTime,
      lastChecked: new Date().toISOString(),
      error: apiError.message,
      url,
    };
  }
}

/**
 * Check health of Mock Salesforce service
 */
export async function checkMockSalesforceHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  const url = import.meta.env.VITE_MOCK_SALESFORCE_URL || 
    (import.meta.env.DEV ? 'http://localhost:8001' : 'http://mock-salesforce:8001');
  
  try {
    const response = await mockSalesforceClient.get<HealthCheckResponse>('/health', {
      timeout: 5000,
    });
    const responseTime = Date.now() - startTime;
    
    // Check if response has status 'ok' or if it's a successful response
    const isHealthy = response.data?.status === 'ok' || response.status === 200;
    
    return {
      service: 'Mock Salesforce',
      status: isHealthy ? 'healthy' : 'unhealthy',
      responseTime,
      lastChecked: new Date().toISOString(),
      url,
    };
  } catch (error) {
    const responseTime = Date.now() - startTime;
    const apiError = handleApiError(error);
    
    console.warn('Mock Salesforce health check failed:', apiError.message);
    
    return {
      service: 'Mock Salesforce',
      status: 'unhealthy',
      responseTime,
      lastChecked: new Date().toISOString(),
      error: apiError.message,
      url,
    };
  }
}

/**
 * Check health of all services
 */
export async function checkAllServicesHealth(): Promise<ServiceHealth[]> {
  const [mcp, langgraph, salesforce] = await Promise.allSettled([
    checkBackendMCPHealth(),
    checkBackendLangGraphHealth(),
    checkMockSalesforceHealth(),
  ]);

  return [
    mcp.status === 'fulfilled' ? mcp.value : {
      service: 'Backend MCP',
      status: 'unhealthy' as const,
      error: mcp.reason?.message || 'Unknown error',
      url: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    },
    langgraph.status === 'fulfilled' ? langgraph.value : {
      service: 'Backend LangGraph',
      status: 'unhealthy' as const,
      error: langgraph.reason?.message || 'Unknown error',
      url: import.meta.env.VITE_LANGGRAPH_URL || 'http://localhost:8002',
    },
    salesforce.status === 'fulfilled' ? salesforce.value : {
      service: 'Mock Salesforce',
      status: 'unhealthy' as const,
      error: salesforce.reason?.message || 'Unknown error',
      url: import.meta.env.VITE_MOCK_SALESFORCE_URL || 'http://localhost:8001',
    },
  ];
}

