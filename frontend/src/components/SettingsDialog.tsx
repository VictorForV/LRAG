/**
 * Settings Dialog Component
 */

import { useState, useEffect } from 'react';
import { Settings } from 'lucide-react';
import { settingsApi } from '../api';
import type { Settings as SettingsType, SettingsUpdate } from '../types';
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
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form fields
  const [apiKey, setApiKey] = useState('');
  const [chatModel, setChatModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [audioModel, setAudioModel] = useState('');
  const [databaseUrl, setDatabaseUrl] = useState('');

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
      const data = await settingsApi.get();
      setSettings(data);
      // Initialize form with current values (API key is not returned for security)
      setChatModel(data.llm_model || '');
      setEmbeddingModel(data.embedding_model || '');
      setAudioModel(data.audio_model || '');
      setApiKey(''); // Don't show current API key
      setDatabaseUrl(''); // Don't show current DB URL
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

    const updateData: SettingsUpdate = {};
    if (apiKey) updateData.llm_api_key = apiKey;
    if (chatModel) updateData.llm_model = chatModel;
    if (apiKey) updateData.embedding_api_key = apiKey;
    if (embeddingModel) updateData.embedding_model = embeddingModel;
    if (audioModel) updateData.audio_model = audioModel;
    if (databaseUrl) updateData.database_url = databaseUrl;

    try {
      await settingsApi.update(updateData);
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
                  <label htmlFor="api-key" className="text-sm font-medium">
                    API Key
                  </label>
                  <Input
                    id="api-key"
                    type="password"
                    placeholder="Enter new API key (leave empty to keep current)"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="mt-1"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for both LLM and embeddings
                  </p>
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
                  <label htmlFor="chat-model" className="text-sm font-medium">
                    Chat Model
                  </label>
                  <Input
                    id="chat-model"
                    placeholder="anthropic/claude-haiku-4.5"
                    value={chatModel}
                    onChange={(e) => setChatModel(e.target.value)}
                    className="mt-1"
                  />
                  {settings && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {settings.llm_model}
                    </p>
                  )}
                </div>
                <div>
                  <label htmlFor="embedding-model" className="text-sm font-medium">
                    Embedding Model
                  </label>
                  <Input
                    id="embedding-model"
                    placeholder="text-embedding-3-small"
                    value={embeddingModel}
                    onChange={(e) => setEmbeddingModel(e.target.value)}
                    className="mt-1"
                  />
                  {settings && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {settings.embedding_model} (dim: {settings.embedding_dimension})
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
                      Current: {settings.audio_model}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Database */}
            <div>
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                🗄️ Database
              </h3>
              <div className="space-y-3">
                <div>
                  <label htmlFor="database-url" className="text-sm font-medium">
                    Database URL
                  </label>
                  <Input
                    id="database-url"
                    type="password"
                    placeholder="postgresql://user:pass@localhost:5432/rag_kb"
                    value={databaseUrl}
                    onChange={(e) => setDatabaseUrl(e.target.value)}
                    className="mt-1 font-mono text-xs"
                  />
                  {settings && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Connected: {settings.database_name}
                      {settings.database_connected && ' ✅'}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Current Status */}
            {settings && (
              <div className="p-3 bg-muted rounded-md text-sm">
                <p className="font-semibold mb-1">Current Status:</p>
                <ul className="text-xs space-y-1 text-muted-foreground">
                  <li>• LLM: {settings.llm_provider}</li>
                  <li>• API Key: {settings.llm_api_key_configured ? '✅ Configured' : '❌ Missing'}</li>
                  <li>• Embedding Key: {settings.embedding_api_key_configured ? '✅ Configured' : '❌ Missing'}</li>
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
