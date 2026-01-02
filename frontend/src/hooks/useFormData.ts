// Form data fetching hook
import { useQuery } from '@tanstack/react-query';
import { getRecordData } from '../services/mockSalesforce';
import type { MockSalesforceResponse } from '../types/form';

export function useFormData(recordId: string, enabled: boolean = true) {
  return useQuery<MockSalesforceResponse, Error>({
    queryKey: ['formData', recordId],
    queryFn: () => getRecordData(recordId),
    enabled: enabled && !!recordId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

