// Detailed service health dashboard component
import { useServiceHealth } from '../../hooks/useServiceHealth';
import { LoadingSpinner } from './LoadingSpinner';
import type { ServiceHealth } from '../../services/health';

export function ServiceHealthDashboard() {
  const { data: services, isLoading, error } = useServiceHealth();

  if (isLoading) {
    return (
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" />
          <span className="ml-3 text-gray-600">Checking service health...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-red-200/50">
        <div className="flex items-center text-red-700">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span className="font-semibold">Error checking service health</span>
        </div>
      </div>
    );
  }

  if (!services || services.length === 0) {
    return null;
  }

  const allHealthy = services.every(s => s.status === 'healthy');
  const unhealthyCount = services.filter(s => s.status === 'unhealthy').length;

  return (
    <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900 flex items-center">
          <svg className="w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Service Health Status
        </h2>
        <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
          allHealthy
            ? 'bg-green-100 text-green-800'
            : 'bg-red-100 text-red-800'
        }`}>
          {allHealthy ? 'All Healthy' : `${unhealthyCount} Service${unhealthyCount > 1 ? 's' : ''} Down`}
        </div>
      </div>

      <div className="space-y-3">
        {services.map((service, index) => (
          <ServiceHealthCard key={index} service={service} />
        ))}
      </div>
    </div>
  );
}

function ServiceHealthCard({ service }: { service: ServiceHealth }) {
  const statusColors = {
    healthy: 'bg-green-50 border-green-200 text-green-800',
    unhealthy: 'bg-red-50 border-red-200 text-red-800',
    checking: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  };

  const statusIcons = {
    healthy: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    unhealthy: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
    checking: (
      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
      </svg>
    ),
  };

  return (
    <div className={`border-2 rounded-xl p-4 ${statusColors[service.status]}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            {statusIcons[service.status]}
          </div>
          <div>
            <h3 className="font-semibold text-sm">{service.service}</h3>
            <p className="text-xs opacity-75 mt-0.5">{service.url}</p>
          </div>
        </div>
        <div className="text-right">
          {service.responseTime !== undefined && (
            <div className="text-xs font-medium">
              {service.responseTime}ms
            </div>
          )}
          {service.lastChecked && (
            <div className="text-xs opacity-75 mt-1">
              {new Date(service.lastChecked).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>
      {service.error && (
        <div className="mt-2 pt-2 border-t border-current/20">
          <p className="text-xs font-medium">{service.error}</p>
        </div>
      )}
    </div>
  );
}

