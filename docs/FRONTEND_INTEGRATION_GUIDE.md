# Next.js Frontend Integration Guide
## AI Dashboard Platform - Complete User Journey Implementation

### 🚀 **Quick Start Setup**

#### 1. **Project Structure**
```
nextjs-dashboard/
├── src/
│   ├── components/
│   │   ├── data-sources/
│   │   ├── data-processing/
│   │   ├── data-validation/
│   │   ├── data-cleanup/
│   │   ├── metadata/
│   │   ├── workflow/
│   │   └── dashboard/
│   ├── hooks/
│   │   ├── useDataFlow.ts
│   │   ├── useWorkflow.ts
│   │   └── useDashboard.ts
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── dashboard.ts
│   └── pages/
│       ├── dashboard/
│       │   ├── create.tsx
│       │   ├── [id].tsx
│       │   └── index.tsx
│       └── workflow/
│           ├── [id].tsx
│           └── index.tsx
```

#### 2. **API Service Setup**

```typescript
// src/services/api.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// API Service Classes
export class DataSourceService {
  static async connect(config: DataSourceConfig) {
    return api.post('/api/data-sources/connect', config);
  }

  static async test(sourceId: string) {
    return api.post(`/api/data-sources/test`, { source_id: sourceId });
  }

  static async list() {
    return api.get('/api/data-sources/list');
  }
}

export class DataProcessingService {
  static async ingest(sourceId: string, options: ProcessingOptions) {
    return api.post('/api/processing/ingest', { source_id: sourceId, ...options });
  }

  static async normalize(dataId: string) {
    return api.post('/api/processing/normalize', { data_id: dataId });
  }

  static async profile(dataId: string) {
    return api.get(`/api/processing/profile/${dataId}`);
  }
}

export class DataValidationService {
  static async validate(dataId: string) {
    return api.post('/api/data-validation/validate', { data_id: dataId });
  }

  static async getReport(validationId: string) {
    return api.get(`/api/data-validation/report/${validationId}`);
  }
}

export class DataCleanupService {
  static async analyze(dataId: string) {
    return api.post('/api/data-cleanup/analyze', { data_id: dataId });
  }

  static async preview(cleanupId: string, operations: CleanupOperation[]) {
    return api.post('/api/data-cleanup/preview', { cleanup_id: cleanupId, operations });
  }

  static async apply(cleanupId: string, operations: CleanupOperation[]) {
    return api.post('/api/data-cleanup/apply', { cleanup_id: cleanupId, operations });
  }
}

export class MetadataService {
  static async extract(dataId: string) {
    return api.post('/api/metadata/extract', { data_id: dataId });
  }

  static async enhance(metadataId: string, enhancements: MetadataEnhancement[]) {
    return api.post('/api/metadata/enhance', { metadata_id: metadataId, enhancements });
  }

  static async validate(metadataId: string) {
    return api.post('/api/metadata/validate', { metadata_id: metadataId });
  }
}

export class WorkflowService {
  static async create(workflowData: WorkflowCreateRequest) {
    return api.post('/api/workflow/create', workflowData);
  }

  static async approve(workflowId: string, approval: ApprovalData) {
    return api.post(`/api/workflow/${workflowId}/approve`, approval);
  }

  static async getStatus(workflowId: string) {
    return api.get(`/api/workflow/${workflowId}/status`);
  }
}

export class DashboardService {
  static async generate(request: DashboardGenerationRequest) {
    return api.post('/api/dashboard-generation/generate', request);
  }

  static async export(dashboardId: string, options: ExportOptions) {
    return api.post(`/api/dashboard-generation/${dashboardId}/export`, options);
  }

  static async getVersions(dashboardId: string) {
    return api.get(`/api/dashboard-generation/${dashboardId}/versions`);
  }

  static async rollback(dashboardId: string, targetVersionId: string, reason: string) {
    return api.post(`/api/dashboard-generation/${dashboardId}/rollback`, {
      target_version_id: targetVersionId,
      rollback_reason: reason
    });
  }
}
```

### 🎯 **Complete User Journey Implementation**

#### 3. **Main Data Flow Hook**

