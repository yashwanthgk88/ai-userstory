import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { Plus, FileText, BarChart3, Upload, Clock, Settings, ArrowLeft, Play, Loader2, Link2, Trash2, Zap } from 'lucide-react'

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [showIntegrations, setShowIntegrations] = useState(false)
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const [criteria, setCriteria] = useState('')

  // Import state
  const [importSource, setImportSource] = useState<'jira' | 'ado'>('jira')
  const [importUrl, setImportUrl] = useState('')
  const [importProject, setImportProject] = useState('')
  const [importToken, setImportToken] = useState('')
  const [importEmail, setImportEmail] = useState('')
  const [importLoading, setImportLoading] = useState(false)
  const [importIntegrationId, setImportIntegrationId] = useState('')

  // New integration form state
  const [newIntType, setNewIntType] = useState<'jira' | 'ado' | 'servicenow'>('jira')
  const [newIntName, setNewIntName] = useState('')
  const [newIntUrl, setNewIntUrl] = useState('')
  const [newIntProject, setNewIntProject] = useState('')
  const [newIntEmail, setNewIntEmail] = useState('')
  const [newIntToken, setNewIntToken] = useState('')
  const [newIntUser, setNewIntUser] = useState('')

  // Bulk analyze state
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false)
  const [bulkResult, setBulkResult] = useState<any>(null)

  // Per-story analyze
  const [analyzingStoryId, setAnalyzingStoryId] = useState<string | null>(null)

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.get(`/projects/${projectId}`).then(r => r.data),
  })

  const { data: stories = [], isLoading } = useQuery({
    queryKey: ['stories', projectId],
    queryFn: () => api.get(`/projects/${projectId}/stories`).then(r => r.data),
  })

  const { data: integrations = [] } = useQuery({
    queryKey: ['integrations', projectId],
    queryFn: () => api.get(`/projects/${projectId}/integrations`).then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (body: any) => api.post(`/projects/${projectId}/stories`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stories', projectId] })
      setShowCreate(false)
      setTitle('')
      setDesc('')
      setCriteria('')
    },
  })

  const handleImport = async () => {
    setImportLoading(true)
    try {
      if (importIntegrationId) {
        const endpoint = importSource === 'jira'
          ? `/projects/${projectId}/stories/import/jira`
          : `/projects/${projectId}/stories/import/ado`
        await api.post(endpoint, { integration_id: importIntegrationId })
      } else if (importSource === 'jira') {
        await api.post(`/projects/${projectId}/stories/import/jira`, {
          jira_url: importUrl, project_key: importProject, api_token: importToken, email: importEmail,
        })
      } else {
        await api.post(`/projects/${projectId}/stories/import/ado`, {
          org_url: importUrl, project: importProject, pat: importToken,
        })
      }
      queryClient.invalidateQueries({ queryKey: ['stories', projectId] })
      setShowImport(false)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Import failed')
    } finally {
      setImportLoading(false)
    }
  }

  const handleSaveIntegration = async () => {
    const config: any = { url: newIntUrl }
    if (newIntType === 'jira') {
      config.project_key = newIntProject
      config.email = newIntEmail
    } else if (newIntType === 'ado') {
      config.project = newIntProject
    } else {
      config.username = newIntUser
    }
    try {
      await api.post(`/projects/${projectId}/integrations`, {
        integration_type: newIntType,
        name: newIntName,
        config,
        token: newIntToken,
      })
      queryClient.invalidateQueries({ queryKey: ['integrations', projectId] })
      setNewIntName('')
      setNewIntUrl('')
      setNewIntProject('')
      setNewIntEmail('')
      setNewIntToken('')
      setNewIntUser('')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save integration')
    }
  }

  const handleDeleteIntegration = async (id: string) => {
    if (!confirm('Delete this integration?')) return
    await api.delete(`/integrations/${id}`)
    queryClient.invalidateQueries({ queryKey: ['integrations', projectId] })
  }

  const handleTestIntegration = async (id: string) => {
    try {
      const resp = await api.post(`/integrations/${id}/test`)
      alert(resp.data.message)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Connection test failed')
    }
  }

  const handleBulkAnalyze = async () => {
    setBulkAnalyzing(true)
    setBulkResult(null)
    try {
      const resp = await api.post(`/projects/${projectId}/analyze`)
      setBulkResult(resp.data)
      queryClient.invalidateQueries({ queryKey: ['stories', projectId] })
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Bulk analysis failed')
    } finally {
      setBulkAnalyzing(false)
    }
  }

  const handleAnalyzeStory = async (storyId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setAnalyzingStoryId(storyId)
    try {
      await api.post(`/stories/${storyId}/analyze`)
      queryClient.invalidateQueries({ queryKey: ['stories', projectId] })
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Analysis failed')
    } finally {
      setAnalyzingStoryId(null)
    }
  }

  const filteredIntegrations = integrations.filter((i: any) => i.integration_type === importSource)

  return (
    <div>
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-4">
        <Link to="/" className="hover:text-white"><ArrowLeft className="w-4 h-4 inline" /> Projects</Link>
        <span>/</span>
        <span className="text-white">{project?.name}</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">{project?.name}</h1>
          {project?.description && <p className="text-gray-400 mt-1">{project.description}</p>}
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <button onClick={() => setShowIntegrations(true)} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
            <Link2 className="w-4 h-4" /> Integrations
          </button>
          <Link to={`/projects/${projectId}/standards`} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
            <Settings className="w-4 h-4" /> Standards
          </Link>
          <Link to={`/projects/${projectId}/history`} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
            <Clock className="w-4 h-4" /> History
          </Link>
          <button onClick={() => setShowImport(true)} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
            <Upload className="w-4 h-4" /> Import
          </button>
          <button onClick={handleBulkAnalyze} disabled={bulkAnalyzing || stories.length === 0} className="flex items-center gap-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 px-3 py-2 rounded-lg text-sm text-white font-medium">
            {bulkAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            {bulkAnalyzing ? 'Analyzing...' : 'Analyze All'}
          </button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-white font-medium">
            <Plus className="w-4 h-4" /> Add Story
          </button>
        </div>
      </div>

      {/* Bulk Analysis Result */}
      {bulkResult && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-green-300 font-medium">Bulk Analysis Complete: {bulkResult.results.filter((r: any) => r.status === 'success').length}/{bulkResult.total} stories analyzed</span>
            <button onClick={() => setBulkResult(null)} className="text-gray-400 hover:text-white text-sm">Dismiss</button>
          </div>
          {bulkResult.results.some((r: any) => r.status === 'error') && (
            <div className="mt-2 text-sm text-red-400">
              {bulkResult.results.filter((r: any) => r.status === 'error').map((r: any) => (
                <div key={r.story_id}>Failed: {r.story_title} - {r.error}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Integrations Modal */}
      {showIntegrations && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-white/20 rounded-2xl max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-white mb-4">Integrations</h2>

            {integrations.length > 0 && (
              <div className="space-y-2 mb-6">
                {integrations.map((int: any) => (
                  <div key={int.id} className="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg p-3">
                    <div>
                      <span className="text-white font-medium">{int.name}</span>
                      <span className="ml-2 text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 uppercase">{int.integration_type}</span>
                      <div className="text-xs text-gray-500 mt-1">{int.config?.url}</div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => handleTestIntegration(int.id)} className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded hover:bg-blue-500/30">Test</button>
                      <button onClick={() => handleDeleteIntegration(int.id)} className="text-xs px-2 py-1 bg-red-500/20 text-red-300 rounded hover:bg-red-500/30"><Trash2 className="w-3 h-3" /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase">Add New Integration</h3>
            <div className="flex gap-2 mb-3">
              {(['jira', 'ado', 'servicenow'] as const).map(t => (
                <button key={t} onClick={() => setNewIntType(t)} className={`flex-1 py-2 rounded-lg text-sm font-medium ${newIntType === t ? 'bg-purple-500 text-white' : 'bg-white/10 text-gray-300'}`}>
                  {t === 'jira' ? 'Jira' : t === 'ado' ? 'Azure DevOps' : 'ServiceNow'}
                </button>
              ))}
            </div>
            <div className="space-y-3">
              <input value={newIntName} onChange={e => setNewIntName(e.target.value)} placeholder="Integration name (e.g., My Jira)" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              <input value={newIntUrl} onChange={e => setNewIntUrl(e.target.value)} placeholder={newIntType === 'jira' ? 'https://your-company.atlassian.net' : newIntType === 'ado' ? 'https://dev.azure.com/your-org' : 'https://instance.service-now.com'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              {newIntType !== 'servicenow' && (
                <input value={newIntProject} onChange={e => setNewIntProject(e.target.value)} placeholder={newIntType === 'jira' ? 'Project Key (e.g., KAN)' : 'Project Name'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              )}
              {newIntType === 'jira' && <input value={newIntEmail} onChange={e => setNewIntEmail(e.target.value)} placeholder="Email" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />}
              {newIntType === 'servicenow' && <input value={newIntUser} onChange={e => setNewIntUser(e.target.value)} placeholder="Username" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />}
              <input type="password" value={newIntToken} onChange={e => setNewIntToken(e.target.value)} placeholder={newIntType === 'jira' ? 'API Token' : newIntType === 'ado' ? 'Personal Access Token' : 'Password'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              <div className="flex gap-2">
                <button onClick={handleSaveIntegration} disabled={!newIntName || !newIntUrl || !newIntToken} className="flex-1 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium">Save Integration</button>
                <button onClick={() => setShowIntegrations(false)} className="px-4 py-2 bg-white/10 text-white rounded-lg">Close</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImport && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-white/20 rounded-2xl max-w-lg w-full p-6">
            <h2 className="text-xl font-bold text-white mb-4">Import User Stories</h2>
            <div className="flex gap-2 mb-4">
              <button onClick={() => { setImportSource('jira'); setImportIntegrationId('') }} className={`flex-1 py-2 rounded-lg text-sm font-medium ${importSource === 'jira' ? 'bg-blue-500 text-white' : 'bg-white/10 text-gray-300'}`}>Jira</button>
              <button onClick={() => { setImportSource('ado'); setImportIntegrationId('') }} className={`flex-1 py-2 rounded-lg text-sm font-medium ${importSource === 'ado' ? 'bg-sky-500 text-white' : 'bg-white/10 text-gray-300'}`}>Azure DevOps</button>
            </div>

            {filteredIntegrations.length > 0 && (
              <div className="mb-4">
                <label className="text-xs text-gray-400 mb-1 block">Use saved integration</label>
                <select value={importIntegrationId} onChange={e => setImportIntegrationId(e.target.value)} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white">
                  <option value="">Enter credentials manually</option>
                  {filteredIntegrations.map((i: any) => (
                    <option key={i.id} value={i.id}>{i.name} ({i.config?.url})</option>
                  ))}
                </select>
              </div>
            )}

            {!importIntegrationId && (
              <div className="space-y-3">
                <input value={importUrl} onChange={e => setImportUrl(e.target.value)} placeholder={importSource === 'jira' ? 'https://your-company.atlassian.net' : 'https://dev.azure.com/your-org'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                <input value={importProject} onChange={e => setImportProject(e.target.value)} placeholder={importSource === 'jira' ? 'Project Key (e.g., SEC)' : 'Project Name'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                {importSource === 'jira' && <input value={importEmail} onChange={e => setImportEmail(e.target.value)} placeholder="Email" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />}
                <input type="password" value={importToken} onChange={e => setImportToken(e.target.value)} placeholder={importSource === 'jira' ? 'API Token' : 'Personal Access Token'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <button onClick={handleImport} disabled={importLoading} className="flex-1 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium">
                {importLoading ? 'Importing...' : 'Import Stories'}
              </button>
              <button onClick={() => setShowImport(false)} className="px-4 py-2 bg-white/10 text-white rounded-lg">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Story Form */}
      {showCreate && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
          <h3 className="font-semibold mb-4 text-white">New User Story</h3>
          <div className="space-y-3">
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Story title" className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="As a [user], I want to [action] so that [benefit]" rows={3} className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
            <textarea value={criteria} onChange={e => setCriteria(e.target.value)} placeholder="Acceptance criteria (optional)" rows={2} className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
            <div className="flex gap-2">
              <button onClick={() => createMutation.mutate({ title, description: desc, acceptance_criteria: criteria || null })} disabled={!title || !desc} className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium">Create</button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-white/10 text-white rounded-lg">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Loading stories...</div>
      ) : stories.length === 0 ? (
        <div className="text-center py-16 bg-white/5 border border-white/10 rounded-2xl">
          <FileText className="w-16 h-16 text-purple-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No user stories yet</h3>
          <p className="text-gray-400">Add stories manually or import from Jira / Azure DevOps</p>
        </div>
      ) : (
        <div className="space-y-3">
          {stories.map((s: any) => (
            <div key={s.id} className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors">
              <Link to={`/projects/${projectId}/stories/${s.id}`} className="flex-1 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {s.external_id && <span className="text-xs font-mono text-purple-400 bg-purple-500/20 px-2 py-0.5 rounded">{s.external_id}</span>}
                    <span className="text-xs text-gray-500 capitalize bg-white/5 px-2 py-0.5 rounded">{s.source}</span>
                  </div>
                  <span className="flex items-center gap-1 text-xs text-gray-500"><BarChart3 className="w-3 h-3" /> {s.analysis_count} analyses</span>
                </div>
                <h3 className="font-semibold text-white mb-1">{s.title}</h3>
                <p className="text-sm text-gray-400 line-clamp-2">{s.description}</p>
              </Link>
              <button
                onClick={(e) => handleAnalyzeStory(s.id, e)}
                disabled={analyzingStoryId === s.id}
                className="mr-4 flex items-center gap-1.5 px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 rounded-lg text-sm border border-purple-500/30 disabled:opacity-50"
              >
                {analyzingStoryId === s.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                {analyzingStoryId === s.id ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
