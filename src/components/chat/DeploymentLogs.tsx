/**
 * Deployment Logs Component
 * Collapsible log viewer for deployment progress (like Lovable's "show all" button)
 * Bismillah ar-Rahman ar-Rahim
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DeploymentStage, DeploymentStageStatus } from '@/types/deployment';
import { cn } from '@/lib/utils';

interface DeploymentLogsProps {
  stages: DeploymentStage[];
  currentStage: string;
  overallProgress: number;
  status: 'deploying' | 'success' | 'failed';
}

export function DeploymentLogs({ stages, currentStage, overallProgress, status }: DeploymentLogsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const getStatusIcon = (stageStatus: DeploymentStageStatus) => {
    switch (stageStatus) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'in-progress':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-slate-500" />;
    }
  };

  const getProgressColor = () => {
    if (status === 'success') return 'bg-green-500';
    if (status === 'failed') return 'bg-red-500';
    return 'bg-blue-500';
  };

  return (
    <div className="w-full border border-border/50 rounded-lg overflow-hidden bg-background/50 backdrop-blur-sm">
      {/* Header - Always Visible */}
      <div className="flex items-center justify-between p-3 border-b border-border/50 bg-muted/30">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative w-10 h-10">
            <svg className="w-10 h-10 transform -rotate-90">
              <circle
                cx="20"
                cy="20"
                r="16"
                stroke="currentColor"
                strokeWidth="3"
                fill="none"
                className="text-muted"
              />
              <circle
                cx="20"
                cy="20"
                r="16"
                stroke="currentColor"
                strokeWidth="3"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 16}`}
                strokeDashoffset={`${2 * Math.PI * 16 * (1 - overallProgress / 100)}`}
                className={cn("transition-all duration-500", getProgressColor())}
                strokeLinecap="round"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold">
              {overallProgress}%
            </span>
          </div>
          
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-foreground">
              {status === 'success' ? '✅ Deployment Complete' : 
               status === 'failed' ? '❌ Deployment Failed' : 
               '🚀 Deploying to Cloud Run'}
            </h3>
            <p className="text-xs text-muted-foreground">
              {stages.filter(s => s.status === 'success').length} of {stages.length} stages complete
            </p>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-8 px-2 hover:bg-muted"
        >
          <span className="text-xs mr-1">
            {isExpanded ? 'Hide logs' : 'Show all'}
          </span>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Expandable Logs Section */}
      {isExpanded && (
        <div className="p-3 space-y-2 max-h-96 overflow-y-auto">
          {stages.map((stage, index) => {
            const isActive = stage.id === currentStage;
            const isCompleted = stage.status === 'success' || stage.status === 'error';

            return (
              <div
                key={stage.id}
                className={cn(
                  "p-3 rounded-md border transition-all duration-200",
                  isActive && "border-primary/50 bg-primary/5",
                  !isActive && isCompleted && "border-border/30 bg-muted/20",
                  !isActive && !isCompleted && "border-border/20 bg-background/50 opacity-60"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {getStatusIcon(stage.status)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{stage.icon}</span>
                      <span className={cn(
                        "text-sm font-medium",
                        isActive && "text-primary",
                        stage.status === 'success' && "text-green-600",
                        stage.status === 'error' && "text-red-600"
                      )}>
                        {stage.label}
                      </span>
                      {stage.duration && (
                        <span className="text-xs text-muted-foreground">
                          ({stage.duration}s)
                        </span>
                      )}
                    </div>

                    {stage.message && (
                      <p className="text-xs text-muted-foreground mb-2">
                        {stage.message}
                      </p>
                    )}

                    {stage.details && stage.details.length > 0 && (
                      <ul className="space-y-1 mt-2">
                        {stage.details.map((detail, idx) => (
                          <li key={idx} className="text-xs text-muted-foreground flex items-start gap-1.5">
                            <span className="text-primary mt-0.5">•</span>
                            <span className="flex-1">{detail}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