```typescript
// src/hooks/useDataFlow.ts
import { useState, useCallback } from 'react';
import { DataSourceService, DataProcessingService, DataValidationService, DataCleanupService, MetadataService, WorkflowService, DashboardService } from '../services/api';

export interface DataFlowState {
  currentStep: number;
  dataSourceId?: string;
  dataId?: string;
  validationId?: string;
  cleanupId?: string;
  metadataId?: string;
  workflowId?: string;
  dashboardId?: string;
  loading: boolean;
  error?: string;
}

export const useDataFlow = () => {
  const [state, setState] = useState<DataFlowState>({
    currentStep: 1,
    loading: false
  });

  const updateState = (updates: Partial<DataFlowState>) => {
    setState(prev => ({ ...prev, ...updates }));
  };

  // Step 1: Connect Data Source
  const connectDataSource = useCallback(async (config: DataSourceConfig) => {
    updateState({ loading: true, error: undefined });
    try {
      const response = await DataSourceService.connect(config);
      updateState({
        dataSourceId: response.data.source_id,
        currentStep: 2,
        loading: false
      });
      return response.data;
    } catch (error) {
      updateState({ error: error.message, loading: false });
      throw error;
    }
  }, []);

  // Step 2: Process Data
  const processData = useCallback(async (options: ProcessingOptions) => {
    if (!state.dataSourceId) throw new Error('No data source connected');
    updateState({ loading: true, error: undefined });
    try {
      const response = await DataProcessingService.ingest(state.dataSourceId, options);
      updateState({
        dataId: response.data.data_id,
        currentStep: 3,
        loading: false
      });
      return response.data;
    } catch (error) {
      updateState({ error: error.message, loading: false });
      throw error;
    }
  }, [state.dataSourceId]);

  // Step 3: Validate Data
  const validateData = useCallback(async () => {
    if (!state.dataId) throw new Error('No data to validate');
    updateState({ loading: true, error: undefined });
    try {
      const response = await DataValidationService.validate(state.dataId);
      updateState({
        validationId: response.data.validation_id,
        currentStep: 4,
        loading: false
      });
      return response.data;
    } catch (error) {
      updateState({ error: error.message, loading: false });
      throw error;
    }
  }, [state.dataId]);

  // Step 4: Clean Data
  const cleanData = useCallback(async (operations: CleanupOperation[]) => {
    if (!state.dataId) throw new Error('No data to clean');
    updateState({ loading: true, error: undefined });
    try {
      const analyzeResponse = await DataCleanupService.analyze(state.dataId);
      const cleanupId = analyzeResponse.data.cleanup_id;

      const response = await DataCleanupService.apply(cleanupId, operations);
      updateState({
        cleanupId: cleanupId,
        currentStep: 5,
        loading: false
      });
      return response.data;
    } catch (error) {
      updateState({ error: error.message, loading: false });
      throw error;
    }
  }, [state.dataId]);

  // Step 5: Manage Metadata
  const enhanceMetadata = useCallback(async (enhancements: MetadataEnhancement[]) => {
    if (!state.dataId) throw new Error('No data for metadata');
    updateState({ loading: true, error: undefined });
    try {
      const extractResponse = await MetadataService.extract(state.dataId);
      const metadataId = extractResponse.data.metadata_id;

      const response = await MetadataService.enhance(metadataId, enhancements);
      updateState({
        metadataId: metadataId,
        currentStep: 6,
        loading: false
      });
      return response.data;
    } catch (error) {
      updateState({ error: error.message, loading: false });
      throw error;
    }
  }, [state.dataId]);

  // Step 6: Create Workflow
  const createWorkflow = useCallback(async (workflowData: WorkflowCreateRequest) => {
    updateState({ loading: true, error: undefined });
    try {
      const response = await WorkflowService.create({
        ...workflowData,
        data_id: state.dataId,
        metadata_id: state.metadataId,
        cleanup_id: state.cleanupId
      });
      updateState({
        workflowId: response.data.workflow_id,
        currentStep: 7,
        loading: false
      });
      return response.data;
    } catch (error) {
      updateState({ error: error.message, loading: false });
      throw error;
    }
  }, [state.dataId, state.metadataId, state.cleanupId]);

  // Step 7: Generate Dashboard
  const generateDashboard = useCallback(async (dashboardConfig: DashboardConfig) => {
    if (!state.workflowId) throw new Error('No approved workflow');
    updateState({ loading: true, error: undefined });
    try {
      const response = await DashboardService.generate({
        workflow_id: state.workflowId,
        dashboard_config: dashboardConfig,
        data: {} // Will be populated from workflow
      });
      updateState({
        dashboardId: response.data.dashboard_id,
        currentStep: 8,
        loading: false
      });
      return response.data;
    } catch (error) {
      updateState({ error: error.message, loading: false });
      throw error;
    }
  }, [state.workflowId]);

  return {
    state,
    connectDataSource,
    processData,
    validateData,
    cleanData,
    enhanceMetadata,
    createWorkflow,
    generateDashboard,
    updateState
  };
};
```

