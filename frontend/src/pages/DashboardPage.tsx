import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { Layers, Plus, Shield, FileText, BarChart3, Trash2, Link2, Loader2, ExternalLink } from 'lucide-react'

interface JiraProject {
  id: string
  key: string
  name: string
  avatar_url: string | null
}

interface Integration {
  id: string
  integration_type: string
  name: string
  config: Record<string, any>
}

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [showCreate, setShowCreate] = useState(false)
  const [showIntegrationSetup, setShowIntegrationSetup] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [importingProject, setImportingProject] = useState<string | null>(null)

  // Integration form state
  const [jiraUrl, setJiraUrl] = useState('')
  const [jiraEmail, setJiraEmail] = useState('')
  const [jiraToken, setJiraToken] = useState('')

  const { data: spaces = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects').then(r => r.data),
  })

  // Fetch global integrations
  const { data: globalIntegrations = [] } = useQuery({
    queryKey: ['integrations', 'global'],
    queryFn: () => api.get('/integrations/global').then(r => r.data),
  })

  // Get the first Jira integration
  const jiraIntegration: Integration | undefined = globalIntegrations.find((i: Integration) => i.integration_type === 'jira')

  // Fetch Jira projects if we have a Jira integration
  const { data: jiraProjects = [], isLoading: loadingJiraProjects, error: jiraProjectsError } = useQuery<JiraProject[]>({
    queryKey: ['jira-projects', jiraIntegration?.id],
    queryFn: () => api.get(`/integrations/${jiraIntegration!.id}/jira/projects`).then(r => r.data),
    enabled: !!jiraIntegration,
    retry: 1,
  })

  // Check which Jira projects already have a local space
  const linkedProjectKeys = new Set(spaces.filter((s: any) => s.jira_project_key).map((s: any) => s.jira_project_key))

  const createMutation = useMutation({
    mutationFn: (body: { name: string; description: string }) => api.post('/projects', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowCreate(false)
      setName('')
      setDesc('')
    },
  })

  const createIntegrationMutation = useMutation({
    mutationFn: (body: { integration_type: string; name: string; config: any; token: string }) =>
      api.post('/integrations/global', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations', 'global'] })
      setShowIntegrationSetup(false)
      setJiraUrl('')
      setJiraEmail('')
      setJiraToken('')
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || 'Failed to create integration')
    },
  })

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Delete this space and all its stories and analyses?')) return
    try {
      await api.delete(`/projects/${id}`)
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Delete failed')
    }
  }

  const handleImportJiraProject = async (project: JiraProject) => {
    if (!jiraIntegration) return
    setImportingProject(project.key)
    try {
      // Create space with Jira project info
      const response = await api.post('/projects/from-jira', {
        integration_id: jiraIntegration.id,
        jira_project_key: project.key,
        jira_project_name: project.name,
      })
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      // Navigate to the new space
      navigate(`/projects/${response.data.id}`)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to import project')
    } finally {
      setImportingProject(null)
    }
  }

  const handleCreateIntegration = () => {
    createIntegrationMutation.mutate({
      integration_type: 'jira',
      name: 'Jira',
      config: { url: jiraUrl.replace(/\/$/, ''), email: jiraEmail },
      token: jiraToken,
    })
  }

  // Filter unlinked Jira projects
  const unlinkedJiraProjects = jiraProjects.filter(p => !linkedProjectKeys.has(p.key))

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Spaces</h1>
          <p className="text-gray-400 mt-1">Manage your application security analyses</p>
        </div>
        <div className="flex gap-2">
          {!jiraIntegration && (
            <button
              onClick={() => setShowIntegrationSetup(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 py-2.5 rounded-xl text-white font-medium transition-colors"
            >
              <Link2 className="w-5 h-5" /> Connect Jira
            </button>
          )}
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2.5 rounded-xl text-white font-medium transition-colors">
            <Plus className="w-5 h-5" /> New Space
          </button>
        </div>
      </div>

      {/* Jira Integration Setup */}
      {showIntegrationSetup && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-2xl p-6 mb-6">
          <h3 className="font-semibold mb-4 text-white flex items-center gap-2">
            <Link2 className="w-5 h-5 text-blue-400" /> Connect Jira
          </h3>
          <p className="text-gray-400 text-sm mb-4">
            Connect your Jira instance to automatically import projects and stories.
          </p>
          <div className="space-y-3">
            <input
              value={jiraUrl}
              onChange={e => setJiraUrl(e.target.value)}
              placeholder="Jira URL (e.g., https://yourcompany.atlassian.net)"
              className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500"
            />
            <input
              value={jiraEmail}
              onChange={e => setJiraEmail(e.target.value)}
              placeholder="Email address"
              className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500"
            />
            <input
              value={jiraToken}
              onChange={e => setJiraToken(e.target.value)}
              type="password"
              placeholder="API Token (from id.atlassian.com/manage-profile/security/api-tokens)"
              className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500"
            />
            <div className="flex gap-2">
              <button
                onClick={handleCreateIntegration}
                disabled={!jiraUrl || !jiraEmail || !jiraToken || createIntegrationMutation.isPending}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium flex items-center gap-2"
              >
                {createIntegrationMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Connect
              </button>
              <button onClick={() => setShowIntegrationSetup(false)} className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Jira Projects Section */}
      {jiraIntegration && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <ExternalLink className="w-5 h-5 text-blue-400" />
            Jira Projects
            <span className="text-sm font-normal text-gray-400">— Click to import</span>
          </h2>
          {loadingJiraProjects ? (
            <div className="text-center py-8 text-gray-400">Loading Jira projects...</div>
          ) : jiraProjectsError ? (
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 text-red-400">
              <p className="font-medium">Failed to load Jira projects</p>
              <p className="text-sm mt-1">{(jiraProjectsError as any)?.response?.data?.detail || (jiraProjectsError as Error)?.message || 'Unknown error'}</p>
              <button
                onClick={() => queryClient.invalidateQueries({ queryKey: ['jira-projects'] })}
                className="mt-2 text-sm underline hover:no-underline"
              >
                Try again
              </button>
            </div>
          ) : unlinkedJiraProjects.length === 0 ? (
            <div className="text-center py-8 text-gray-400">All Jira projects have been imported</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {unlinkedJiraProjects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => handleImportJiraProject(project)}
                  disabled={importingProject === project.key}
                  className="text-left bg-blue-500/10 border border-blue-500/30 rounded-2xl p-5 hover:bg-blue-500/20 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center gap-3 mb-2">
                    {project.avatar_url ? (
                      <img src={project.avatar_url} alt="" className="w-8 h-8 rounded" />
                    ) : (
                      <div className="w-8 h-8 bg-blue-500/30 rounded flex items-center justify-center text-blue-400 font-bold text-sm">
                        {project.key[0]}
                      </div>
                    )}
                    <div>
                      <h3 className="font-semibold text-white">{project.name}</h3>
                      <span className="text-xs text-blue-400">{project.key}</span>
                    </div>
                    {importingProject === project.key && (
                      <Loader2 className="w-5 h-5 text-blue-400 animate-spin ml-auto" />
                    )}
                  </div>
                  <p className="text-gray-400 text-sm">Click to import as a space</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {showCreate && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
          <h3 className="font-semibold mb-4 text-white">Create Space</h3>
          <div className="space-y-3">
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Space name (e.g., Jira project key)" className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="Description (optional)" rows={2} className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
            <div className="flex gap-2">
              <button onClick={() => createMutation.mutate({ name, description: desc })} disabled={!name} className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium">Create</button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Layers className="w-5 h-5 text-purple-400" />
        Your Spaces
      </h2>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Loading spaces...</div>
      ) : spaces.length === 0 ? (
        <div className="text-center py-16 bg-white/5 border border-white/10 rounded-2xl">
          <Shield className="w-16 h-16 text-purple-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No spaces yet</h3>
          <p className="text-gray-400">
            {jiraIntegration
              ? 'Import a Jira project above or create a new space manually'
              : 'Connect Jira to import projects or create a new space manually'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {spaces.map((p: any) => (
            <div key={p.id} className="relative bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 transition-colors group">
              <Link to={`/projects/${p.id}`} className="block p-5">
                <div className="flex items-center gap-3 mb-3">
                  <Layers className="w-6 h-6 text-purple-400" />
                  <h3 className="font-semibold text-white group-hover:text-purple-300 transition-colors">{p.name}</h3>
                  {p.jira_project_key && (
                    <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">{p.jira_project_key}</span>
                  )}
                </div>
                {p.description && <p className="text-gray-400 text-sm mb-4 line-clamp-2">{p.description}</p>}
                <div className="flex gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> {p.story_count} stories</span>
                  <span className="flex items-center gap-1"><BarChart3 className="w-3.5 h-3.5" /> {p.analysis_count} analyses</span>
                </div>
              </Link>
              <button
                onClick={(e) => handleDelete(p.id, e)}
                className="absolute top-3 right-3 p-1.5 bg-red-500/10 hover:bg-red-500/30 text-red-400 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete space"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
