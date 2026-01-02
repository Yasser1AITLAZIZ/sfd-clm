// Compact service health status component for header
import { useServiceHealth } from '../../hooks/useServiceHealth';
import type { ServiceHealth } from '../../services/health';

interface ServiceHealthStatusProps {
  compact?: boolean;
}

export function ServiceHealthStatus({ compact = true }: ServiceHealthStatusProps) {
  const { data: services, isLoading } = useServiceHealth();

  if (isLoading || !services) {
    return (
      <div className="flex items-center space-x-2">
        <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" title="Checking services..." />
        <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
        <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
      </div>
    );
  }

  if (compact) {
    return (
      <div className="flex items-center space-x-2" title={getTooltipText(services)}>
        {services.map((service, index) => (
          <div
            key={index}
            className={`w-2.5 h-2.5 rounded-full ${
              service.status === 'healthy'
                ? 'bg-green-500'
                : service.status === 'unhealthy'
                ? 'bg-red-500'
                : 'bg-yellow-500'
            }`}
            title={`${service.service}: ${service.status}`}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-3">
      {services.map((service, index) => (
        <div
          key={index}
          className="flex items-center space-x-2"
          title={`${service.service}: ${service.status}${service.responseTime ? ` (${service.responseTime}ms)` : ''}`}
        >
          <div
            className={`w-3 h-3 rounded-full ${
              service.status === 'healthy'
                ? 'bg-green-500'
                : service.status === 'unhealthy'
                ? 'bg-red-500'
                : 'bg-yellow-500'
            }`}
          />
          <span className="text-xs text-gray-600 hidden sm:inline">{service.service}</span>
        </div>
      ))}
    </div>
  );
}

function getTooltipText(services: ServiceHealth[]): string {
  const statuses = services.map(s => `${s.service}: ${s.status}`).join(', ');
  const allHealthy = services.every(s => s.status === 'healthy');
  return allHealthy ? `All services healthy - ${statuses}` : `Service status - ${statuses}`;
}

