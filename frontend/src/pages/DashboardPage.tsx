import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { FolderOpen, Plus, Shield, FileText, BarChart3, Trash2 } from 'lucide-react'

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects').then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (body: { name: string; description: string }) => api.post('/projects', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowCreate(false)
      setName('')
      setDesc('')
    },
  })

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Delete this project and all its stories and analyses?')) return
    try {
      await api.delete(`/projects/${id}`)
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Delete failed')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="text-gray-400 mt-1">Manage your application security analyses</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2.5 rounded-xl text-white font-medium transition-colors">
          <Plus className="w-5 h-5" /> New Project
        </button>
      </div>

      {showCreate && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
          <h3 className="font-semibold mb-4 text-white">Create Project</h3>
          <div className="space-y-3">
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Project name" className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="Description (optional)" rows={2} className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
            <div className="flex gap-2">
              <button onClick={() => createMutation.mutate({ name, description: desc })} disabled={!name} className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium">Create</button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 bg-white/5 border border-white/10 rounded-2xl">
          <Shield className="w-16 h-16 text-purple-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No projects yet</h3>
          <p className="text-gray-400">Create your first project to start generating security requirements</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p: any) => (
            <div key={p.id} className="relative bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 transition-colors group">
              <Link to={`/projects/${p.id}`} className="block p-5">
                <div className="flex items-center gap-3 mb-3">
                  <FolderOpen className="w-6 h-6 text-purple-400" />
                  <h3 className="font-semibold text-white group-hover:text-purple-300 transition-colors">{p.name}</h3>
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
                title="Delete project"
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