#### 4. **Main Dashboard Creation Flow Component**

```typescript
// src/components/DashboardCreationFlow.tsx
import React, { useState } from 'react';
import { useDataFlow } from '../hooks/useDataFlow';
import { StepIndicator } from './StepIndicator';
import { DataSourceConnection } from './data-sources/DataSourceConnection';
import { DataProcessing } from './data-processing/DataProcessing';
import { DataValidation } from './data-validation/DataValidation';
import { DataCleanup } from './data-cleanup/DataCleanup';
import { MetadataManagement } from './metadata/MetadataManagement';
import { WorkflowApproval } from './workflow/WorkflowApproval';
import { DashboardGeneration } from './dashboard/DashboardGeneration';

const STEPS = [
  { id: 1, name: 'Connect Data Source', description: 'Configure your data connection' },
  { id: 2, name: 'Process Data', description: 'Ingest and normalize your data' },
  { id: 3, name: 'Validate Data', description: 'Check data quality and integrity' },
  { id: 4, name: 'Clean Data', description: 'Fix data quality issues' },
  { id: 5, name: 'Enhance Metadata', description: 'Add context and descriptions' },
  { id: 6, name: 'Review & Approve', description: 'Validate AI recommendations' },
  { id: 7, name: 'Generate Dashboard', description: 'Create your dashboard' },
];

export const DashboardCreationFlow: React.FC = () => {
  const {
    state,
    connectDataSource,
    processData,
    validateData,
    cleanData,
    enhanceMetadata,
    createWorkflow,
    generateDashboard
  } = useDataFlow();

  const renderCurrentStep = () => {
    switch (state.currentStep) {
      case 1:
        return <DataSourceConnection onConnect={connectDataSource} loading={state.loading} />;
      case 2:
        return <DataProcessing onProcess={processData} loading={state.loading} />;
      case 3:
        return <DataValidation onValidate={validateData} loading={state.loading} />;
      case 4:
        return <DataCleanup onClean={cleanData} loading={state.loading} />;
      case 5:
        return <MetadataManagement onEnhance={enhanceMetadata} loading={state.loading} />;
      case 6:
        return <WorkflowApproval onCreate={createWorkflow} loading={state.loading} />;
      case 7:
        return <DashboardGeneration onGenerate={generateDashboard} loading={state.loading} />;
      default:
        return <div>Step not found</div>;
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">Create AI Dashboard</h1>
        <StepIndicator steps={STEPS} currentStep={state.currentStep} />
      </div>

      {state.error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
          <p className="text-red-800">{state.error}</p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border p-6">
        {renderCurrentStep()}
      </div>

      {/* Progress Summary */}
      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h3 className="font-medium mb-2">Progress Summary:</h3>
        <div className="text-sm text-gray-600 space-y-1">
          {state.dataSourceId && <p>✅ Data Source Connected: {state.dataSourceId}</p>}
          {state.dataId && <p>✅ Data Processed: {state.dataId}</p>}
          {state.validationId && <p>✅ Data Validated: {state.validationId}</p>}
          {state.cleanupId && <p>✅ Data Cleaned: {state.cleanupId}</p>}
          {state.metadataId && <p>✅ Metadata Enhanced: {state.metadataId}</p>}
          {state.workflowId && <p>✅ Workflow Created: {state.workflowId}</p>}
          {state.dashboardId && <p>🎉 Dashboard Generated: {state.dashboardId}</p>}
        </div>
      </div>
    </div>
  );
};
```

