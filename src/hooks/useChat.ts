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
import { DEPLOYMENT_STAGES } from '@/types/deployment'; // ✅ Import deployment stages

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
  
  // ✅ PHASE 1.2: State for deployment progress tracking
  const [activeDeployment, setActiveDeployment] = useState<{
    deploymentId: string;
    stages: any[];
    currentStage: string;
    overallProgress: number;
    status: 'deploying' | 'success' | 'failed';
    startTime: string;
  } | null>(null);
  
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
        // ✅ FIX: Don't show typing indicator for too long - will be cleared by first progress message
        setIsTyping(true);
        
        // Auto-clear typing after 3 seconds if no message arrives (prevents stuck bouncing dots)
        setTimeout(() => {
          setIsTyping(false);
        }, 3000);
        break;
      
      case 'deployment_started':
        console.log('[useChat] 🚀 Deployment started:', (serverMessage as any).deployment_id);
        setIsTyping(false); // Clear typing immediately
        
        const deploymentMsg = serverMessage as any;
        
        // ✅ PHASE 1.2: Initialize deployment tracking state
        setActiveDeployment({
          deploymentId: deploymentMsg.deployment_id,
          stages: DEPLOYMENT_STAGES.map(s => ({ ...s })), // Clone stages
          currentStage: 'repo_access',
          overallProgress: 0,
          status: 'deploying',
          startTime: new Date().toISOString()
        });
        
        // Add message with deployment logs component
        addAssistantMessage({
          content: `Starting deployment to Cloud Run...`,
          metadata: { 
            type: 'deployment_started', 
            deployment_id: deploymentMsg.deployment_id,
            showLogs: true // Flag to render DeploymentLogs component
          }
        });
        break;
      
      case 'deployment_progress':
        console.log('[useChat] 📊 Deployment progress:', (serverMessage as any).stage, (serverMessage as any).status);
        setIsTyping(false); // Clear typing indicator
        
        // ✅ PHASE 1.2: Update deployment state instead of adding individual messages
        const progressMsg = serverMessage as any;
        
        setActiveDeployment(prev => {
          if (!prev) {
            console.warn('[useChat] No active deployment to update');
            return prev;
          }

          // Update the specific stage
          const updatedStages = prev.stages.map(stage => {
            if (stage.id === progressMsg.stage) {
              return {
                ...stage,
                status: progressMsg.status,
                message: progressMsg.message,
                details: progressMsg.details ? Object.entries(progressMsg.details).map(([k, v]) => {
                  const key = k.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
                  return `${key}: ${v}`;
                }) : stage.details,
                endTime: progressMsg.status === 'success' || progressMsg.status === 'error' 
                  ? new Date().toISOString() 
                  : stage.endTime,
                startTime: stage.startTime || new Date().toISOString()
              };
            }
            return stage;
          });

          // Calculate duration for completed stages
          updatedStages.forEach(stage => {
            if ((stage.status === 'success' || stage.status === 'error') && stage.startTime && stage.endTime) {
              const start = new Date(stage.startTime).getTime();
              const end = new Date(stage.endTime).getTime();
              stage.duration = Math.round((end - start) / 1000);
            }
          });

          // Calculate overall progress
          const completedStages = updatedStages.filter(s => s.status === 'success').length;
          const overallProgress = Math.round((completedStages / updatedStages.length) * 100);

          return {
            ...prev,
            stages: updatedStages,
            currentStage: progressMsg.stage,
            overallProgress,
            status: progressMsg.status === 'error' ? 'failed' : prev.status
          };
        });

        // Update the deployment message in place (find and replace)
        setMessages(prevMessages => {
          const deploymentMsgIndex = prevMessages.findIndex(
            m => m.metadata?.type === 'deployment_started' && m.metadata?.showLogs
          );
          
          if (deploymentMsgIndex === -1) return prevMessages;

          const updatedMessages = [...prevMessages];
          updatedMessages[deploymentMsgIndex] = {
            ...updatedMessages[deploymentMsgIndex],
            metadata: {
              ...updatedMessages[deploymentMsgIndex].metadata,
              lastUpdate: new Date().toISOString() // Trigger re-render
            }
          };

          return updatedMessages;
        });
        break;
        
      case 'message':
        console.log('[useChat] Setting typing to false, adding message');
        setIsTyping(false);
        
        const msgData = serverMessage.data as any;
        
        // ✅ FIX: Check for env vars at BOTH data level AND top level of serverMessage
        const needsEnvVars = msgData?.request_env_vars || (serverMessage as any).request_env_vars;
        const detectedEnvVars = msgData?.detected_env_vars || (serverMessage as any).detected_env_vars || [];
        
        if (needsEnvVars) {
          console.log('[useChat] ✅ Analysis complete, REQUESTING ENV VARS!');
          console.log('[useChat] Detected env vars:', detectedEnvVars);
          
          addAssistantMessage({
            content: msgData.content,
            metadata: { 
              type: 'analysis_with_env_request',
              request_env_vars: true,
              detected_env_vars: detectedEnvVars
            }
          });
          
          // Trigger env vars UI
          sonnerToast.info('Environment Variables Required', {
            description: `Please provide ${detectedEnvVars.length} environment variable(s) to continue.`,
            duration: 5000,
          });
        } else {
          // Handle progress messages vs regular messages
          const isProgress = msgData?.metadata?.type === 'progress';
          
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
        
        // ✅ PHASE 1.2: Update deployment to success/failed status
        setActiveDeployment(prev => {
          if (!prev) return prev;
          
          return {
            ...prev,
            status: isSuccess ? 'success' : 'failed',
            overallProgress: 100
          };
        });
        
        // Update the deployment message one final time
        setMessages(prevMessages => {
          const deploymentMsgIndex = prevMessages.findIndex(
            m => m.metadata?.type === 'deployment_started' && m.metadata?.showLogs
          );
          
          if (deploymentMsgIndex === -1) return prevMessages;

          const updatedMessages = [...prevMessages];
          updatedMessages[deploymentMsgIndex] = {
            ...updatedMessages[deploymentMsgIndex],
            metadata: {
              ...updatedMessages[deploymentMsgIndex].metadata,
              lastUpdate: new Date().toISOString(),
              deploymentUrl: deployData?.url,
              error: deployData?.error
            }
          };

          return updatedMessages;
        });
        
        // Add summary message after logs
        const completeEmoji = isSuccess ? '🎉' : '❌';
        const completeTitle = isSuccess ? 'Deployment Successful!' : 'Deployment Failed';
        
        let completeContent = `## ${completeEmoji} ${completeTitle}\n\n`;
        completeContent += deployData?.message || 'Deployment process completed.';
        
        if (deployData?.url) {
          completeContent += `\n\n### 🌐 Your Application is Live!\n\n`;
          completeContent += `**URL:** [${deployData.url}](${deployData.url})\n\n`;
          completeContent += `Click the link above to view your deployed application.`;
        }
        
        if (deployData?.error) {
          completeContent += `\n\n### ❌ Error Details\n\n\`\`\`\n${deployData.error}\n\`\`\``;
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
    activeDeployment, // ✅ PHASE 1.2: Expose deployment state
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
