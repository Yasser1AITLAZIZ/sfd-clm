// Service Diagnostic Page
import { ServiceHealthDashboard } from '../components/common/ServiceHealthDashboard';
import { ServiceDebugLogs } from '../components/common/ServiceDebugLogs';

export function ServiceDiagnosticPage() {
  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 bg-clip-text text-transparent mb-2">
              Service Diagnostic
            </h1>
            <p className="text-gray-600 text-lg">Monitor service health and debug logs</p>
          </div>
        </div>
      </div>

      {/* Service Health Status */}
      <ServiceHealthDashboard />

      {/* Service Debug Logs */}
      <ServiceDebugLogs />
    </div>
  );
}

