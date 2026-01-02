// Main App component with routing
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/common/Layout';
import { FormPage } from './pages/FormPage';
import { WorkflowPage } from './pages/WorkflowPage';
import { DataFlowPage } from './pages/DataFlowPage';
import { DocumentViewerPage } from './pages/DocumentViewerPage';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<FormPage />} />
            <Route path="/workflow" element={<WorkflowPage />} />
            <Route path="/dataflow" element={<DataFlowPage />} />
            <Route path="/documents" element={<DocumentViewerPage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
