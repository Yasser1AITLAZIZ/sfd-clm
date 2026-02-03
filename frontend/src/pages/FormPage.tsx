// Form Visualization Page - Chatbot panel + form area with pagination
import { useState, useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useFormData } from '../hooks/useFormData';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import { useServiceHealth } from '../hooks/useServiceHealth';
import { ChatbotPanel } from '../components/Chatbot/ChatbotPanel';
import { FormPagination } from '../components/FormVisualization/FormPagination';
import { WorkflowProgressBar } from '../components/FormVisualization/WorkflowProgressBar';
import { RecentWorkflowsList } from '../components/FormVisualization/RecentWorkflowsList';
import { ErrorDisplay } from '../components/common/ErrorDisplay';
import { matchFields } from '../utils/fieldMatcher';
import { getWorkflowStatus } from '../services/workflow';
import { DEFAULT_FORM_GROUP_ORDER } from '../utils/formGrouping';
import type { MatchedField } from '../types/form';

const DEFAULT_RECORD_ID = '001XX000001';
const RECORD_ID_STORAGE_KEY = 'sfd-clm-record-id';

export function FormPage() {
  // Get recordId from localStorage (shared with WorkflowPage)
  const [recordId] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(RECORD_ID_STORAGE_KEY) || DEFAULT_RECORD_ID;
    }
    return DEFAULT_RECORD_ID;
  });
  const [userMessage, setUserMessage] = useState('Remplis tous les champs manquants');
  const [matchedFields, setMatchedFields] = useState<MatchedField[]>([]);
  const [rootConfidenceScores, setRootConfidenceScores] = useState<Record<string, number>>({});
  const [hasExecutedPipeline, setHasExecutedPipeline] = useState(false);
  const [restartKey, setRestartKey] = useState(0);

  const queryClient = useQueryClient();
  const { data: formData, isLoading: isLoadingForm, error: formError, refetch: refetchForm } = useFormData(recordId);
  const { executeAsync, workflowId, isLoading: isExecuting, error: executionError, clearWorkflow } = usePipelineExecution();
  const { data: servicesHealth } = useServiceHealth();
  const allServicesHealthy = servicesHealth?.every(s => s.status === 'healthy') ?? false;
  const [localWorkflowId, setLocalWorkflowId] = useState<string | null>(null);
  const [, setIsLoadingWorkflow] = useState(false);
  
  // Sync workflowId from usePipelineExecution (only after new execution)
  useEffect(() => {
    if (workflowId) {
      setLocalWorkflowId(workflowId);
      localStorage.setItem('sfd-clm-workflow-id', workflowId);
    }
  }, [workflowId]);

  const activeWorkflowId = workflowId || localWorkflowId;

  // Function to manually load a workflow (called from RecentWorkflowsList)
  const handleLoadWorkflow = async (workflowIdToLoad: string) => {
    if (!formData) {
      console.warn('[FormPage] Cannot load workflow: formData not available');
      return;
    }

    setIsLoadingWorkflow(true);
    try {
      console.log('[FormPage] Loading workflow results for:', workflowIdToLoad);
      
      const workflowStatus = await getWorkflowStatus(workflowIdToLoad);
      
      // Extract filled_form_json from workflow status
      const responseStep = workflowStatus?.steps?.find(s => s.step_name === 'response_handling');
      const mcpStep = workflowStatus?.steps?.find(s => s.step_name === 'mcp_sending');
      
      let filledFormJson: any[] = [];
      let confidenceScores: Record<string, number> = {};

      // Try multiple paths to find filled_form_json
      if (responseStep?.output_data?.filled_form_json && Array.isArray(responseStep.output_data.filled_form_json)) {
        filledFormJson = responseStep.output_data.filled_form_json;
        confidenceScores = responseStep.output_data.confidence_scores || {};
        console.log('[FormPage] Found filled_form_json in response_handling:', filledFormJson.length, 'fields');
      } else if (mcpStep?.output_data?.mcp_response?.filled_form_json && Array.isArray(mcpStep.output_data.mcp_response.filled_form_json)) {
        filledFormJson = mcpStep.output_data.mcp_response.filled_form_json;
        confidenceScores = mcpStep.output_data.mcp_response.confidence_scores || {};
        console.log('[FormPage] Found filled_form_json in mcp_sending:', filledFormJson.length, 'fields');
      }

      // If we found results, update the form
      if (filledFormJson.length > 0 && formData) {
        const matched = matchFields(formData.fields, filledFormJson);
        setRootConfidenceScores(confidenceScores);
        setMatchedFields(matched);
        setHasExecutedPipeline(true);
        
        // Store workflowId in localStorage and state
        localStorage.setItem('sfd-clm-workflow-id', workflowIdToLoad);
        setLocalWorkflowId(workflowIdToLoad);
        
        console.log('[FormPage] Loaded workflow results:', matched.length, 'fields');
      } else {
        console.warn('[FormPage] No filled_form_json found in workflow');
      }
    } catch (error) {
      console.error('[FormPage] Error loading workflow results:', error);
    } finally {
      setIsLoadingWorkflow(false);
    }
  };

  // Listen for workflow execution results in real-time (only for newly executed workflows)
  useEffect(() => {
    // Only poll if workflow was just executed (workflowId from usePipelineExecution)
    // NOT if it was loaded manually from RecentWorkflowsList
    if (!workflowId || !formData || matchedFields.length > 0) {
      return;
    }

    let pollCount = 0;
    const maxPolls = 30; // Maximum 30 polls (60 seconds)
    
    // Poll workflow status to get results as they become available
    const pollInterval = setInterval(async () => {
      pollCount++;
      
      // Stop polling after max attempts
      if (pollCount > maxPolls) {
        clearInterval(pollInterval);
        console.log('[FormPage] Stopped polling after max attempts');
        return;
      }

      try {
        const workflowStatus = await getWorkflowStatus(workflowId);
        
        // Check if workflow is completed and we have results
        if (workflowStatus?.status === 'completed') {
          const responseStep = workflowStatus?.steps?.find(s => s.step_name === 'response_handling');
          const mcpStep = workflowStatus?.steps?.find(s => s.step_name === 'mcp_sending');
          
          let filledFormJson: any[] = [];
          let confidenceScores: Record<string, number> = {};

          if (responseStep?.output_data?.filled_form_json && Array.isArray(responseStep.output_data.filled_form_json)) {
            filledFormJson = responseStep.output_data.filled_form_json;
            confidenceScores = responseStep.output_data.confidence_scores || {};
          } else if (mcpStep?.output_data?.mcp_response?.filled_form_json && Array.isArray(mcpStep.output_data.mcp_response.filled_form_json)) {
            filledFormJson = mcpStep.output_data.mcp_response.filled_form_json;
            confidenceScores = mcpStep.output_data.mcp_response.confidence_scores || {};
          }

          if (filledFormJson.length > 0 && formData) {
            const matched = matchFields(formData.fields, filledFormJson);
            setRootConfidenceScores(confidenceScores);
            setMatchedFields(matched);
            setHasExecutedPipeline(true);
            clearInterval(pollInterval);
            console.log('[FormPage] Polled and loaded workflow results:', matched.length, 'fields');
          } else if (workflowStatus?.status === 'completed') {
            // Workflow completed but no results found, stop polling
            clearInterval(pollInterval);
            console.log('[FormPage] Workflow completed but no filled_form_json found');
          }
        }
      } catch (error) {
        console.error('[FormPage] Error polling workflow status:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [workflowId, formData]); // Only poll for newly executed workflows

  // Function to reset form to initial state (new form)
  const handleResetForm = () => {
    console.log('[FormPage] Resetting form to initial state...');
    
    // Clear workflow ID from localStorage and state
    localStorage.removeItem('sfd-clm-workflow-id');
    clearWorkflow();
    
    // Reset ALL form state
    setMatchedFields([]);
    setRootConfidenceScores({});
    setHasExecutedPipeline(false);
    setLocalWorkflowId(null);
    
    // Reset user message to default
    setUserMessage('Remplis tous les champs manquants');
    
    // Force complete cache removal
    queryClient.removeQueries({ queryKey: ['formData', recordId] });
    queryClient.removeQueries({ queryKey: ['workflowStatus'] });
    
    // Force remount of FormFieldList
    setRestartKey(prev => prev + 1);
    
    // Refetch form data to get clean state
    refetchForm().then(() => {
      console.log('[FormPage] Form reset to initial state - all data cleared');
    });
  };

  const handleExecutePipeline = async () => {
    if (!formData) return;

    try {
      const response = await executeAsync({
        recordId,
        sessionId: null,
        userMessage: userMessage,
      });

      console.log('Pipeline response:', response);

      // Extract filled_form_json from response
      let filledFormJson: any[] = [];
      let confidenceScores: Record<string, number> = {};

      // Try root level first (primary location)
      if (response.filled_form_json && Array.isArray(response.filled_form_json)) {
        filledFormJson = response.filled_form_json;
        confidenceScores = response.confidence_scores || {};
        console.log('Found filled_form_json at root level:', filledFormJson.length, 'fields');
      }
      // Try response_handling
      else if (response.data?.response_handling?.filled_form_json && Array.isArray(response.data.response_handling.filled_form_json)) {
        filledFormJson = response.data.response_handling.filled_form_json;
        confidenceScores = response.data.response_handling.confidence_scores || {};
        console.log('Found filled_form_json in response_handling:', filledFormJson.length, 'fields');
      }
      // Try mcp_sending.mcp_response
      else if (response.data?.mcp_sending?.mcp_response?.filled_form_json && Array.isArray(response.data.mcp_sending.mcp_response.filled_form_json)) {
        filledFormJson = response.data.mcp_sending.mcp_response.filled_form_json;
        confidenceScores = response.data.mcp_sending.mcp_response.confidence_scores || {};
        console.log('Found filled_form_json in mcp_sending.mcp_response:', filledFormJson.length, 'fields');
      }
      // Try data directly
      else if (response.data?.filled_form_json && Array.isArray(response.data.filled_form_json)) {
        filledFormJson = response.data.filled_form_json;
        confidenceScores = response.data.confidence_scores || {};
        console.log('Found filled_form_json in data:', filledFormJson.length, 'fields');
      }

      // CRITICAL: Store workflowId immediately in localStorage
      if (response.workflow_id) {
        localStorage.setItem('sfd-clm-workflow-id', response.workflow_id);
        setLocalWorkflowId(response.workflow_id);
        console.log('[FormPage] Stored workflowId in localStorage:', response.workflow_id);
      }

      // Match fields
      if (filledFormJson.length > 0 && formData) {
        const matched = matchFields(formData.fields, filledFormJson);
        setRootConfidenceScores(confidenceScores);
        setMatchedFields(matched);
        setHasExecutedPipeline(true);
      }
      
      // CRITICAL: Start polling workflow status immediately
      if (response.workflow_id) {
        queryClient.invalidateQueries({ queryKey: ['workflowStatus', response.workflow_id] });
        queryClient.refetchQueries({ queryKey: ['workflowStatus', response.workflow_id] });
      }
      
      console.log('[FormPage] Pipeline executed successfully, workflowId:', response.workflow_id);
    } catch (error) {
      console.error('Pipeline execution error:', error);
    }
  };


  // Ensure displayFields always shows initial state (no AI values) when no matched fields
  // Use useMemo to force reset when activeWorkflowId is cleared
  const displayFields = useMemo(() => {
    // If no matched fields AND no active workflow, return clean fields
    if (matchedFields.length === 0 && !activeWorkflowId) {
      return formData?.fields.map(f => ({
        ...f,
        isMatched: false,
        dataValue_target_AI: null, // Explicitly clear AI values
        dataValue: f.defaultValue || null, // Reset to default only
      })) || [];
    }
    
    // If matched fields exist, use them
    if (matchedFields.length > 0) {
      return matchedFields;
    }
    
    // Otherwise, return clean fields
    return formData?.fields.map(f => ({
      ...f,
      isMatched: false,
      dataValue_target_AI: null,
      dataValue: f.defaultValue || null,
    })) || [];
  }, [matchedFields, formData, activeWorkflowId]);

  const statusMessage = activeWorkflowId
    ? hasExecutedPipeline
      ? 'Workflow terminé.'
      : 'Workflow en cours…'
    : null;

  return (
    <div className="space-y-6">
      {/* Header Section - full width */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
          <div className="flex-1 min-w-0">
            <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-800 bg-clip-text text-transparent mb-2">
              Form Visualization
            </h1>
            <p className="text-gray-600 text-base sm:text-lg">View and interact with Salesforce form fields</p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={handleResetForm}
              className="px-4 py-2 bg-gradient-to-r from-gray-500 to-gray-600 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 flex items-center space-x-2 whitespace-nowrap"
              title="Réinitialiser le formulaire à l'état vierge"
            >
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span className="hidden sm:inline">Nouveau formulaire</span>
              <span className="sm:hidden">Nouveau</span>
            </button>
            <RecentWorkflowsList 
              onSelectWorkflow={handleLoadWorkflow}
              currentWorkflowId={activeWorkflowId}
            />
            {activeWorkflowId && (
              <Link
                to="/workflow"
                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 whitespace-nowrap"
              >
                <span className="hidden sm:inline">View Workflow Status</span>
                <span className="sm:hidden">Workflow</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Two-column layout: Chatbot (small) | Form area (large) */}
      <div className="flex flex-col lg:flex-row gap-6 min-h-[480px]">
        {/* Chatbot panel - fixed width on large screens */}
        <aside className="w-full lg:w-80 flex-shrink-0 lg:min-h-[420px]">
          <div className="h-full min-h-[320px] lg:min-h-[420px]">
            <ChatbotPanel
              userMessage={userMessage}
              setUserMessage={setUserMessage}
              onExecute={handleExecutePipeline}
              isExecuting={isExecuting}
              allServicesHealthy={allServicesHealthy}
              formDataLoaded={!!formData}
              executionError={executionError}
              statusMessage={statusMessage}
            />
          </div>
        </aside>

        {/* Form section - takes remaining space */}
        <section className="flex-1 min-w-0 flex flex-col bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 overflow-hidden">
          {/* Execution Error - shown in form area when present */}
          {executionError && (
            <div className="p-4 border-b border-red-200/50 bg-red-50/80">
              <ErrorDisplay error={executionError} />
            </div>
          )}
          {/* Workflow Progress Bar */}
          {activeWorkflowId && (
            <div className="flex-shrink-0 border-b border-gray-200/50">
              <WorkflowProgressBar workflowId={activeWorkflowId} />
            </div>
          )}
          {/* Form content: loading or paginated fields */}
          <div className="flex-1 p-6 min-h-0 flex flex-col">
            {isLoadingForm ? (
              <div className="flex justify-center items-center flex-1 py-12">
                <div className="text-center">
                  <div className="relative">
                    <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
                    </div>
                  </div>
                  <p className="mt-4 text-gray-600 font-medium">Chargement des champs…</p>
                </div>
              </div>
            ) : formData ? (
              <FormPagination
                key={`form-pagination-${restartKey}`}
                fields={displayFields}
                formGroupOrder={[...DEFAULT_FORM_GROUP_ORDER]}
                rootConfidenceScores={rootConfidenceScores}
                hasExecutedPipeline={hasExecutedPipeline}
                layout="horizontal"
              />
            ) : formError ? (
              <div className="flex items-center justify-center flex-1 py-12">
                <p className="text-red-600">{formError.message}</p>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}

