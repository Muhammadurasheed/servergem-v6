import { useState, useEffect } from 'react';
import { GitHubConnect } from '@/components/GitHubConnect';
import { RepoSelector } from '@/components/RepoSelector';
import { DeploymentProgress } from '@/components/DeploymentProgress';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Rocket, ArrowLeft, CheckCircle2, Loader2, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useGitHub } from '@/hooks/useGitHub';
import { useChat } from '@/hooks/useChat';

const Deploy = () => {
  const navigate = useNavigate();
  const { isConnected: isGitHubConnected } = useGitHub();
  const { 
    messages, 
    isConnected: isWSConnected, 
    isTyping, 
    sendMessage,
    connectionStatus 
  } = useChat();
  
  const [selectedRepo, setSelectedRepo] = useState<{ url: string; branch: string } | null>(null);
  const [deploymentUrl, setDeploymentUrl] = useState<string | undefined>();
  const [showDeployActions, setShowDeployActions] = useState(false);

  // Extract deployment URL from messages
  useEffect(() => {
    const completeMessage = messages.find(m => m.deploymentUrl);
    if (completeMessage?.deploymentUrl) {
      setDeploymentUrl(completeMessage.deploymentUrl);
    }
  }, [messages]);

  // Check if analysis is complete and waiting for deployment confirmation
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.content) {
      const content = lastMessage.content.toLowerCase();
      // Check for various deployment confirmation prompts
      const deploymentPrompts = [
        'are you ready to deploy',
        'would you like me to proceed',
        'ready to deploy',
        'proceed with the deployment',
        'shall i deploy',
        'deploy to cloud run?'
      ];
      
      const shouldShowActions = deploymentPrompts.some(prompt => 
        content.includes(prompt)
      );
      
      setShowDeployActions(shouldShowActions);
    }
  }, [messages]);

  const handleProceedDeployment = () => {
    if (!isWSConnected) {
      toast.error('Backend connection lost');
      return;
    }
    
    setShowDeployActions(false);
    sendMessage('yes', { action: 'confirm_deploy' });
    toast.success('Deployment started!');
  };

  const handleCancelDeployment = () => {
    setShowDeployActions(false);
    sendMessage('no', { action: 'cancel_deploy' });
    toast.info('Deployment cancelled');
  };

  const handleSelectRepo = async (repoUrl: string, branch: string) => {
    if (!isWSConnected) {
      toast.error('Backend connection is not available', {
        description: 'Please ensure the backend server is running at http://localhost:8000'
      });
      return;
    }

    setSelectedRepo({ url: repoUrl, branch });
    
    // Send deployment request via WebSocket
    const message = `I want to analyze and deploy this repository: ${repoUrl} (branch: ${branch})`;
    sendMessage(message, {
      action: 'deploy',
      repoUrl,
      branch,
      githubToken: localStorage.getItem('github_token')
    });
    
    toast.success(`Deployment initiated`, {
      description: 'Analyzing repository and preparing deployment...'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <div className="border-b border-border/50 bg-background/50 backdrop-blur-xl sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/')}
                className="gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
              <div className="flex items-center gap-2">
                <Rocket className="w-6 h-6 text-primary" />
                <h1 className="text-2xl font-bold">Deploy to Cloud Run</h1>
              </div>
            </div>
            
            {/* Backend Connection Status */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                connectionStatus.state === 'connected' ? 'bg-green-500' :
                connectionStatus.state === 'connecting' ? 'bg-yellow-500 animate-pulse' :
                'bg-red-500'
              }`} />
              <span className="text-xs text-muted-foreground">
                {connectionStatus.state === 'connected' ? 'Backend Online' : 
                 connectionStatus.state === 'connecting' ? 'Connecting...' : 
                 'Backend Offline'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Backend Connection Warning */}
          {!isWSConnected && (
            <Alert variant="destructive">
              <WifiOff className="h-4 w-4" />
              <AlertDescription>
                <strong>Backend Offline:</strong> Please start the backend server at http://localhost:8000
                <br />
                <code className="text-xs mt-1 block">cd backend && python app.py</code>
              </AlertDescription>
            </Alert>
          )}

          {/* Progress Steps */}
          <Card className="border-border/50 bg-background/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Deployment Steps</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isGitHubConnected ? 'bg-green-500 text-white' : 'bg-muted text-muted-foreground'}`}>
                    {isGitHubConnected ? <CheckCircle2 className="w-5 h-5" /> : '1'}
                  </div>
                  <span className={`text-sm ${isGitHubConnected ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                    Connect GitHub
                  </span>
                </div>
                <div className="flex-1 h-[2px] bg-border" />
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${selectedRepo ? 'bg-green-500 text-white' : 'bg-muted text-muted-foreground'}`}>
                    {selectedRepo ? <CheckCircle2 className="w-5 h-5" /> : '2'}
                  </div>
                  <span className={`text-sm ${selectedRepo ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                    Select Repository
                  </span>
                </div>
                <div className="flex-1 h-[2px] bg-border" />
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${deploymentUrl ? 'bg-green-500 text-white' : messages.length > 0 ? 'bg-yellow-500 text-white' : 'bg-muted text-muted-foreground'}`}>
                    {deploymentUrl ? <CheckCircle2 className="w-5 h-5" /> : messages.length > 0 ? <Loader2 className="w-5 h-5 animate-spin" /> : '3'}
                  </div>
                  <span className={`text-sm ${deploymentUrl || messages.length > 0 ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                    Deploy
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* GitHub Connection */}
          {!isGitHubConnected && <GitHubConnect />}

          {/* Repository Selector */}
          {isGitHubConnected && !selectedRepo && (
            <RepoSelector onSelectRepo={handleSelectRepo} />
          )}

          {/* Deployment Progress & Results */}
          {selectedRepo && (
            <>
              <DeploymentProgress 
                messages={messages}
                isTyping={isTyping}
                deploymentUrl={deploymentUrl}
              />
              
              {/* Deployment Action Buttons */}
              {showDeployActions && (
                <Card className="border-primary/20 bg-primary/5">
                  <CardContent className="pt-6">
                    <div className="flex flex-col items-center gap-4">
                      <p className="text-center text-muted-foreground">
                        Analysis complete! Ready to deploy to Cloud Run?
                      </p>
                      <div className="flex gap-3">
                        <Button
                          onClick={handleProceedDeployment}
                          size="lg"
                          className="gap-2"
                        >
                          <Rocket className="w-4 h-4" />
                          Deploy Now
                        </Button>
                        <Button
                          onClick={handleCancelDeployment}
                          variant="outline"
                          size="lg"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {/* Help Card - Only show if no repo selected */}
          {!selectedRepo && (
            <Card className="border-border/50 bg-background/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">How It Works</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-primary">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">Connect GitHub</p>
                    <p>Link your GitHub account with a Personal Access Token</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-primary">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">Select Repository</p>
                    <p>Choose any repo - we'll handle the deployment</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-primary">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">AI-Powered Deployment</p>
                    <p>ServerGem analyzes, builds, and deploys to *.servergem.app - no Google Cloud setup needed!</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default Deploy;
