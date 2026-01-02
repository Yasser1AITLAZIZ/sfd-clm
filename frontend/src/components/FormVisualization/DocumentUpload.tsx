// Document upload component with drag & drop
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { validateFileType, validateFileSize } from '../../utils/validators';
import { useDocumentUpload } from '../../hooks/useDocumentUpload';

interface DocumentUploadProps {
  onFileSelect: (file: File) => void;
  onUploadComplete?: (documentId: string, url: string) => void;
  recordId: string;
  disabled?: boolean;
}

export function DocumentUpload({ onFileSelect, onUploadComplete, recordId, disabled = false }: DocumentUploadProps) {
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const { uploadAsync } = useDocumentUpload();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setError(null);
      setUploading(true);

      // Validate file type
      const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
      if (!validateFileType(file, allowedTypes)) {
        setError('Invalid file type. Please upload a PDF or image file.');
        setUploading(false);
        return;
      }

      // Validate file size (max 10MB)
      if (!validateFileSize(file, 10)) {
        setError('File size exceeds 10MB limit.');
        setUploading(false);
        return;
      }

      // Notify parent component about file selection
      onFileSelect(file);

      // Upload document automatically
      try {
        const result = await uploadAsync({ recordId, file });
        console.log('[DocumentUpload] Document uploaded successfully:', result);
        
        // Notify parent about successful upload
        if (onUploadComplete) {
          onUploadComplete(result.document_id, result.url);
        }
      } catch (uploadError: any) {
        console.error('[DocumentUpload] Upload error:', uploadError);
        setError(uploadError.message || 'Failed to upload document. Please try again.');
      } finally {
        setUploading(false);
      }
    },
    [onFileSelect, onUploadComplete, recordId, uploadAsync]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled,
    multiple: false,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 ${
          isDragActive
            ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-50 shadow-lg scale-[1.02]'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50 hover:shadow-md'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center">
          <div className={`mb-4 transition-transform duration-300 ${isDragActive ? 'scale-110' : ''}`}>
            <svg
              className="mx-auto h-16 w-16 text-gray-400"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <p className="mt-2 text-base font-semibold text-gray-700">
            {uploading ? (
              <span className="text-blue-600 flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Uploading...
              </span>
            ) : isDragActive ? (
              <span className="text-blue-600">Drop the file here</span>
            ) : (
              'Drag and drop a document here, or click to select'
            )}
          </p>
          <p className="mt-2 text-sm text-gray-500 flex items-center justify-center space-x-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>PDF, PNG, JPG up to 10MB</span>
          </p>
          <div className="mt-3 inline-flex items-center px-3 py-1 bg-gray-100 rounded-full">
            <span className="text-xs text-gray-600 font-medium">Record ID: {recordId}</span>
          </div>
        </div>
      </div>
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center text-sm text-red-700">
          <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

