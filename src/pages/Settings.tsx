/**
 * Settings Page
 * Account settings, preferences, and configurations
 */

import { DashboardLayout } from '@/components/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/hooks/useAuth';
import { useGitHub } from '@/hooks/useGitHub';
import { toast } from 'sonner';
import { ApiKeySettings } from '@/components/ApiKeySettings';
import { 
  User, 
  Github, 
  Bell, 
  Shield,
  Trash2,
  LogOut,
  CheckCircle2,
  XCircle,
  ArrowLeft
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Settings = () => {
  const { user, signOut } = useAuth();
  const { isConnected: isGitHubConnected, user: githubUser, disconnect: disconnectGitHub } = useGitHub();
  const navigate = useNavigate();

  const handleSaveProfile = () => {
    toast.success('Profile updated successfully!');
  };

  const handleDeleteAccount = () => {
    if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      toast.error('Account deletion - Contact support to proceed');
    }
  };

  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="flex items-center gap-4 mb-8">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold">Settings</h1>
        </div>

        {/* Profile Settings */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <User className="w-5 h-5" />
              <CardTitle>Profile</CardTitle>
            </div>
            <CardDescription>
              Manage your personal information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="display-name">Display Name</Label>
              <Input
                id="display-name"
                defaultValue={user?.displayName || ''}
                placeholder="Your name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                defaultValue={user?.email || ''}
                placeholder="your@email.com"
                disabled
              />
              <p className="text-xs text-muted-foreground">
                Contact support to change your email
              </p>
            </div>
            <Button onClick={handleSaveProfile}>Save Changes</Button>
          </CardContent>
        </Card>

        {/* GitHub Integration */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Github className="w-5 h-5" />
              <CardTitle>GitHub Integration</CardTitle>
            </div>
            <CardDescription>
              Manage your GitHub connection
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isGitHubConnected && githubUser ? (
              <div className="flex items-center justify-between p-4 rounded-lg border bg-accent/50">
                <div className="flex items-center gap-3">
                  <img 
                    src={githubUser.avatar_url} 
                    alt={githubUser.name}
                    className="w-10 h-10 rounded-full"
                  />
                  <div>
                    <p className="font-medium">{githubUser.name}</p>
                    <p className="text-sm text-muted-foreground">@{githubUser.login}</p>
                  </div>
                  <CheckCircle2 className="w-5 h-5 text-green-500 ml-2" />
                </div>
                <Button variant="destructive" size="sm" onClick={disconnectGitHub}>
                  Disconnect
                </Button>
              </div>
            ) : (
              <div className="flex items-center justify-between p-4 rounded-lg border">
                <div className="flex items-center gap-3">
                  <XCircle className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Not Connected</p>
                    <p className="text-sm text-muted-foreground">
                      Connect to deploy private repositories
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Connect GitHub
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* API Configuration */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>API Configuration</CardTitle>
            <CardDescription>
              Configure your Gemini API key for AI features
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ApiKeySettings />
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              <CardTitle>Notifications</CardTitle>
            </div>
            <CardDescription>
              Configure how you receive updates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Deployment notifications</p>
                <p className="text-sm text-muted-foreground">
                  Get notified when deployments complete
                </p>
              </div>
              <input type="checkbox" defaultChecked className="w-4 h-4" />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Usage alerts</p>
                <p className="text-sm text-muted-foreground">
                  Alert when approaching plan limits
                </p>
              </div>
              <input type="checkbox" defaultChecked className="w-4 h-4" />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Product updates</p>
                <p className="text-sm text-muted-foreground">
                  News about new features
                </p>
              </div>
              <input type="checkbox" className="w-4 h-4" />
            </div>
          </CardContent>
        </Card>

        {/* Security */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              <CardTitle>Security</CardTitle>
            </div>
            <CardDescription>
              Manage your account security
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button variant="outline">Change Password</Button>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-destructive/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-destructive" />
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
            </div>
            <CardDescription>
              Irreversible actions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg border border-destructive/50 bg-destructive/5">
              <div>
                <p className="font-medium">Delete Account</p>
                <p className="text-sm text-muted-foreground">
                  Permanently delete your account and all data
                </p>
              </div>
              <Button variant="destructive" onClick={handleDeleteAccount}>
                Delete Account
              </Button>
            </div>
            
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-medium">Sign Out</p>
                <p className="text-sm text-muted-foreground">
                  Sign out of your account
                </p>
              </div>
              <Button variant="outline" onClick={signOut} className="gap-2">
                <LogOut className="w-4 h-4" />
                Sign Out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Settings;
