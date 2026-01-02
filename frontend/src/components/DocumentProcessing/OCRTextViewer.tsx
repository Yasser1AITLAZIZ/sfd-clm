// OCR text display component
interface OCRTextViewerProps {
  ocrText: string;
  title?: string;
}

export function OCRTextViewer({ ocrText, title }: OCRTextViewerProps) {
  return (
    <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl p-6 border border-gray-200/50">
      {title && (
        <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
          <svg className="w-6 h-6 mr-2 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {title}
        </h3>
      )}
      <div className="bg-gray-900 rounded-xl p-4 max-h-[600px] overflow-y-auto">
        <pre className="text-sm whitespace-pre-wrap font-mono text-gray-100 leading-relaxed">{ocrText}</pre>
      </div>
    </div>
  );
}

