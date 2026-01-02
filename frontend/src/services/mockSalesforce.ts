// Mock Salesforce API service
import { mockSalesforceClient, handleApiError, extractApiData } from './api';
import type { MockSalesforceResponse } from '../types/form';
import type { ApiResponse } from '../types/api';

/**
 * Get record data from mock Salesforce
 * POST /mock/salesforce/get-record-data
 */
export async function getRecordData(recordId: string): Promise<MockSalesforceResponse> {
  try {
    const response = await mockSalesforceClient.post<ApiResponse<MockSalesforceResponse>>(
      '/mock/salesforce/get-record-data',
      { record_id: recordId }
    );
    return extractApiData(response.data);
  } catch (error) {
    const apiError = handleApiError(error);
    throw new Error(apiError.message);
  }
}

