/**
 * Dashboard - My Deployments Overview
 * Shows all user's deployed services with real-time status
 */

import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Rocket, 
  ExternalLink, 
  Settings, 
  RotateCw, 
  Trash2,
  Activity,
  Clock,
  TrendingUp,
  Plus,
  Globe,
  Zap,
  Loader2,
  ArrowLeft,
  Home
} from 'lucide-react';
import { toast } from 'sonner';
import { useDeployments } from '@/hooks/useDeployments';
import { formatDistanceToNow } from 'date-fns';

const Dashboard = () => {
  const navigate = useNavigate();
  const { deployments, isLoading, error, deleteDeployment } = useDeployments();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'live': return 'bg-green-500';
      case 'deploying': return 'bg-yellow-500 animate-pulse';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'live': return 'Live';
      case 'deploying': return 'Deploying';
      case 'error': return 'Error';
      default: return 'Unknown';
    }
  };

  const handleRedeploy = async (deploymentId: string, name: string) => {
    toast.info(`Redeploying ${name}...`);
    // Implementation in Phase 3
  };

  const handleDelete = async (deploymentId: string, name: string) => {
    if (confirm(`Delete ${name}? This cannot be undone.`)) {
      try {
        await deleteDeployment(deploymentId);
      } catch (err) {
        // Error already shown by hook
      }
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch {
      return dateString;
    }
  };

  if (error) {
    return (
      <DashboardLayout>
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <Card className="p-8 text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Back Navigation */}
        <div className="mb-6">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => navigate('/')}
            className="gap-2"
          >
            <Home className="w-4 h-4" />
            Back to Home
          </Button>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">My Deployments</h1>
            <p className="text-muted-foreground">
              Manage your ServerGem deployments
            </p>
          </div>
          <Button onClick={() => navigate('/deploy')} className="gap-2" size="lg">
            <Plus className="w-5 h-5" />
            Deploy New App
          </Button>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active Services</p>
                  <p className="text-2xl font-bold">{deployments.filter(d => d.status === 'live').length}</p>
                </div>
                <Rocket className="w-8 h-8 text-primary" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Requests Today</p>
                  <p className="text-2xl font-bold">
                    {deployments.reduce((sum, d) => sum + d.request_count, 0)}
                  </p>
                </div>
                <Activity className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg Uptime</p>
                  <p className="text-2xl font-bold">99.9%</p>
                </div>
                <TrendingUp className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">This Month</p>
                  <p className="text-2xl font-bold">$0.00</p>
                </div>
                <Zap className="w-8 h-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Deployments List */}
        {isLoading ? (
          <Card className="p-12">
            <div className="flex flex-col items-center justify-center space-y-4">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Loading deployments...</p>
            </div>
          </Card>
        ) : deployments.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Rocket className="w-16 h-16 text-muted-foreground mb-4" />
              <h3 className="text-xl font-semibold mb-2">No deployments yet</h3>
              <p className="text-muted-foreground mb-6 text-center max-w-md">
                Deploy your first app to ServerGem in just 3 minutes. No Google Cloud setup required!
              </p>
              <Button onClick={() => navigate('/deploy')} className="gap-2" size="lg">
                <Rocket className="w-5 h-5" />
                Deploy Your First App
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {deployments.map((deployment) => (
              <Card key={deployment.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`w-3 h-3 rounded-full ${getStatusColor(deployment.status)}`} />
                        <CardTitle className="text-xl">{deployment.service_name}</CardTitle>
                      </div>
                      <CardDescription className="flex items-center gap-2">
                        <Globe className="w-4 h-4" />
                        <a 
                          href={deployment.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-primary hover:underline"
                        >
                          {deployment.url}
                        </a>
                        <ExternalLink className="w-3 h-3" />
                      </CardDescription>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(deployment.url, '_blank')}
                        disabled={deployment.status !== 'live'}
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRedeploy(deployment.id, deployment.service_name)}
                        disabled={deployment.status === 'deploying'}
                      >
                        <RotateCw className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/dashboard/settings`)}
                      >
                        <Settings className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(deployment.id, deployment.service_name)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Status</p>
                      <p className="text-sm font-medium">{getStatusLabel(deployment.status)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Deployed</p>
                      <p className="text-sm font-medium flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDate(deployment.created_at)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Requests</p>
                      <p className="text-sm font-medium">{deployment.request_count}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Memory</p>
                      <p className="text-sm font-medium">{deployment.memory}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
