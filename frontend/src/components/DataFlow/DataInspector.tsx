// JSON viewer component
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface DataInspectorProps {
  data: any;
  title?: string;
}

export function DataInspector({ data, title }: DataInspectorProps) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      {title && <h3 className="text-lg font-semibold mb-2">{title}</h3>}
      <SyntaxHighlighter
        language="json"
        style={vscDarkPlus}
        customStyle={{ borderRadius: '0.5rem', fontSize: '0.875rem' }}
      >
        {JSON.stringify(data, null, 2)}
      </SyntaxHighlighter>
    </div>
  );
}

