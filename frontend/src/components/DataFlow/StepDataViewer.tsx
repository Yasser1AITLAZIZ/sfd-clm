// Data at each step component
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface StepDataViewerProps {
  stepName: string;
  stepOrder: number;
  data: any;
  isExpanded: boolean;
  onToggle: () => void;
}

export function StepDataViewer({ stepName, stepOrder, data, isExpanded, onToggle }: StepDataViewerProps) {
  const dataSize = JSON.stringify(data).length;
  const fieldCount = data.fields?.length || data.filled_form_json?.length || 0;

  return (
    <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg border-2 border-blue-200 transition-all duration-300 hover:shadow-xl">
      <button
        onClick={onToggle}
        className="w-full px-6 py-5 flex items-center justify-between hover:bg-gradient-to-r hover:from-blue-50/50 hover:to-indigo-50/50 transition-all duration-200 rounded-t-2xl"
      >
        <div className="flex items-center space-x-4 flex-1">
          <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-lg text-white shadow-md">
            {stepOrder}
          </div>
          <div className="flex-1 text-left">
            <h3 className="text-lg font-bold text-gray-900">{stepName}</h3>
            <div className="flex items-center space-x-3 mt-1 text-sm">
              {fieldCount > 0 && (
                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full font-medium">
                  {fieldCount} fields
                </span>
              )}
              <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full font-medium">
                {dataSize} bytes
              </span>
            </div>
          </div>
        </div>
        <svg
          className={`w-6 h-6 text-gray-400 transform transition-transform duration-200 flex-shrink-0 ml-4 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isExpanded && (
        <div className="px-6 pb-6 border-t border-gray-200 pt-4 animate-in slide-in-from-top-2 duration-200">
          <div className="bg-gray-900 rounded-xl p-4 overflow-x-auto">
            <SyntaxHighlighter
              language="json"
              style={vscDarkPlus}
              customStyle={{ 
                borderRadius: '0.5rem', 
                fontSize: '0.875rem',
                margin: 0,
                padding: '1rem',
              }}
            >
              {JSON.stringify(data, null, 2)}
            </SyntaxHighlighter>
          </div>
        </div>
      )}
    </div>
  );
}

