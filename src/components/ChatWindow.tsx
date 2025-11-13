import { useEffect, useRef, useState } from "react";
import { X, Minus, Sparkles, Copy, Check, WifiOff, Loader2, Maximize2 } from "lucide-react";
import confetti from "canvas-confetti";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import { useChat } from "@/hooks/useChat";
import type { MessageAction } from "@/types/websocket";

interface ChatWindowProps {
  onClose: () => void;
  initialMessage?: string;
}

const ChatWindow = ({ onClose, initialMessage }: ChatWindowProps) => {
  const { 
    messages, 
    isConnected, 
    isTyping, 
    connectionStatus,
    sendMessage,
    sendStructuredMessage,
    activeDeployment, // ✅ PHASE 1.2: Get deployment state
  } = useChat();
  
  const [isMinimized, setIsMinimized] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const isReconnecting = connectionStatus.state === 'reconnecting';
  
  // Debug: Log ChatWindow state
  useEffect(() => {
    console.log('[ChatWindow] isConnected:', isConnected, 'isTyping:', isTyping, 'disabled will be:', !isConnected || isTyping);
  }, [isConnected, isTyping]);

  // Handle initial message from CTA buttons
  useEffect(() => {
    if (initialMessage && messages.length === 0) {
      sendMessage(initialMessage);
    }
  }, [initialMessage]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const triggerConfetti = () => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ["#3b82f6", "#8b5cf6", "#06b6d4"],
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const handleActionClick = (action: MessageAction) => {
    if (action.action) {
      sendMessage(action.action);
    } else if (action.url) {
      window.open(action.url, '_blank');
    }
  };

  const handleQuickAction = (action: string) => {
    sendMessage(action);
  };

  // Get connection status display
  const getConnectionStatusText = () => {
    switch (connectionStatus.state) {
      case 'connecting':
        return 'Connecting...';
      case 'connected':
        return 'Online • Ready to help';
      case 'reconnecting':
        return `Reconnecting (${connectionStatus.reconnectAttempt || 1})...`;
      case 'disconnected':
        return 'Offline';
      case 'error':
        return 'Connection Error';
      default:
        return 'Initializing...';
    }
  };

  const getConnectionIndicatorColor = () => {
    switch (connectionStatus.state) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
      case 'reconnecting':
        return 'bg-yellow-500 animate-pulse';
      case 'error':
      case 'disconnected':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div
      className={`
        fixed
        bg-background/95 backdrop-blur-xl
        border border-[rgba(139,92,246,0.3)]
        shadow-2xl
        flex flex-col
        transition-all duration-300 ease-in-out
        ${isMaximized 
          ? 'inset-4 rounded-2xl z-[100]' 
          : isMinimized 
            ? 'bottom-5 right-5 w-[400px] h-[60px] rounded-2xl z-30' 
            : 'bottom-5 right-5 w-[400px] h-[600px] rounded-2xl z-30'
        }
        animate-in slide-in-from-bottom-4 fade-in duration-300
        max-md:inset-5 max-md:max-w-none max-md:h-[calc(100vh-40px)] max-md:z-[100]
        group
      `}
      style={!isMaximized && !isMinimized ? { 
        resize: 'both',
        minWidth: '350px',
        minHeight: '400px',
        maxWidth: '90vw',
        maxHeight: '90vh',
        overflow: 'hidden'
      } : {}}
    >
      {/* Header */}
      <div className="relative border-b border-[rgba(139,92,246,0.3)] bg-gradient-to-r from-[#8b5cf6]/10 to-[#06b6d4]/10">
        <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-[#8b5cf6] to-[#06b6d4]" />
        
        {/* Connection Status Banner */}
        {!isConnected && !isMinimized && (
          <div className="border-b border-border">
            {isReconnecting ? (
              <div className="bg-yellow-500/10 border-b border-yellow-500/30 px-4 py-1.5 flex items-center justify-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin text-yellow-400" />
                <span className="text-xs text-yellow-400">
                  Reconnecting... {connectionStatus.reconnectAttempt ? `(Attempt ${connectionStatus.reconnectAttempt})` : ''}
                </span>
              </div>
            ) : (
              <div className="bg-red-500/10 border-b border-red-500/30 px-4 py-1.5 flex items-center justify-center gap-2">
                <WifiOff className="w-3 h-3 text-red-400" />
                <span className="text-xs text-red-400">
                  Disconnected from server
                </span>
              </div>
            )}
          </div>
        )}
        
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Sparkles className="w-6 h-6 text-[hsl(var(--secondary))]" />
              <span className={`absolute -top-1 -right-1 w-3 h-3 ${getConnectionIndicatorColor()} rounded-full border-2 border-background`} />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">ServerGem AI Assistant</h3>
              <p className="text-xs text-muted-foreground flex items-center gap-2">
                {connectionStatus.state === 'connecting' && <Loader2 className="w-3 h-3 animate-spin" />}
                {connectionStatus.state === 'error' && <WifiOff className="w-3 h-3" />}
                {getConnectionStatusText()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setIsMaximized(!isMaximized);
                setIsMinimized(false);
              }}
              className="p-2 hover:bg-accent rounded-lg transition-colors"
              aria-label={isMaximized ? "Restore" : "Fullscreen"}
              title={isMaximized ? "Restore size" : "Maximize to fullscreen"}
            >
              <Maximize2 size={18} />
            </button>
            <button
              onClick={() => {
                setIsMinimized(!isMinimized);
                setIsMaximized(false);
              }}
              className="p-2 hover:bg-accent rounded-lg transition-colors"
              aria-label="Minimize"
              title="Minimize chat"
            >
              <Minus size={18} />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-accent rounded-lg transition-colors"
              aria-label="Close"
              title="Close chat"
            >
              <X size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      {!isMinimized && (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#3b82f6] to-[#8b5cf6] flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h4 className="text-lg font-semibold mb-2">Welcome to ServerGem!</h4>
                  <p className="text-sm text-muted-foreground mb-6">
                    I can help you deploy to Cloud Run in minutes.
                  </p>
                </div>
                <div className="space-y-2 w-full max-w-xs">
                  <button
                    onClick={() => handleQuickAction("I want to deploy my app to Cloud Run")}
                    className="w-full px-4 py-3 bg-accent/10 hover:bg-accent/20 border border-accent/30 rounded-lg text-sm font-medium transition-colors text-left"
                  >
                    🚀 Deploy my app
                  </button>
                  <button
                    onClick={() => handleQuickAction("Help me debug a deployment error")}
                    className="w-full px-4 py-3 bg-accent/10 hover:bg-accent/20 border border-accent/30 rounded-lg text-sm font-medium transition-colors text-left"
                  >
                    🔧 Debug deployment
                  </button>
                  <button
                    onClick={() => handleQuickAction("Optimize my Cloud Run costs")}
                    className="w-full px-4 py-3 bg-accent/10 hover:bg-accent/20 border border-accent/30 rounded-lg text-sm font-medium transition-colors text-left"
                  >
                    💰 Optimize costs
                  </button>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <div key={message.id}>
                    <ChatMessage 
                      message={message}
                      sendStructuredMessage={sendStructuredMessage}
                      activeDeployment={activeDeployment} // ✅ PHASE 1.2: Pass deployment state
                      onEnvSubmit={(envVars) => {
                        // Send structured env vars data to backend via WebSocket
                        sendStructuredMessage('env_vars_uploaded', {
                          variables: envVars.map(env => ({
                            key: env.key,
                            value: env.value,
                            isSecret: env.isSecret
                          })),
                          count: envVars.length
                        });
                      }}
                    />
                    {message.deploymentUrl && (
                      <div className="flex items-center gap-2 mb-4 ml-10">
                        <code className="flex-1 px-3 py-2 bg-accent/30 border border-[rgba(139,92,246,0.2)] rounded-lg text-sm text-[#06b6d4] font-mono">
                          {message.deploymentUrl}
                        </code>
                        <button
                          onClick={() => copyToClipboard(message.deploymentUrl!)}
                          className="p-2 bg-accent/50 hover:bg-accent rounded-lg transition-colors"
                          aria-label="Copy URL"
                        >
                          {copiedUrl ? (
                            <Check size={16} className="text-green-500" />
                          ) : (
                            <Copy size={16} />
                          )}
                        </button>
                      </div>
                    )}
                    {message.actions && message.actions.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-4 ml-10">
                        {message.actions.map((action) => (
                          <button
                            key={action.id}
                            onClick={() => handleActionClick(action)}
                            className="px-4 py-2 bg-accent/10 hover:bg-accent/20 border border-accent/30 rounded-lg text-sm font-medium transition-colors"
                          >
                            {action.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {isTyping && (
                  <div className="flex items-start gap-2">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[hsl(var(--secondary))] to-[hsl(var(--accent))] flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-card/80 border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-primary rounded-full animate-pulse" style={{ animationDelay: '0s' }} />
                        <span className="w-2 h-2 bg-primary rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                        <span className="w-2 h-2 bg-primary rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <ChatInput 
            onSendMessage={sendMessage} 
            disabled={!isConnected || isTyping || isReconnecting} 
          />
        </>
      )}

      {/* Resize Handle Indicator */}
      {!isMaximized && !isMinimized && (
        <div className="resize-handle-indicator" />
      )}
    </div>
  );
};

export default ChatWindow;
