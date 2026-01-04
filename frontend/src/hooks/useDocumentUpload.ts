// Document upload hook
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadDocument } from '../services/documents';

export function useDocumentUpload() {
  const queryClient = useQueryClient();
  const [uploadProgress, setUploadProgress] = useState(0);

  const mutation = useMutation<
    { document_id: string; url: string; filename: string },
    Error,
    { recordId: string; file: File }
  >({
    mutationFn: ({ recordId, file }) => uploadDocument(recordId, file),
    onSuccess: (data, variables) => {
      setUploadProgress(0);
      // CRITICAL: Invalidate formData cache to refresh documents list
      // This ensures the newly uploaded document appears in Document Processing page
      queryClient.invalidateQueries({ queryKey: ['formData', variables.recordId] });
      console.log('[useDocumentUpload] Document uploaded and cache invalidated for recordId:', variables.recordId);
    },
    onError: (error) => {
      setUploadProgress(0);
      console.error('[useDocumentUpload] Upload error:', error);
    },
  });

  return {
    ...mutation,
    uploadProgress,
    upload: mutation.mutate,
    uploadAsync: mutation.mutateAsync,
  };
}

