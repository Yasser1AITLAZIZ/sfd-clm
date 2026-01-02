// Document upload hook
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { uploadDocument } from '../services/documents';

export function useDocumentUpload() {
  const [uploadProgress, setUploadProgress] = useState(0);

  const mutation = useMutation<
    { document_id: string; url: string },
    Error,
    { recordId: string; file: File }
  >({
    mutationFn: ({ recordId, file }) => uploadDocument(recordId, file),
    onSuccess: () => {
      setUploadProgress(0);
    },
    onError: () => {
      setUploadProgress(0);
    },
  });

  return {
    ...mutation,
    uploadProgress,
    upload: mutation.mutate,
    uploadAsync: mutation.mutateAsync,
  };
}

