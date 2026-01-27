import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { Plus, FileText, BarChart3, Upload, Clock, Settings, ArrowLeft } from 'lucide-react'

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [showImport, setShowImport] = useState(false)
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

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.get(`/projects/${projectId}`).then(r => r.data),
  })

  const { data: stories = [], isLoading } = useQuery({
    queryKey: ['stories', projectId],
    queryFn: () => api.get(`/projects/${projectId}/stories`).then(r => r.data),
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
      if (importSource === 'jira') {
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
        <div className="flex gap-2">
          <Link to={`/projects/${projectId}/standards`} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
            <Settings className="w-4 h-4" /> Standards
          </Link>
          <Link to={`/projects/${projectId}/history`} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
            <Clock className="w-4 h-4" /> History
          </Link>
          <button onClick={() => setShowImport(true)} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
            <Upload className="w-4 h-4" /> Import
          </button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-white font-medium">
            <Plus className="w-4 h-4" /> Add Story
          </button>
        </div>
      </div>

      {/* Import Modal */}
      {showImport && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-white/20 rounded-2xl max-w-lg w-full p-6">
            <h2 className="text-xl font-bold text-white mb-4">Import User Stories</h2>
            <div className="flex gap-2 mb-4">
              <button onClick={() => setImportSource('jira')} className={`flex-1 py-2 rounded-lg text-sm font-medium ${importSource === 'jira' ? 'bg-blue-500 text-white' : 'bg-white/10 text-gray-300'}`}>Jira</button>
              <button onClick={() => setImportSource('ado')} className={`flex-1 py-2 rounded-lg text-sm font-medium ${importSource === 'ado' ? 'bg-sky-500 text-white' : 'bg-white/10 text-gray-300'}`}>Azure DevOps</button>
            </div>
            <div className="space-y-3">
              <input value={importUrl} onChange={e => setImportUrl(e.target.value)} placeholder={importSource === 'jira' ? 'https://your-company.atlassian.net' : 'https://dev.azure.com/your-org'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              <input value={importProject} onChange={e => setImportProject(e.target.value)} placeholder={importSource === 'jira' ? 'Project Key (e.g., SEC)' : 'Project Name'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              {importSource === 'jira' && <input value={importEmail} onChange={e => setImportEmail(e.target.value)} placeholder="Email" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />}
              <input type="password" value={importToken} onChange={e => setImportToken(e.target.value)} placeholder={importSource === 'jira' ? 'API Token' : 'Personal Access Token'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
              <div className="flex gap-2">
                <button onClick={handleImport} disabled={importLoading} className="flex-1 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium">
                  {importLoading ? 'Importing...' : 'Import Stories'}
                </button>
                <button onClick={() => setShowImport(false)} className="px-4 py-2 bg-white/10 text-white rounded-lg">Cancel</button>
              </div>
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
            <Link key={s.id} to={`/projects/${projectId}/stories/${s.id}`} className="block bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-colors">
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
          ))}
        </div>
      )}
    </div>
  )
}
