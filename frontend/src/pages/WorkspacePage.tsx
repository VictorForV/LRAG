/**
 * Workspace Page - Main workspace with chat, documents, and upload
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Plus,
  Trash2,
  Edit2,
  MessageSquare,
  FileText,
  Upload,
  Moon,
  Sun,
  Send,
  X,
  Check,
  AlertCircle,
} from 'lucide-react';
import { projectsApi, sessionsApi, messagesApi, documentsApi, chatApi } from '../api';
import type { Project, Session, Message, Document } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { useAppStore } from '../store/appStore';
import { estimateTokens } from '../lib/utils';

export default function WorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useAppStore();

  const [project, setProject] = useState<Project | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeTab, setActiveTab] = useState<'chat' | 'documents' | 'upload'>('chat');
  const [loading, setLoading] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const [uploadResults, setUploadResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingSessionTitle, setEditingSessionTitle] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Load project
  const loadProject = async () => {
    if (!projectId) return;
    try {
      const data = await projectsApi.get(projectId);
      setProject(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load project';
      setError(message);
    }
  };

  // Load sessions
  const loadSessions = async () => {
    if (!projectId) return;
    try {
      const data = await sessionsApi.list(projectId);
      setSessions(data);
    } catch (err: unknown) {
      console.error('Failed to load sessions:', err);
    }
  };

  // Load messages for current session
  const loadMessages = async (sessionId: string) => {
    try {
      const data = await messagesApi.list(sessionId);
      setMessages(data);
    } catch (err: unknown) {
      console.error('Failed to load messages:', err);
    }
  };

  // Load documents
  const loadDocuments = async () => {
    if (!projectId) return;
    try {
      const data = await documentsApi.list(projectId);
      setDocuments(data);
    } catch (err: unknown) {
      console.error('Failed to load documents:', err);
    }
  };

  // Initial load
  useEffect(() => {
    setLoading(true);
    Promise.all([loadProject(), loadSessions(), loadDocuments()]).finally(() => {
      setLoading(false);
    });
  }, [projectId]);

  // Create new session
  const createSession = async () => {
    if (!projectId) return;
    try {
      const newSession = await sessionsApi.create(projectId, { title: 'New Chat' });
      await loadSessions();
      setCurrentSession(newSession);
      setMessages([]);
      setEditingSessionId(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create session';
      setError(message);
    }
  };

  // Select session
  const selectSession = async (session: Session) => {
    setCurrentSession(session);
    await loadMessages(session.id);
    setEditingSessionId(null);
  };

  // Delete session
  const deleteSession = async (sessionId: string) => {
    if (!confirm('Delete this chat session?')) return;
    try {
      await sessionsApi.delete(sessionId);
      await loadSessions();
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete session';
      setError(message);
    }
  };

  // Rename session
  const saveSessionTitle = async (sessionId: string, newTitle: string) => {
    if (!newTitle.trim()) {
      setEditingSessionId(null);
      return;
    }
    try {
      await sessionsApi.update(sessionId, { title: newTitle });
      await loadSessions();
      if (currentSession?.id === sessionId) {
        setCurrentSession({ ...currentSession, title: newTitle });
      }
    } catch (err: unknown) {
      console.error('Failed to rename session:', err);
    }
    setEditingSessionId(null);
  };

  // Send message
  const sendMessage = async () => {
    if (!inputMessage.trim() || !currentSession || sendingMessage) return;

    setSendingMessage(true);
    setError(null);

    // Add user message to UI immediately
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      session_id: currentSession.id,
      role: 'user',
      content: inputMessage,
      metadata: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    const messageToSend = inputMessage;
    setInputMessage('');

    // Track streaming response
    let assistantContent = '';
    const assistantMessageId = `temp-assistant-${Date.now()}`;

    try {
      await chatApi.stream(
        {
          session_id: currentSession.id,
          project_id: projectId!,
          message: messageToSend,
          message_history: messages.map((m) => ({ role: m.role, content: m.content })),
        },
        {
          onStart: () => {
            // Add placeholder for assistant message
            setMessages((prev) => [
              ...prev,
              {
                id: assistantMessageId,
                session_id: currentSession.id,
                role: 'assistant',
                content: '',
                metadata: {},
                created_at: new Date().toISOString(),
              },
            ]);
          },
          onChunk: (chunkData) => {
            assistantContent += chunkData.content;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId ? { ...m, content: assistantContent } : m
              )
            );
          },
          onDone: () => {
            setSendingMessage(false);
            // Reload messages to get saved versions
            loadMessages(currentSession.id);
          },
          onError: (data) => {
            setError(data.content);
            setSendingMessage(false);
            setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId));
          },
        }
      );
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to send message';
      setError(message);
      setSendingMessage(false);
      setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId));
    }
  };

  // Handle file upload
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0 || !projectId) return;

    setUploadingFiles(true);
    setError(null);
    setUploadResults([]);

    try {
      const results = await documentsApi.upload(projectId, Array.from(files));
      setUploadResults(results);
      await loadDocuments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to upload files';
      setError(message);
    } finally {
      setUploadingFiles(false);
    }
  };

  // Delete document
  const deleteDocument = async (documentId: string) => {
    if (!confirm('Delete this document?')) return;
    try {
      await documentsApi.delete(documentId);
      await loadDocuments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete document';
      setError(message);
    }
  };

  // Calculate token count
  const tokenCount = messages.reduce((acc, msg) => acc + estimateTokens(msg.content), 0);
  const tokenPercent = Math.min(100, Math.round((tokenCount / 16000) * 100));

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading workspace...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Project Not Found</CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="primary" onClick={() => navigate('/')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Projects
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-0'
        } border-r bg-card transition-all duration-300 overflow-hidden flex flex-col`}
      >
        {/* Header */}
        <div className="p-4 border-b">
          <h2 className="font-semibold text-lg truncate">{project.name}</h2>
          {project.description && (
            <p className="text-sm text-muted-foreground truncate">{project.description}</p>
          )}
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <Button variant="primary" className="w-full" onClick={createSession}>
            <Plus className="h-4 w-4 mr-2" />
            New Chat
          </Button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-2">
          <div className="text-xs text-muted-foreground px-2 mb-2">CHAT SESSIONS</div>
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer hover:bg-accent mb-1 ${
                currentSession?.id === session.id ? 'bg-accent' : ''
              }`}
            >
              {editingSessionId === session.id ? (
                <div className="flex-1 flex gap-1">
                  <Input
                    value={editingSessionTitle}
                    onChange={(e) => setEditingSessionTitle(e.target.value)}
                    className="h-7 text-sm"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        saveSessionTitle(session.id, editingSessionTitle);
                      } else if (e.key === 'Escape') {
                        setEditingSessionId(null);
                      }
                    }}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => saveSessionTitle(session.id, editingSessionTitle)}
                  >
                    <Check className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => setEditingSessionId(null)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ) : (
                <>
                  <MessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <div
                    className="flex-1 min-w-0 truncate text-sm"
                    onClick={() => selectSession(session)}
                  >
                    {session.title}
                  </div>
                  <div className="hidden group-hover:flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => {
                        setEditingSessionId(session.id);
                        setEditingSessionTitle(session.title);
                      }}
                    >
                      <Edit2 className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => deleteSession(session.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t">
          <Button
            variant="ghost"
            className="w-full justify-start"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Projects
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="border-b bg-card px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <MenuIcon />
            </Button>
            <h1 className="font-semibold">{project.name}</h1>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-sm text-muted-foreground">
              {documents.length} docs
            </div>
            <Button variant="ghost" size="sm" onClick={toggleTheme}>
              {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </Button>
          </div>
        </header>

        {/* Tabs */}
        <div className="border-b bg-card">
          <div className="flex">
            <button
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'chat'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setActiveTab('chat')}
            >
              Chat
            </button>
            <button
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'documents'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setActiveTab('documents')}
            >
              Documents
            </button>
            <button
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'upload'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setActiveTab('upload')}
            >
              Upload
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {/* Error Display */}
          {error && (
            <div className="mx-4 mt-4 p-4 bg-destructive/10 border border-destructive text-destructive rounded-md flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
              <Button
                variant="ghost"
                size="sm"
                className="ml-auto h-6 w-6 p-0"
                onClick={() => setError(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="h-full flex flex-col">
              {!currentSession ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <MessageSquare className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <h3 className="text-lg font-semibold mb-2">No Chat Selected</h3>
                    <p className="text-muted-foreground mb-4">Create a new chat or select one from the sidebar</p>
                    <Button variant="primary" onClick={createSession}>
                      <Plus className="h-4 w-4 mr-2" />
                      New Chat
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[75%] rounded-2xl px-4 py-2 ${
                            msg.role === 'user'
                              ? 'bg-blue-300/50 text-slate-700 rounded-br-sm'
                              : 'bg-muted text-foreground rounded-bl-sm'
                          }`}
                        >
                          {msg.role === 'assistant' ? (
                            <div
                              className="prose prose-sm dark:prose-invert max-w-none"
                              dangerouslySetInnerHTML={{ __html: msg.content }}
                            />
                          ) : (
                            <p className="whitespace-pre-wrap">{msg.content}</p>
                          )}
                        </div>
                      </div>
                    ))}
                    {sendingMessage && (
                      <div className="flex justify-start">
                        <div className="bg-muted text-foreground rounded-2xl rounded-bl-sm px-4 py-2">
                          <p className="text-muted-foreground">Thinking...</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Input */}
                  <div className="border-t bg-card p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm text-muted-foreground">Tokens: {tokenCount.toLocaleString()}</span>
                      {tokenPercent > 80 && (
                        <span className="text-xs text-destructive">
                          ({tokenPercent}% of limit)
                        </span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Input
                        placeholder="Ask about your documents..."
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            sendMessage();
                          }
                        }}
                        disabled={sendingMessage}
                        className="flex-1"
                      />
                      <Button
                        variant="primary"
                        onClick={sendMessage}
                        disabled={sendingMessage || !inputMessage.trim()}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="h-full overflow-y-auto px-4 py-6">
              {documents.length === 0 ? (
                <div className="text-center text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4" />
                  <p>No documents uploaded yet</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {documents.map((doc) => (
                    <Card key={doc.id}>
                      <CardHeader>
                        <CardTitle className="text-base">{doc.title}</CardTitle>
                        <CardDescription>{doc.source}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-between text-sm text-muted-foreground">
                          <span>{doc.chunk_count || 0} chunks</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deleteDocument(doc.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'upload' && (
            <div className="h-full overflow-y-auto px-4 py-6">
              <div className="max-w-2xl mx-auto">
                <Card>
                  <CardHeader>
                    <CardTitle>Upload Documents</CardTitle>
                    <CardDescription>
                      Upload PDF, DOCX, TXT, MD, images, or audio files
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="border-2 border-dashed rounded-lg p-8 text-center">
                      <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mb-4">
                        Drag files here or click to select
                      </p>
                      <input
                        type="file"
                        multiple
                        accept=".pdf,.docx,.doc,.txt,.md,.jpg,.jpeg,.png,.mp3,.wav"
                        onChange={(e) => handleFileUpload(e.target.files)}
                        disabled={uploadingFiles}
                        className="hidden"
                        id="file-upload"
                      />
                      <label htmlFor="file-upload">
                        <span className="inline-block">
                          <Button variant="primary" disabled={uploadingFiles}>
                            {uploadingFiles ? 'Uploading...' : 'Select Files'}
                          </Button>
                        </span>
                      </label>
                    </div>

                    {uploadResults.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="font-semibold text-sm">Upload Results</h4>
                        {uploadResults.map((result, idx) => (
                          <div
                            key={idx}
                            className={`flex items-center justify-between p-2 rounded ${
                              result.success ? 'bg-green-50 dark:bg-green-950' : 'bg-red-50 dark:bg-red-950'
                            }`}
                          >
                            <span className="text-sm truncate">{result.filename}</span>
                            <span className="text-xs text-muted-foreground">
                              {result.success ? `${result.chunks} chunks` : result.error}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// Helper component for menu icon
function MenuIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" x2="20" y1="12" y2="12" />
      <line x1="4" x2="20" y1="6" y2="6" />
      <line x1="4" x2="20" y1="18" y2="18" />
    </svg>
  );
}
