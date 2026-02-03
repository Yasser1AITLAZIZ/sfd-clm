// Small chatbot panel: user message input + Execute Workflow button + optional status
import { LoadingSpinner } from '../common/LoadingSpinner';

export interface ChatbotPanelProps {
  userMessage: string;
  setUserMessage: (value: string) => void;
  onExecute: () => void;
  isExecuting: boolean;
  allServicesHealthy: boolean;
  formDataLoaded: boolean;
  executionError?: Error | null;
  statusMessage?: string | null;
}

export function ChatbotPanel({
  userMessage,
  setUserMessage,
  onExecute,
  isExecuting,
  allServicesHealthy,
  formDataLoaded,
  executionError,
  statusMessage,
}: ChatbotPanelProps) {
  return (
    <div className="flex flex-col h-full bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 overflow-hidden">
      <div className="p-4 border-b border-gray-200/50">
        <h2 className="text-lg font-bold text-gray-900">Assistant</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Message pour guider le remplissage des champs
        </p>
      </div>
      <div className="flex-1 flex flex-col p-4 gap-4 min-h-0">
        <label className="block text-sm font-semibold text-gray-700">
          User Message
        </label>
        <textarea
          value={userMessage}
          onChange={(e) => setUserMessage(e.target.value)}
          className="w-full px-3 py-2 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder-gray-400 resize-y text-sm"
          rows={3}
          placeholder="Ex: Remplis tous les champs manquants"
        />
        {!allServicesHealthy && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-xl text-yellow-800 text-xs">
            Certains services sont indisponibles. L’exécution peut échouer.
          </div>
        )}
        <button
          onClick={onExecute}
          disabled={isExecuting || !formDataLoaded || !allServicesHealthy || !userMessage.trim()}
          className="w-full px-4 py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm"
        >
          {isExecuting ? (
            <>
              <LoadingSpinner size="sm" />
              <span>Exécution…</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Exécuter le workflow</span>
            </>
          )}
        </button>
        {statusMessage && (
          <p className="text-xs text-gray-600">{statusMessage}</p>
        )}
        {executionError && (
          <p className="text-xs text-red-600">{executionError.message}</p>
        )}
      </div>
    </div>
  );
}
