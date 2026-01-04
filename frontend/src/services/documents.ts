// Document API service
import { apiClient, handleApiError } from './api';
import type { ApiResponse } from '../types/api';

/**
 * Upload document
 */
export async function uploadDocument(
  recordId: string,
  file: File
): Promise<{ document_id: string; url: string; filename: string }> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('record_id', recordId);

    const response = await apiClient.post<ApiResponse<{ document_id: string; url: string; filename: string; size: number; content_type: string }>>(
      '/api/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    
    if (response.data.status === 'error') {
      throw new Error(response.data.error?.message || 'Upload failed');
    }
    
    const uploadResult = response.data.data!;
    
    // Add document to Mock Salesforce record
    try {
      const mockSalesforceUrl = import.meta.env.VITE_MOCK_SALESFORCE_URL || 
        (import.meta.env.DEV ? 'http://localhost:8001' : 'http://mock-salesforce:8001');
      
      const addResponse = await fetch(`${mockSalesforceUrl}/mock/salesforce/add-document`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          record_id: recordId,
          document_url: uploadResult.url,
          document_name: file.name,
          document_type: file.type || 'application/pdf'
        })
      });
      
      if (!addResponse.ok) {
        const errorData = await addResponse.json().catch(() => ({ error: { message: 'Unknown error' } }));
        throw new Error(errorData.error?.message || `HTTP ${addResponse.status}: ${addResponse.statusText}`);
      }
      
      const addResult = await addResponse.json();
      console.log('[uploadDocument] Document added to Mock Salesforce record:', addResult);
    } catch (addError: any) {
      console.error('[uploadDocument] Failed to add document to Mock Salesforce:', {
        error: addError,
        message: addError?.message,
        recordId,
        documentUrl: uploadResult.url,
        documentName: file.name
      });
      // Don't fail the upload if adding to Mock Salesforce fails, but log the error
      // The document is already uploaded to backend-mcp and copied to test-data
    }
    
    return {
      document_id: uploadResult.document_id,
      url: uploadResult.url,
      filename: uploadResult.filename
    };
  } catch (error) {
    const apiError = handleApiError(error);
    throw new Error(apiError.message);
  }
}

