// Service health polling hook
import { useQuery } from '@tanstack/react-query';
import { checkAllServicesHealth, type ServiceHealth } from '../services/health';

export function useServiceHealth(enabled: boolean = true) {
  return useQuery<ServiceHealth[], Error>({
    queryKey: ['serviceHealth'],
    queryFn: checkAllServicesHealth,
    enabled,
    refetchInterval: 10000, // Poll every 10 seconds
    staleTime: 5000, // Consider data stale after 5 seconds
  });
}

