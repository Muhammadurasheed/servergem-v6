/**
 * WebSocket Message Types and Interfaces
 * Type-safe message definitions for client-server communication
 */

// ============================================================================
// Connection Types
// ============================================================================

export type ConnectionState = 
  | 'idle'          // Not connected
  | 'connecting'    // Attempting connection
  | 'connected'     // Successfully connected
  | 'reconnecting'  // Lost connection, attempting to reconnect
  | 'disconnected'  // Intentionally disconnected
  | 'error';        // Connection error

export interface ConnectionStatus {
  state: ConnectionState;
  error?: string;
  reconnectAttempt?: number;
  lastConnected?: Date;
}

// ============================================================================
// Base Message Types
// ============================================================================

export type MessageRole = 'user' | 'assistant' | 'system';

export type ServerMessageType = 
  | 'connected'           // Initial connection confirmation
  | 'typing'              // AI is processing
  | 'message'             // AI response message
  | 'analysis'            // Code analysis result
  | 'deployment_started'  // Deployment process started
  | 'deployment_progress' // Real-time deployment progress
  | 'deployment_update'   // Deployment progress update (legacy)
  | 'deployment_complete' // Deployment finished
  | 'error'               // Error occurred
  | 'pong';               // Heartbeat response

export type ClientMessageType =
  | 'init'                // Initialize connection
  | 'message'             // User message
  | 'ping';               // Heartbeat

// ============================================================================
// Client Messages (Frontend → Backend)
// ============================================================================

export interface ClientInitMessage {
  type: 'init';
  session_id: string;
  instance_id?: string;
  is_reconnect?: boolean;
  metadata?: {
    userAgent: string;
    timestamp: string;
  };
}

export interface ClientChatMessage {
  type: 'message';
  message: string;
  context?: Record<string, any>;
}

export interface ClientPingMessage {
  type: 'ping';
  timestamp: string;
}

export type ClientMessage = 
  | ClientInitMessage 
  | ClientChatMessage 
  | ClientPingMessage;

// ============================================================================
// Server Messages (Backend → Frontend)
// ============================================================================

export interface ServerConnectedMessage {
  type: 'connected';
  session_id: string;
  message: string;
}

export interface ServerTypingMessage {
  type: 'typing';
  timestamp: string;
}

export interface ServerChatMessage {
  type: 'message';
  data: {
    content: string;
    intent?: string;
    agents?: string[];
    actions?: MessageAction[];
    metadata?: Record<string, any>;
  };
  timestamp: string;
}

export interface ServerAnalysisMessage {
  type: 'analysis';
  data: {
    language: string;
    framework: string;
    entry_point?: string;
    dependencies: Array<{ name: string; version: string }>;
    database?: string;
    env_vars: string[];
    port: number;
    recommendations: string[];
    warnings: string[];
  };
  timestamp: string;
}

export interface ServerDeploymentUpdate {
  type: 'deployment_update';
  data: {
    stage: string;
    progress: number;
    message: string;
    logs?: string[];
  };
  timestamp: string;
}

export interface ServerDeploymentStarted {
  type: 'deployment_started';
  deployment_id: string;
  data?: {
    message?: string;
  };
  message?: string;
  timestamp: string;
}

export interface ServerDeploymentProgress {
  type: 'deployment_progress';
  deployment_id: string;
  stage: string;
  status: string;
  message: string;
  details?: Record<string, any>;
  progress?: number;
  timestamp: string;
}

export interface ServerDeploymentComplete {
  type: 'deployment_complete';
  data: {
    status?: string;
    message?: string;
    url?: string;
    service_name?: string;
    region?: string;
    error?: string;
    details?: Record<string, any>;
    metadata?: Record<string, any>;
  };
  timestamp: string;
}

export interface ServerErrorMessage {
  type: 'error';
  message: string;
  code?: string;
  timestamp: string;
}

export interface ServerPongMessage {
  type: 'pong';
  timestamp: string;
}

export type ServerMessage = 
  | ServerConnectedMessage
  | ServerTypingMessage
  | ServerChatMessage
  | ServerAnalysisMessage
  | ServerDeploymentStarted
  | ServerDeploymentProgress
  | ServerDeploymentUpdate
  | ServerDeploymentComplete
  | ServerErrorMessage
  | ServerPongMessage;

// ============================================================================
// Message Actions (UI Interactions)
// ============================================================================

export interface MessageAction {
  id: string;
  label: string;
  type: 'button' | 'link' | 'input';
  action?: string;
  url?: string;
  variant?: 'primary' | 'secondary' | 'ghost';
}

// ============================================================================
// Chat Message (UI Display)
// ============================================================================

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  actions?: MessageAction[];
  deploymentUrl?: string;
  metadata?: Record<string, any>;
  isTyping?: boolean;
}

// ============================================================================
// WebSocket Configuration
// ============================================================================

export interface WebSocketConfig {
  url: string;
  reconnect: {
    enabled: boolean;
    maxAttempts: number;
    initialDelay: number;
    maxDelay: number;
    backoffMultiplier: number;
  };
  heartbeat: {
    enabled: boolean;
    interval: number;
    timeout: number;
  };
  messageQueue: {
    enabled: boolean;
    maxSize: number;
  };
}

// ============================================================================
// Hooks Return Types
// ============================================================================

export interface UseWebSocketReturn {
  // Connection state
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  
  // Methods
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: ClientMessage) => boolean;
  
  // Event handlers
  onMessage: (handler: (message: ServerMessage) => void) => () => void;
  onError: (handler: (error: Error) => void) => () => void;
  onConnectionChange: (handler: (status: ConnectionStatus) => void) => () => void;
}

export interface UseChatReturn {
  // State
  messages: ChatMessage[];
  isConnected: boolean;
  isTyping: boolean;
  connectionStatus: ConnectionStatus;
  
  // Methods
  sendMessage: (content: string, context?: Record<string, any>) => void;
  sendStructuredMessage: (type: string, data: any) => void;
  clearMessages: () => void;
  
  // Connection control
  connect: () => void;
  disconnect: () => void;
  
  // ✅ PHASE 1.2: Deployment progress state
  activeDeployment: {
    deploymentId: string;
    stages: any[];
    currentStage: string;
    overallProgress: number;
    status: 'deploying' | 'success' | 'failed';
    startTime: string;
  } | null;
}
