/**
 * High-level Chat Hook
 * Abstracts WebSocket complexity for chat UI
 * Now uses app-level WebSocket context for persistent connection
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { UseChatReturn, ChatMessage, ServerMessage } from '@/types/websocket';
import { useToast } from '@/hooks/use-toast';
import { toast as sonnerToast } from 'sonner';

/**
 * Hook for chat functionality
 * Manages messages, typing state, and connection status
 */
export const useChat = (): UseChatReturn => {
  const navigate = useNavigate();
  const { 
    connectionStatus, 
    isConnected, 
    sendMessage: wsSendMessage,
    onMessage,
  } = useWebSocketContext();
  
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  
  // Debug: Log state changes
  useEffect(() => {
    console.log('[useChat] isTyping state changed to:', isTyping);
  }, [isTyping]);
  
  useEffect(() => {
    console.log('[useChat] isConnected state changed to:', isConnected);
  }, [isConnected]);
  
  // ========================================================================
  // Message Creators (defined first to avoid circular dependencies)
  // ========================================================================
  
  const addAssistantMessage = useCallback((data: {
    content: string;
    actions?: any[];
    metadata?: Record<string, any>;
  }) => {
    const message: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: data.content,
      timestamp: new Date(),
      actions: data.actions,
      metadata: data.metadata,
    };
    
    setMessages(prev => [...prev, message]);
  }, []);
  
  const addAnalysisMessage = useCallback((data: any) => {
    const content = formatAnalysisMessage(data);
    addAssistantMessage({ content });
  }, [addAssistantMessage]);
  
  const addDeploymentCompleteMessage = useCallback((data: any) => {
    const message: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: formatDeploymentComplete(data),
      timestamp: new Date(),
      deploymentUrl: data.url,
      actions: [
        { id: 'view_logs', label: '📊 View Logs', type: 'button', action: 'view_logs' },
        { id: 'setup_cicd', label: '🔄 Set Up CI/CD', type: 'button', action: 'setup_cicd' },
        { id: 'custom_domain', label: '🌐 Custom Domain', type: 'button', action: 'custom_domain' },
      ],
    };
    
    setMessages(prev => [...prev, message]);
    
    // Show success toast
    toast({
      title: '🎉 Deployment Successful!',
      description: `Your app is live at ${data.url}`,
    });
  }, [toast]);
  
  const handleErrorMessage = useCallback((serverMessage: any) => {
    const message: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: `❌ **Error:** ${serverMessage.message}`,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, message]);
    
    toast({
      title: 'Error',
      description: serverMessage.message,
      variant: 'destructive',
    });
  }, [toast]);

  const handleServerMessage = useCallback((serverMessage: ServerMessage) => {
    console.log('[useChat] Received server message:', serverMessage.type);
    
    switch (serverMessage.type) {
      case 'connected':
        console.log('[useChat] Connected to server:', serverMessage.message);
        break;
        
      case 'typing':
        console.log('[useChat] Setting typing to true');
        setIsTyping(true);
        break;
      
      case 'deployment_started':
        console.log('[useChat] 🚀 Deployment started:', (serverMessage as any).deployment_id);
        setIsTyping(true);
        
        const deploymentMsg = serverMessage as any;
        const deployStartContent = `## 🚀 Deployment Started\n\n${deploymentMsg.data?.message || 'Starting deployment process to Cloud Run...'}\n\n**Deployment ID:** \`${deploymentMsg.deployment_id}\`\n\n---\n\n*Real-time updates will appear below as each stage completes...*`;
        
        addAssistantMessage({
          content: deployStartContent,
          metadata: { type: 'deployment_started', deployment_id: deploymentMsg.deployment_id }
        });
        break;
      
      case 'deployment_progress':
        console.log('[useChat] 📊 Deployment progress:', (serverMessage as any).stage, (serverMessage as any).status);
        setIsTyping(true);
        
        // Add beautifully formatted progress update
        const progressMsg = serverMessage as any;
        const stageIcons: Record<string, string> = {
          repo_clone: '📦',
          code_analysis: '🔍',
          dockerfile_generation: '🐳',
          security_scan: '🔒',
          container_build: '🏗️',
          cloud_deployment: '☁️',
        };
        
        const stageNames: Record<string, string> = {
          repo_clone: 'Repository Clone',
          code_analysis: 'Code Analysis',
          dockerfile_generation: 'Dockerfile Generation',
          security_scan: 'Security Scan',
          container_build: 'Container Build',
          cloud_deployment: 'Cloud Deployment',
        };
        
        const icon = stageIcons[progressMsg.stage] || '⚙️';
        const stageName = stageNames[progressMsg.stage] || progressMsg.stage;
        
        let statusIcon = '';
        let statusText = '';
        
        if (progressMsg.status === 'success') {
          statusIcon = '✅';
          statusText = 'Complete';
        } else if (progressMsg.status === 'error') {
          statusIcon = '❌';
          statusText = 'Failed';
        } else if (progressMsg.status === 'in-progress') {
          statusIcon = '⏳';
          statusText = 'In Progress';
        }
        
        let content = `### ${icon} ${stageName} ${statusIcon}\n\n`;
        content += `**Status:** ${statusText}`;
        
        if (progressMsg.progress !== undefined && progressMsg.progress > 0) {
          content += ` - ${progressMsg.progress}%`;
        }
        
        content += `\n\n${progressMsg.message}`;
        
        // Add details in clean format
        if (progressMsg.details) {
          content += '\n\n**Details:**';
          Object.entries(progressMsg.details).forEach(([key, value]) => {
            const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
            content += `\n- ${formattedKey}: \`${value}\``;
          });
        }
        
        addAssistantMessage({
          content,
          metadata: { type: 'deployment_progress', stage: progressMsg.stage }
        });
        break;
        
      case 'message':
        console.log('[useChat] Setting typing to false, adding message');
        setIsTyping(false);
        
        const msgData = serverMessage.data as any;
        
        // Check if this is an analysis response requesting env vars
        if (msgData?.request_env_vars) {
          console.log('[useChat] Analysis complete, requesting env vars...');
          
          addAssistantMessage({
            content: msgData.content,
            metadata: { 
              type: 'analysis_with_env_request',
              detected_env_vars: msgData.detected_env_vars || []
            }
          });
          
          // Trigger env vars UI by sending a special metadata flag
          sonnerToast.info('Environment Variables Required', {
            description: 'Please provide your environment variables to continue.',
            duration: 5000,
          });
        } else {
          // Handle progress messages vs regular messages
          const isProgress = msgData.metadata?.type === 'progress';
          
          addAssistantMessage({
            content: msgData.content,
            actions: msgData.actions,
            metadata: isProgress ? { type: 'progress' } : msgData.metadata,
          });
        }
        break;
        
      case 'analysis':
        setIsTyping(false);
        addAnalysisMessage(serverMessage.data);
        break;
        
      case 'deployment_complete':
        setIsTyping(false);
        
        const deployData = serverMessage.data;
        const isSuccess = deployData?.status === 'success';
        const completeEmoji = isSuccess ? '🎉' : '❌';
        const completeTitle = isSuccess ? 'Deployment Successful!' : 'Deployment Failed';
        
        let completeContent = `## ${completeEmoji} ${completeTitle}\n\n---\n\n`;
        completeContent += deployData?.message || 'Deployment process completed.';
        
        if (deployData?.url) {
          completeContent += `\n\n### 🌐 Your Application is Live!\n\n`;
          completeContent += `**URL:** [${deployData.url}](${deployData.url})\n\n`;
          completeContent += `Click the link above to view your deployed application.`;
        }
        
        if (deployData?.error) {
          completeContent += `\n\n### ❌ Error Details\n\n\`\`\`\n${deployData.error}\n\`\`\``;
        }
        
        if (deployData?.details) {
          completeContent += '\n\n### 📊 Deployment Summary\n';
          Object.entries(deployData.details).forEach(([key, value]) => {
            const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
            completeContent += `\n- **${formattedKey}:** \`${value}\``;
          });
        }
        
        const completeMessage: ChatMessage = {
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: completeContent,
          timestamp: new Date(),
          deploymentUrl: deployData?.url,
          actions: isSuccess ? [
            { id: 'view_logs', label: '📊 View Logs', type: 'button', action: 'view_logs' },
            { id: 'setup_cicd', label: '🔄 Set Up CI/CD', type: 'button', action: 'setup_cicd' },
            { id: 'custom_domain', label: '🌐 Custom Domain', type: 'button', action: 'custom_domain' },
          ] : undefined,
        };
        
        setMessages(prev => [...prev, completeMessage]);
        
        // Show success/error toast
        if (isSuccess) {
          sonnerToast.success('Deployment Complete! 🎉', {
            description: deployData?.url || 'Your app is live!',
            duration: 5000,
          });
          
          toast({
            title: '🎉 Deployment Successful!',
            description: `Your app is live at ${deployData?.url}`,
          });
        } else {
          sonnerToast.error('Deployment Failed', {
            description: deployData?.error || 'Please check the logs for details.',
            duration: 5000,
          });
        }
        break;
        
      case 'error':
        setIsTyping(false);
        
        // Handle specific error codes
        const errorCode = (serverMessage as any).code;
        
        if (errorCode === 'API_KEY_REQUIRED' || errorCode === 'INVALID_API_KEY') {
          sonnerToast.error(
            serverMessage.message,
            {
              duration: 10000,
              action: {
                label: 'Add API Key',
                onClick: () => navigate('/settings')
              },
            }
          );
        } else if (errorCode === 'QUOTA_EXCEEDED') {
          sonnerToast.error(
            serverMessage.message,
            {
              duration: 10000,
              action: {
                label: 'Check Quota',
                onClick: () => window.open('https://ai.google.dev/aistudio', '_blank')
              },
            }
          );
          
          // Add error message to chat
          const errorMessage: ChatMessage = {
            id: `msg_${Date.now()}`,
            role: 'assistant',
            content: `❌ **API Quota Exceeded**\n\n${serverMessage.message}\n\n**What to do:**\n• Check your Gemini API quota at [Google AI Studio](https://ai.google.dev/aistudio)\n• Wait a few minutes for the quota to reset\n• Consider upgrading your API plan if you need higher limits`,
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, errorMessage]);
        } else {
          // For other errors, also show in chat
          const errorMessage: ChatMessage = {
            id: `msg_${Date.now()}`,
            role: 'assistant',
            content: `❌ **Error**\n\n${serverMessage.message}`,
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, errorMessage]);
        }
        
        handleErrorMessage(serverMessage);
        break;
        
      default:
        console.warn('[useChat] Unknown message type:', serverMessage);
    }
  }, [addAssistantMessage, addAnalysisMessage, addDeploymentCompleteMessage, handleErrorMessage, navigate]);
  
  useEffect(() => {
    const unsubscribe = onMessage((serverMessage: ServerMessage) => {
      handleServerMessage(serverMessage);
    });
    
    return unsubscribe;
  }, [onMessage, handleServerMessage]);
  
  // ========================================================================
  // Public Methods
  // ========================================================================
  
  const sendMessage = useCallback((content: string, files?: File[] | Record<string, any>) => {
    // Determine if files is actually files or context
    const isFileArray = Array.isArray(files) && files.length > 0 && files[0] instanceof File;
    const contextData = isFileArray ? undefined : files as Record<string, any> | undefined;
    const uploadedFiles = isFileArray ? files as File[] : undefined;

    // Add user message to UI
    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: uploadedFiles && uploadedFiles.length > 0 
        ? `${content}\n\n📎 Attached: ${uploadedFiles.map(f => f.name).join(', ')}`
        : content,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);

    // TODO: Handle file upload to backend
    if (uploadedFiles && uploadedFiles.length > 0) {
      console.log('[useChat] Files to upload:', uploadedFiles.map(f => f.name));
      // Future: Upload files to backend and get URLs
    }
    
    // Send to backend
    const success = wsSendMessage({
      type: 'message',
      message: content,
      context: contextData,
    });
    
    if (!success) {
      toast({
        title: 'Message Queued',
        description: 'Your message will be sent when connection is restored.',
      });
    }
  }, [wsSendMessage, toast]);
  
  /**
   * Send structured data to backend (for env vars, etc.)
   */
  const sendStructuredMessage = useCallback((type: string, data: any) => {
    if (!isConnected) {
      console.warn('[useChat] Not connected, cannot send structured message');
      return;
    }
    
    console.log(`[useChat] Sending structured message: ${type}`, data);
    
    wsSendMessage({
      type,
      ...data,
    });
  }, [isConnected, wsSendMessage]);
  
  const clearMessages = useCallback(() => {
    setMessages([]);
    setIsTyping(false);
  }, []);
  
  // ========================================================================
  // Connection Status Handling
  // ========================================================================
  
  useEffect(() => {
    if (connectionStatus.state === 'error') {
      // Reset typing state on connection error
      setIsTyping(false);
      toast({
        title: 'Connection Error',
        description: connectionStatus.error || 'Failed to connect to server',
        variant: 'destructive',
      });
    } else if (connectionStatus.state === 'reconnecting') {
      // Reset typing state when reconnecting
      setIsTyping(false);
      toast({
        title: 'Reconnecting...',
        description: `Attempt ${connectionStatus.reconnectAttempt || 1}`,
      });
    } else if (connectionStatus.state === 'connected' && connectionStatus.reconnectAttempt) {
      // Successfully reconnected
      console.log('[useChat] ✅ Successfully reconnected!');
      toast({
        title: 'Reconnected!',
        description: 'Connection restored.',
      });
    }
  }, [connectionStatus, toast]);
  
  // ========================================================================
  // Return
  // ========================================================================
  
  return {
    messages,
    isConnected,
    isTyping,
    sendMessage,
    clearMessages,
    connectionStatus,
    sendStructuredMessage,
    connect: () => console.log('[useChat] connect() is handled by WebSocketProvider'),
    disconnect: () => console.log('[useChat] disconnect() is handled by WebSocketProvider'),
  };
};

// ========================================================================
// Helper Functions
// ========================================================================

function formatAnalysisMessage(data: any): string {
  return `**Analysis Complete** ✅\n\n${data.summary || 'No summary available'}`;
}

function formatDeploymentComplete(data: any): string {
  return `**Deployment Complete!** 🎉\n\nYour app is now live at:\n${data.url}`;
}
