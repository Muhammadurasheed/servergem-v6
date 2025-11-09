/**
 * WebSocket Context Provider
 * Maintains a single, persistent WebSocket connection across the entire app
 * Bismillah ar-Rahman ar-Rahim
 */

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { WebSocketClient } from '@/lib/websocket/WebSocketClient';
import { ConnectionStatus, ServerMessage, ClientMessage } from '@/types/websocket';
import { toast } from 'sonner';

interface WebSocketContextValue {
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  sendMessage: (message: ClientMessage) => boolean;
  onMessage: (handler: (message: ServerMessage) => void) => () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [client] = useState(() => {
    console.log('[WebSocketProvider] 🏗️ Creating WebSocketClient singleton');
    return new WebSocketClient();
  });
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    state: 'idle',
  });

  useEffect(() => {
    console.log('[WebSocketProvider] 🚀 Initializing app-level WebSocket connection');
    console.log('[WebSocketProvider] 🔍 Checking for duplicate mounts...');

    // Subscribe to connection changes
    const unsubscribe = client.onConnectionChange((status) => {
      console.log('[WebSocketProvider] Connection status:', status.state);
      setConnectionStatus(status);

      // FAANG-style: No toast spam. Let the subtle indicator in the UI show connection status.
      // Only show critical errors that require user action
      if (status.state === 'error' && status.error) {
        toast.error(`Connection Error: ${status.error}`, { duration: 3000 });
      }
    });

    // Connect immediately
    client.connect();

    // Cleanup only when app unmounts (not when components remount)
    return () => {
      console.log('[WebSocketProvider] 🔴 Provider unmounting - cleaning up WebSocket');
      console.log('[WebSocketProvider] 🔍 This should only happen once during app lifetime');
      unsubscribe();
      client.destroy();
    };
  }, [client]); // Only depend on client (which never changes due to useState)

  const sendMessage = useCallback((message: ClientMessage) => {
    return client.sendMessage(message);
  }, [client]);

  const onMessage = useCallback((handler: (message: ServerMessage) => void) => {
    return client.onMessage(handler);
  }, [client]);

  const value: WebSocketContextValue = {
    isConnected: connectionStatus.state === 'connected',
    connectionStatus,
    sendMessage,
    onMessage,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider');
  }
  return context;
}