#### 5. **Example Step Components**

```typescript
// src/components/data-sources/DataSourceConnection.tsx
import React, { useState } from 'react';

interface DataSourceConnectionProps {
  onConnect: (config: DataSourceConfig) => Promise<void>;
  loading: boolean;
}

export const DataSourceConnection: React.FC<DataSourceConnectionProps> = ({ onConnect, loading }) => {
  const [config, setConfig] = useState({
    type: 'excel',
    name: '',
    connection_params: {}
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onConnect(config);
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Connect Your Data Source</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Data Source Type</label>
          <select
            value={config.type}
            onChange={(e) => setConfig(prev => ({ ...prev, type: e.target.value }))}
            className="w-full border rounded-md px-3 py-2"
          >
            <option value="excel">Excel File</option>
            <option value="csv">CSV File</option>
            <option value="database">Database</option>
            <option value="api">API Endpoint</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Source Name</label>
          <input
            type="text"
            value={config.name}
            onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
            className="w-full border rounded-md px-3 py-2"
            placeholder="My Data Source"
          />
        </div>

        {/* Dynamic configuration based on type */}
        {config.type === 'excel' && (
          <div>
            <label className="block text-sm font-medium mb-2">Upload Excel File</label>
            <input type="file" accept=".xlsx,.xls" className="w-full" />
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Connecting...' : 'Connect Data Source'}
        </button>
      </form>
    </div>
  );
};
```

### 📱 **Frontend Pages Structure**

#### 6. **Main Dashboard Page**

```typescript
// src/pages/dashboard/create.tsx
import { DashboardCreationFlow } from '../../components/DashboardCreationFlow';

export default function CreateDashboard() {
  return <DashboardCreationFlow />;
}
```

#### 7. **Dashboard Management Page**

```typescript
// src/pages/dashboard/index.tsx
import React, { useEffect, useState } from 'react';
import { DashboardService } from '../../services/api';
import Link from 'next/link';

export default function DashboardList() {
  const [dashboards, setDashboards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboards = async () => {
      try {
        // Assuming you have a list endpoint
        const response = await DashboardService.list();
        setDashboards(response.data.dashboards);
      } catch (error) {
        console.error('Failed to fetch dashboards:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboards();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">My Dashboards</h1>
        <Link href="/dashboard/create">
          <a className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
            Create New Dashboard
          </a>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {dashboards.map((dashboard) => (
          <div key={dashboard.id} className="border rounded-lg p-4 hover:shadow-md">
            <h3 className="font-semibold mb-2">{dashboard.name}</h3>
            <p className="text-gray-600 text-sm mb-4">{dashboard.description}</p>
            <div className="flex space-x-2">
              <Link href={`/dashboard/${dashboard.id}`}>
                <a className="text-blue-600 hover:underline">View</a>
              </Link>
              <Link href={`/dashboard/${dashboard.id}/edit`}>
                <a className="text-green-600 hover:underline">Edit</a>
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 🔑 **Key Implementation Notes**

1. **Authentication**: All API calls require Bearer token authentication
2. **Error Handling**: Implement comprehensive error boundaries and user feedback
3. **Loading States**: Show progress indicators for each phase
4. **Data Persistence**: Store intermediate results in state/context
5. **Real-time Updates**: Consider WebSocket connections for long-running operations
6. **Export Options**: Implement dashboard export in multiple formats (PDF, PNG, Excel)
7. **Version Control**: Show version history and allow rollbacks
8. **Responsive Design**: Ensure mobile-friendly interface

### 🎯 **Next Steps**

1. **Set up authentication flow** with your backend
2. **Implement each step component** following the examples above
3. **Add real-time notifications** for workflow approvals
4. **Implement dashboard viewer** with interactive components
5. **Add export and sharing capabilities**
6. **Implement collaborative features** (comments, approvals)

This gives you a complete foundation for integrating your Next.js frontend with the AI Dashboard Platform's comprehensive API!
