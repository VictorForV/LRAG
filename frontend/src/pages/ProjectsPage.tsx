/**
 * Projects Page - List, create, edit, and delete projects
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, RefreshCw, Moon, Sun, FolderOpen, Trash2, Edit2, FileText, MessageSquare, Settings } from 'lucide-react';
import { projectsApi } from '../api';
import type { Project } from '../types';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/Card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/Dialog';
import { useAppStore } from '../store/appStore';
import { formatDate } from '../lib/utils';
import { SettingsDialog } from '../components/SettingsDialog';

export default function ProjectsPage() {
  const navigate = useNavigate();
  const { theme, toggleTheme, settingsDialogOpen, setSettingsDialogOpen } = useAppStore();

  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Load projects
  const loadProjects = async () => {
    console.log('[ProjectsPage] Loading projects...');
    setLoading(true);
    setError(null);
    try {
      const data = await projectsApi.list(search || undefined);
      console.log('[ProjectsPage] Projects loaded:', data);
      setProjects(data);
    } catch (err: unknown) {
      console.error('[ProjectsPage] Error loading projects:', err);
      const message = err instanceof Error ? err.message : 'Failed to load projects';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, [search]);

  // Create project
  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      await projectsApi.create({ name: newProjectName, description: newProjectDescription || undefined });
      setNewProjectName('');
      setNewProjectDescription('');
      setCreateDialogOpen(false);
      loadProjects();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create project';
      setError(message);
    }
  };

  // Edit project
  const handleEditProject = async () => {
    if (!editingProject || !newProjectName.trim()) return;

    try {
      await projectsApi.update(editingProject.id, {
        name: newProjectName,
        description: newProjectDescription || undefined,
      });
      setEditDialogOpen(false);
      setEditingProject(null);
      setNewProjectName('');
      setNewProjectDescription('');
      loadProjects();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update project';
      setError(message);
    }
  };

  // Delete project
  const handleDeleteProject = async (project: Project) => {
    if (!confirm(`Delete project "${project.name}"? This will also delete all associated sessions and documents.`)) {
      return;
    }

    try {
      await projectsApi.delete(project.id);
      loadProjects();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete project';
      setError(message);
    }
  };

  // Open edit dialog
  const openEditDialog = (project: Project) => {
    setEditingProject(project);
    setNewProjectName(project.name);
    setNewProjectDescription(project.description || '');
    setEditDialogOpen(true);
  };

  // Open project
  const openProject = (project: Project) => {
    navigate(`/workspace/${project.id}`);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">RAG Knowledge Base</h1>
              <p className="text-sm text-muted-foreground">Manage your document projects</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => loadProjects()}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSettingsDialogOpen(true)}
              >
                <Settings className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleTheme}
              >
                {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions Bar */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search projects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="primary">
                <Plus className="h-4 w-4 mr-2" />
                New Project
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Project</DialogTitle>
                <DialogDescription>Create a new project to organize your documents</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div>
                  <label htmlFor="name" className="text-sm font-medium">Name *</label>
                  <Input
                    id="name"
                    placeholder="My Research Project"
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label htmlFor="description" className="text-sm font-medium">Description</label>
                  <Input
                    id="description"
                    placeholder="Optional description..."
                    value={newProjectDescription}
                    onChange={(e) => setNewProjectDescription(e.target.value)}
                    className="mt-1"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="ghost" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
                <Button variant="primary" onClick={handleCreateProject} disabled={!newProjectName.trim()}>
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-4 bg-destructive/10 border border-destructive text-destructive rounded-md">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12 text-muted-foreground">
            Loading projects...
          </div>
        )}

        {/* Empty State */}
        {!loading && projects.length === 0 && (
          <div className="text-center py-12">
            <FolderOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No projects found</h3>
            <p className="text-muted-foreground mb-4">Create your first project to get started</p>
            <Button variant="primary" onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
          </div>
        )}

        {/* Projects Grid */}
        {!loading && projects.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Card key={project.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-start justify-between">
                    <span className="truncate flex-1">{project.name}</span>
                  </CardTitle>
                  {project.description && (
                    <CardDescription className="line-clamp-2">
                      {project.description}
                    </CardDescription>
                  )}
                  <p className="text-xs text-muted-foreground mt-2">
                    Created {formatDate(project.created_at)}
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    <div className="flex items-center text-sm text-muted-foreground">
                      <FileText className="h-4 w-4 mr-1" />
                      {project.doc_count}
                    </div>
                    <div className="flex items-center text-sm text-muted-foreground">
                      <MessageSquare className="h-4 w-4 mr-1" />
                      {project.session_count}
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="justify-between">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => openProject(project)}
                  >
                    <FolderOpen className="h-4 w-4 mr-2" />
                    Open
                  </Button>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditDialog(project)}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteProject(project)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        {/* Project Count */}
        {!loading && projects.length > 0 && (
          <p className="text-center text-sm text-muted-foreground mt-6">
            {projects.length} project{projects.length !== 1 ? 's' : ''}
          </p>
        )}
      </main>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Project</DialogTitle>
            <DialogDescription>Update project details</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label htmlFor="edit-name" className="text-sm font-medium">Name *</label>
              <Input
                id="edit-name"
                placeholder="Project name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label htmlFor="edit-description" className="text-sm font-medium">Description</label>
              <Input
                id="edit-description"
                placeholder="Optional description..."
                value={newProjectDescription}
                onChange={(e) => setNewProjectDescription(e.target.value)}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditDialogOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleEditProject} disabled={!newProjectName.trim()}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <SettingsDialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen} />
    </div>
  );
}
