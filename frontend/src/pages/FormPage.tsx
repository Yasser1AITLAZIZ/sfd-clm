// Form Visualization Page - Only form display with horizontal layout
import { useState, useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useFormData } from '../hooks/useFormData';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import { useServiceHealth } from '../hooks/useServiceHealth';
import { FormFieldList } from '../components/FormVisualization/FormFieldList';
import { WorkflowProgressBar } from '../components/FormVisualization/WorkflowProgressBar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorDisplay } from '../components/common/ErrorDisplay';
import { matchFields } from '../utils/fieldMatcher';
import { getWorkflowStatus } from '../services/workflow';
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
  
  useEffect(() => {
    const storedId = typeof window !== 'undefined' ? localStorage.getItem('sfd-clm-workflow-id') : null;
    setLocalWorkflowId(storedId);
  }, [workflowId]);

  const activeWorkflowId = workflowId || localWorkflowId;

  // Load workflow results on mount if workflow exists (only once)
  useEffect(() => {
    let isMounted = true;
    
    const loadWorkflowResults = async () => {
      // Only load if we have a workflow, formData, and no matched fields yet
      if (!activeWorkflowId || !formData || matchedFields.length > 0) {
        return;
      }

      try {
        console.log('[FormPage] Loading existing workflow results for:', activeWorkflowId);
        
        // Fetch workflow status to get filled_form_json
        const workflowStatus = await getWorkflowStatus(activeWorkflowId);

        if (!isMounted) return; // Component unmounted, don't update state

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
        } else if (workflowStatus?.steps?.some(s => s.status === 'completed')) {
          // If workflow is completed but no filled_form_json found
          console.log('[FormPage] Workflow completed but no filled_form_json found in steps');
        }

        if (!isMounted) return; // Check again before updating state

        // If we found results, update the form
        if (filledFormJson.length > 0 && formData) {
          const matched = matchFields(formData.fields, filledFormJson);
          setRootConfidenceScores(confidenceScores);
          setMatchedFields(matched);
          setHasExecutedPipeline(true);
          console.log('[FormPage] Loaded existing workflow results:', matched.length, 'fields');
        } else if (workflowStatus?.status === 'completed' || workflowStatus?.status === 'in_progress') {
          // Mark as executed even if no results yet (workflow is running)
          setHasExecutedPipeline(true);
        }
      } catch (error) {
        console.error('[FormPage] Error loading workflow results:', error);
      }
    };

    loadWorkflowResults();

    return () => {
      isMounted = false;
    };
  }, [activeWorkflowId, formData?.fields?.length]); // Only run when activeWorkflowId changes or formData structure changes

  // Listen for workflow execution results in real-time (only if no matched fields yet)
  useEffect(() => {
    if (!activeWorkflowId || !formData || matchedFields.length > 0) {
      return; // Don't poll if we already have results or no workflow
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
        const workflowStatus = await getWorkflowStatus(activeWorkflowId);
        
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
  }, [activeWorkflowId, formData]); // Remove matchedFields.length from dependencies to avoid infinite loops

  const handleRestartPipeline = () => {
    console.log('[FormPage] Starting pipeline restart...');
    
    // Clear workflow ID and all related state
    clearWorkflow();
    
    // Reset ALL form state IMMEDIATELY
    setMatchedFields([]);
    setRootConfidenceScores({});
    setHasExecutedPipeline(false);
    setLocalWorkflowId(null); // CRITICAL: Clear local workflow ID
    
    // Force complete cache removal (not just invalidation)
    queryClient.removeQueries({ queryKey: ['formData', recordId] });
    queryClient.removeQueries({ queryKey: ['workflowStatus'] });
    
    // Force remount of FormFieldList by changing key (resets all local field states)
    setRestartKey(prev => prev + 1);
    
    // Refetch form data to get clean state (without AI values)
    refetchForm().then(() => {
      // After refetch, ensure displayFields is completely clean
      console.log('[FormPage] Pipeline restarted - all state cleared and form data refreshed');
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

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-800 bg-clip-text text-transparent mb-2">
              Form Visualization
            </h1>
            <p className="text-gray-600 text-lg">View and interact with Salesforce form fields</p>
          </div>
          {activeWorkflowId && (
            <Link
              to="/workflow"
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              View Workflow Status
            </Link>
          )}
        </div>
      </div>

      {/* User Message Input */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
        <label className="block text-sm font-semibold text-gray-700 mb-3">
          User Message
        </label>
        <textarea
          value={userMessage}
          onChange={(e) => setUserMessage(e.target.value)}
          className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-gray-900 placeholder-gray-400 resize-y"
          rows={3}
          placeholder="Enter user message (e.g., 'Remplis tous les champs manquants')"
        />
        <p className="mt-2 text-xs text-gray-500">
          This message will be used to guide the AI in filling the form fields.
        </p>
      </div>

      {/* Execute Pipeline Button */}
      {formData && (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
          {!allServicesHealthy && (
            <div className="mb-4 p-4 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
              <div className="flex items-center text-yellow-800">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="font-semibold">Warning: Some services are unhealthy. Pipeline execution may fail.</span>
              </div>
            </div>
          )}
          <button
            onClick={handleExecutePipeline}
            disabled={isExecuting || !formData || !allServicesHealthy || !userMessage.trim()}
            className="w-full px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center space-x-2"
          >
            {isExecuting ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Executing Pipeline...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>Execute Workflow</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Execution Error */}
      {executionError && (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-red-200/50">
          <ErrorDisplay error={executionError} />
        </div>
      )}

      {/* Workflow Progress Bar - Real-time step-by-step */}
      {activeWorkflowId && (
        <WorkflowProgressBar workflowId={activeWorkflowId} />
      )}

      {/* Form Fields - Displayed below progress bar */}
      {isLoadingForm ? (
        <div className="flex justify-center items-center py-20 bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50">
          <div className="text-center">
            <div className="relative">
              <div className="w-20 h-20 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }}></div>
              </div>
            </div>
            <p className="mt-6 text-gray-600 font-medium text-lg animate-pulse">Loading form data...</p>
            <p className="mt-2 text-sm text-gray-500">Please wait while we fetch your form fields</p>
          </div>
        </div>
      ) : formData ? (
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-gray-200/50">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Form Fields
              <span className="ml-3 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                {displayFields.length}
              </span>
            </h2>
          </div>
          <FormFieldList
            key={`form-fields-${restartKey}`}
            fields={displayFields}
            hasExecutedPipeline={hasExecutedPipeline}
            rootConfidenceScores={rootConfidenceScores}
            layout="horizontal"
          />
        </div>
      ) : null}
    </div>
  );
}

