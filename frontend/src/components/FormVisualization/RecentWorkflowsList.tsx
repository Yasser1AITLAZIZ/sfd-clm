// Recent Workflows List Component - Scrollable dropdown to select and load a workflow
import { useState, useEffect } from 'react';
import { getRecentWorkflows } from '../../services/workflow';
import { LoadingSpinner } from '../common/LoadingSpinner';

interface RecentWorkflowsListProps {
  onSelectWorkflow: (workflowId: string) => void;
  currentWorkflowId: string | null;
}

export function RecentWorkflowsList({ onSelectWorkflow, currentWorkflowId }: RecentWorkflowsListProps) {
  const [workflows, setWorkflows] = useState<Array<{
    workflow_id: string;
    status: string;
    started_at: string;
    completed_at: string | null;
    record_id: string;
  }>>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (isOpen && workflows.length === 0) {
      loadWorkflows();
    }
  }, [isOpen]);

  const loadWorkflows = async () => {
    setLoading(true);
    try {
      const recentWorkflows = await getRecentWorkflows(20);
      setWorkflows(recentWorkflows);
    } catch (error) {
      console.error('[RecentWorkflowsList] Error loading workflows:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 flex items-center space-x-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>Charger un workflow récent</span>
        <svg className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          {/* Backdrop to close dropdown */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute top-full right-0 mt-2 w-96 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 max-h-96 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-indigo-50 to-purple-50">
              <h3 className="text-lg font-bold text-gray-900">Workflows récents</h3>
              <p className="text-sm text-gray-600 mt-1">Sélectionnez un workflow pour charger ses résultats</p>
            </div>
            
            <div className="overflow-y-auto flex-1">
              {loading ? (
                <div className="p-8 flex items-center justify-center">
                  <LoadingSpinner />
                </div>
              ) : workflows.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <svg className="w-12 h-12 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>Aucun workflow récent trouvé</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {workflows.map((workflow) => (
                    <button
                      key={workflow.workflow_id}
                      onClick={() => {
                        onSelectWorkflow(workflow.workflow_id);
                        setIsOpen(false);
                      }}
                      className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                        currentWorkflowId === workflow.workflow_id ? 'bg-indigo-50 border-l-4 border-indigo-500' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full border ${getStatusColor(workflow.status)}`}>
                              {workflow.status}
                            </span>
                            {currentWorkflowId === workflow.workflow_id && (
                              <span className="text-xs text-indigo-600 font-medium">Actuel</span>
                            )}
                          </div>
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {workflow.workflow_id.substring(0, 8)}...
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            Record: {workflow.record_id}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            Début: {formatDate(workflow.started_at)}
                          </p>
                          {workflow.completed_at && (
                            <p className="text-xs text-gray-500">
                              Fin: {formatDate(workflow.completed_at)}
                            </p>
                          )}
                        </div>
                        <svg className="w-5 h-5 text-gray-400 flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

