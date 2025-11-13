import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import { User, Sparkles, Loader2 } from "lucide-react";
import type { ChatMessage } from "@/types/websocket";
import { EnvVariablesInput, EnvVariable } from "./chat/EnvVariablesInput";
import { DeploymentLogs } from "./chat/DeploymentLogs"; // ✅ PHASE 1.2: Import DeploymentLogs

interface ChatMessageProps {
  message: ChatMessage;
  onEnvSubmit?: (envVars: EnvVariable[]) => void;
  sendStructuredMessage?: (type: string, data: any) => void;
  activeDeployment?: any; // ✅ PHASE 1.2: Add deployment state
}

const ChatMessageComponent = ({ message, onEnvSubmit, sendStructuredMessage, activeDeployment }: ChatMessageProps) => {
  const isUser = message.role === "user";
  const time = message.timestamp.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });

  // ✅ FIX: Check for env vars request with explicit metadata flag
  const requestsEnvVars = !isUser && (
    message.metadata?.type === 'analysis_with_env_request' ||
    message.metadata?.request_env_vars === true
  ) && !(
    // Don't show upload UI if message is confirming receipt of env vars
    message.content.toLowerCase().includes('received your environment') ||
    message.content.toLowerCase().includes('configuration received successfully') ||
    message.content.toLowerCase().includes('perfect') ||
    message.content.toLowerCase().includes('✅ configuration')
  );
  
  console.log('[ChatMessage] requestsEnvVars:', requestsEnvVars, 'metadata:', message.metadata);
  
  // Check if this is a progress message (should show with loader)
  const isProgressMessage = message.metadata?.type === 'progress';
  
  // ✅ PHASE 1.2: Check if this message should render deployment logs
  const showDeploymentLogs = message.metadata?.type === 'deployment_started' && message.metadata?.showLogs;

  return (
    <div
      className={`
        flex gap-2 animate-in fade-in slide-in-from-bottom-2 duration-200
        ${isUser ? "flex-row-reverse" : "flex-row"}
      `}
    >
      {/* Avatar */}
      <div
        className={`
          w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
          ${isUser
            ? "bg-gradient-to-br from-[#3b82f6] to-[#8b5cf6]"
            : "bg-gradient-to-br from-[#8b5cf6] to-[#06b6d4]"
          }
        `}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : isProgressMessage ? (
          <Loader2 className="w-4 h-4 text-white animate-spin" />
        ) : (
          <Sparkles className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Bubble */}
      <div className={`flex flex-col gap-1 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`
            rounded-2xl px-4 py-3
            ${isUser
              ? "bg-gradient-to-br from-[#3b82f6] to-[#8b5cf6] text-white rounded-tr-sm"
              : isProgressMessage 
                ? "bg-[rgba(30,41,59,0.6)] border border-[rgba(139,92,246,0.2)] text-gray-300 rounded-tl-sm"
                : "bg-[rgba(30,41,59,0.8)] border border-[rgba(139,92,246,0.3)] text-gray-100 rounded-tl-sm"
            }
          `}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || "");
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        className="rounded-lg !bg-[#1e1e1e] !p-4 !my-2"
                        {...props}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    ) : (
                      <code className="bg-[#1e1e1e] px-1.5 py-0.5 rounded text-[#06b6d4] font-mono text-xs" {...props}>
                        {children}
                      </code>
                    );
                  },
                  p: ({ children }) => <p className="mb-2 last:mb-0 text-sm leading-relaxed">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="text-sm">{children}</li>,
                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-bold mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        
        {/* ✅ PHASE 1.2: Render deployment logs if this is a deployment message */}
        {showDeploymentLogs && activeDeployment && (
          <div className="mt-3 w-full">
            <DeploymentLogs
              stages={activeDeployment.stages}
              currentStage={activeDeployment.currentStage}
              overallProgress={activeDeployment.overallProgress}
              status={activeDeployment.status}
            />
          </div>
        )}
        
        {/* Show env input if AI is requesting env vars */}
        {requestsEnvVars && onEnvSubmit && (
          <div className="mt-3 w-full max-w-2xl">
            <EnvVariablesInput 
              onEnvSubmit={onEnvSubmit}
              onSkip={() => onEnvSubmit([])}
              sendMessageToBackend={sendStructuredMessage}
            />
          </div>
        )}
        
        <span className="text-xs text-muted-foreground px-2">{time}</span>
      </div>
    </div>
  );
};

export default ChatMessageComponent;
