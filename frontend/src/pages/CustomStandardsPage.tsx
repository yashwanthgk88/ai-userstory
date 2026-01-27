import { useState, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { ArrowLeft, Upload, Trash2, FileText } from 'lucide-react'

export default function CustomStandardsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [uploading, setUploading] = useState(false)

  const { data: standards = [], isLoading } = useQuery({
    queryKey: ['standards', projectId],
    queryFn: () => api.get(`/projects/${projectId}/standards`).then(r => r.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/standards/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['standards', projectId] }),
  })

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file || !name) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('name', name)
      form.append('description', desc)
      form.append('file', file)
      await api.post(`/projects/${projectId}/standards`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      queryClient.invalidateQueries({ queryKey: ['standards', projectId] })
      setName('')
      setDesc('')
      if (fileRef.current) fileRef.current.value = ''
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-4">
        <Link to={`/projects/${projectId}`} className="hover:text-white"><ArrowLeft className="w-3 h-3 inline" /> Back</Link>
        <span>/</span><span className="text-white">Custom Security Standards</span>
      </div>

      <h1 className="text-2xl font-bold text-white mb-2">Custom Security Standards</h1>
      <p className="text-gray-400 mb-6">Upload your organization's security standards (JSON, CSV, or PDF). These will be used alongside built-in frameworks when generating security requirements.</p>

      {/* Upload Form */}
      <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
        <h3 className="font-semibold text-white mb-4 flex items-center gap-2"><Upload className="w-5 h-5" /> Upload Standard</h3>
        <div className="space-y-3">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Standard name (e.g., 'Internal AppSec Policy v3')" className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
          <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Description (optional)" className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500" />
          <input ref={fileRef} type="file" accept=".json,.csv,.pdf" className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white file:mr-4 file:rounded-lg file:border-0 file:bg-purple-600 file:text-white file:px-4 file:py-1 file:cursor-pointer" />
          <div className="text-xs text-gray-500">Supported formats: JSON (array of controls), CSV (with columns: control_id, title, description, category), PDF</div>
          <button onClick={handleUpload} disabled={!name || uploading} className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl font-medium">
            {uploading ? 'Uploading...' : 'Upload Standard'}
          </button>
        </div>
      </div>

      {/* Standards List */}
      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading...</div>
      ) : standards.length === 0 ? (
        <div className="text-center py-12 bg-white/5 border border-white/10 rounded-2xl">
          <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">No custom standards uploaded yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {standards.map((s: any) => (
            <div key={s.id} className="bg-white/5 border border-white/10 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white">{s.name}</h3>
                  {s.description && <p className="text-gray-400 text-sm mt-1">{s.description}</p>}
                  <div className="flex gap-3 mt-2 text-xs text-gray-500">
                    <span>Type: {s.file_type?.toUpperCase()}</span>
                    <span>File: {s.original_filename}</span>
                    <span>Controls: {s.controls?.length || 0}</span>
                    <span>{new Date(s.uploaded_at).toLocaleDateString()}</span>
                  </div>
                  {s.controls?.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {s.controls.slice(0, 5).map((c: any, i: number) => (
                        <div key={i} className="text-xs text-gray-400">
                          <span className="text-purple-400 font-mono">{c.control_id}</span> - {c.title}
                        </div>
                      ))}
                      {s.controls.length > 5 && <div className="text-xs text-gray-500">...and {s.controls.length - 5} more</div>}
                    </div>
                  )}
                </div>
                <button onClick={() => deleteMutation.mutate(s.id)} className="text-red-400 hover:text-red-300 p-2">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
