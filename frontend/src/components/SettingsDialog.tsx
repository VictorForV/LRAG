/**
 * Settings Dialog Component
 */

import { useState, useEffect } from 'react';
import { Settings } from 'lucide-react';
import { authApi } from '../api/auth';
import type { UserSettings, UserSettingsUpdate } from '../api/auth';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/Dialog';

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form fields
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [embeddingApiKey, setEmbeddingApiKey] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [audioModel, setAudioModel] = useState('');
  const [proxyHost, setProxyHost] = useState('');
  const [proxyPort, setProxyPort] = useState('');
  const [proxyUsername, setProxyUsername] = useState('');
  const [proxyPassword, setProxyPassword] = useState('');

  // Load settings on mount
  useEffect(() => {
    if (open) {
      loadSettings();
    }
  }, [open]);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await authApi.getSettings();
      setSettings(data);
      // Initialize form with current values (API keys are masked)
      setLlmModel(data.llm_model || '');
      setEmbeddingModel(data.embedding_model || '');
      setAudioModel(data.audio_model || '');
      setProxyHost(data.http_proxy_host || '');
      setProxyPort(data.http_proxy_port?.toString() || '');
      setProxyUsername(data.http_proxy_username || '');
      setLlmApiKey(''); // Don't show current API keys and passwords
      setEmbeddingApiKey('');
      setProxyPassword('');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load settings';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    const updateData: UserSettingsUpdate = {};
    if (llmApiKey) updateData.llm_api_key = llmApiKey;
    if (llmModel) updateData.llm_model = llmModel;
    if (embeddingApiKey) updateData.embedding_api_key = embeddingApiKey;
    if (embeddingModel) updateData.embedding_model = embeddingModel;
    if (audioModel) updateData.audio_model = audioModel;
    if (proxyHost) updateData.http_proxy_host = proxyHost;
    if (proxyPort) updateData.http_proxy_port = parseInt(proxyPort);
    if (proxyUsername) updateData.http_proxy_username = proxyUsername;
    if (proxyPassword) updateData.http_proxy_password = proxyPassword;

    try {
      await authApi.updateSettings(updateData);
      setSuccess(true);
      // Reload settings
      await loadSettings();
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save settings';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setSuccess(false);
    setError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </DialogTitle>
          <DialogDescription>
            Configure API keys, models, and database connection
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="py-8 text-center text-muted-foreground">Loading settings...</div>
        ) : error ? (
          <div className="py-4">
            <div className="mb-4 p-4 bg-destructive/10 border border-destructive text-destructive rounded-md">
              {error}
            </div>
            <div className="p-4 bg-muted rounded-md text-sm">
              <p className="font-semibold mb-2">Make sure your .env file exists with:</p>
              <pre className="text-xs overflow-x-auto">
                DATABASE_URL=postgresql://user:pass@localhost:5432/rag_kb
                LLM_API_KEY=your-api-key
                LLM_MODEL=anthropic/claude-haiku-4.5
                EMBEDDING_MODEL=text-embedding-3-small
              </pre>
            </div>
          </div>
        ) : (
          <div className="space-y-6 px-6 py-4">
            {/* Success Message */}
            {success && (
              <div className="p-3 bg-green-500/10 border border-green-500 text-green-600 rounded-md text-sm">
                ✅ Settings saved successfully!
              </div>
            )}

            {/* API Keys */}
            <div>
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                🔑 API Keys
              </h3>
              <div className="space-y-3">
                <div>
                  <label htmlFor="llm-api-key" className="text-sm font-medium">
                    LLM API Key
                  </label>
                  <Input
                    id="llm-api-key"
                    type="password"
                    placeholder="Enter new LLM API key (leave empty to keep current)"
                    value={llmApiKey}
                    onChange={(e) => setLlmApiKey(e.target.value)}
                    className="mt-1"
                  />
                  {settings && settings.llm_api_key && (
                    <p className="text-xs text-green-600 mt-1">✅ Configured</p>
                  )}
                </div>
                <div>
                  <label htmlFor="embedding-api-key" className="text-sm font-medium">
                    Embedding API Key
                  </label>
                  <Input
                    id="embedding-api-key"
                    type="password"
                    placeholder="Enter new embedding API key (leave empty to keep current)"
                    value={embeddingApiKey}
                    onChange={(e) => setEmbeddingApiKey(e.target.value)}
                    className="mt-1"
                  />
                  {settings && settings.embedding_api_key && (
                    <p className="text-xs text-green-600 mt-1">✅ Configured</p>
                  )}
                </div>
              </div>
            </div>

            {/* Models */}
            <div>
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                🤖 Models
              </h3>
              <div className="space-y-3">
                <div>
                  <label htmlFor="llm-model" className="text-sm font-medium">
                    LLM Model
                  </label>
                  <Input
                    id="llm-model"
                    list="llm-models-list"
                    placeholder="anthropic/claude-haiku-4.5"
                    value={llmModel}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="mt-1"
                  />
                  <datalist id="llm-models-list">
                    <option value="anthropic/claude-sonnet-4.5" />
                    <option value="anthropic/claude-haiku-4.5" />
                    <option value="anthropic/claude-opus-4" />
                    <option value="openai/gpt-4o" />
                    <option value="openai/gpt-4o-mini" />
                    <option value="openai/o1" />
                    <option value="google/gemini-2.0-flash-exp" />
                    <option value="meta-llama/llama-3.3-70b-instruct" />
                    <option value="qwen/qwen-2.5-72b-instruct" />
                  </datalist>
                  {settings && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {settings.llm_model || 'Not set'}
                    </p>
                  )}
                </div>
                <div>
                  <label htmlFor="embedding-model" className="text-sm font-medium">
                    Embedding Model
                  </label>
                  <Input
                    id="embedding-model"
                    list="embedding-models-list"
                    placeholder="text-embedding-3-small"
                    value={embeddingModel}
                    onChange={(e) => setEmbeddingModel(e.target.value)}
                    className="mt-1"
                  />
                  <datalist id="embedding-models-list">
                    <option value="openai/text-embedding-3-small" />
                    <option value="openai/text-embedding-3-large" />
                    <option value="qwen/qwen3-embedding-8b" />
                    <option value="text-embedding-004" />
                    <option value="voyage-3" />
                  </datalist>
                  {settings && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {settings.embedding_model || 'Not set'}
                      {settings.embedding_dimension && ` (dim: ${settings.embedding_dimension})`}
                    </p>
                  )}
                </div>
                <div>
                  <label htmlFor="audio-model" className="text-sm font-medium">
                    Audio Model
                  </label>
                  <Input
                    id="audio-model"
                    placeholder="openai/gpt-audio-mini"
                    value={audioModel}
                    onChange={(e) => setAudioModel(e.target.value)}
                    className="mt-1"
                  />
                  {settings && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {settings.audio_model || 'Not set'}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* HTTP Proxy */}
            <div>
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                🌐 HTTP Proxy (для OpenRouter)
              </h3>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="proxy-host" className="text-sm font-medium">
                      Proxy Host
                    </label>
                    <Input
                      id="proxy-host"
                      placeholder="178.173.248.119"
                      value={proxyHost}
                      onChange={(e) => setProxyHost(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label htmlFor="proxy-port" className="text-sm font-medium">
                      Port
                    </label>
                    <Input
                      id="proxy-port"
                      type="number"
                      placeholder="23627"
                      value={proxyPort}
                      onChange={(e) => setProxyPort(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="proxy-username" className="text-sm font-medium">
                      Username
                    </label>
                    <Input
                      id="proxy-username"
                      placeholder="username"
                      value={proxyUsername}
                      onChange={(e) => setProxyUsername(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label htmlFor="proxy-password" className="text-sm font-medium">
                      Password
                    </label>
                    <Input
                      id="proxy-password"
                      type="password"
                      placeholder="password"
                      value={proxyPassword}
                      onChange={(e) => setProxyPassword(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>
                {settings && settings.http_proxy_host && (
                  <p className="text-xs text-green-600">
                    ✅ Configured: {settings.http_proxy_host}:{settings.http_proxy_port}
                  </p>
                )}
              </div>
            </div>

            {/* Current Status */}
            {settings && (
              <div className="p-3 bg-muted rounded-md text-sm">
                <p className="font-semibold mb-1">Current Status:</p>
                <ul className="text-xs space-y-1 text-muted-foreground">
                  <li>• LLM Provider: {settings.llm_provider || 'Not set'}</li>
                  <li>• LLM API Key: {settings.llm_api_key ? '✅ Configured' : '❌ Missing'}</li>
                  <li>• Embedding API Key: {settings.embedding_api_key ? '✅ Configured' : '❌ Missing'}</li>
                  <li>• LLM Model: {settings.llm_model || 'Not set'}</li>
                  <li>• Embedding Model: {settings.embedding_model || 'Not set'}</li>
                </ul>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={handleClose} disabled={saving}>
            Close
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={saving || loading}>
            {saving ? 'Saving...' : '💾 Save Settings'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
