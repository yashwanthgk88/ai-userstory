import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { Key, Webhook, Trash2, Copy, Plus, CheckCircle, TestTube } from 'lucide-react'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'api-keys' | 'webhooks'>('api-keys')
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState('')
  const [copied, setCopied] = useState(false)

  // Webhook form
  const [whProjectId, setWhProjectId] = useState('')
  const [whUrl, setWhUrl] = useState('')
  const [whSecret, setWhSecret] = useState('')
  const [whEvents, setWhEvents] = useState<string[]>(['analysis.completed', 'bulk_analysis.completed'])

  const { data: apiKeys = [] } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.get('/auth/api-keys').then(r => r.data),
  })

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects').then(r => r.data),
  })

  const { data: webhooks = [] } = useQuery({
    queryKey: ['webhooks', whProjectId],
    queryFn: () => whProjectId ? api.get(`/projects/${whProjectId}/webhooks`).then(r => r.data) : Promise.resolve([]),
    enabled: !!whProjectId,
  })

  const handleCreateKey = async () => {
    if (!newKeyName) return
    try {
      const resp = await api.post('/auth/api-keys', { name: newKeyName })
      setCreatedKey(resp.data.key)
      setNewKeyName('')
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create API key')
    }
  }

  const handleCopyKey = () => {
    navigator.clipboard.writeText(createdKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDeleteKey = async (id: string) => {
    if (!confirm('Revoke this API key? Any pipelines using it will stop working.')) return
    await api.delete(`/auth/api-keys/${id}`)
    queryClient.invalidateQueries({ queryKey: ['api-keys'] })
  }

  const handleCreateWebhook = async () => {
    if (!whProjectId || !whUrl || !whSecret) return
    try {
      await api.post(`/projects/${whProjectId}/webhooks`, { url: whUrl, secret: whSecret, event_types: whEvents })
      queryClient.invalidateQueries({ queryKey: ['webhooks', whProjectId] })
      setWhUrl('')
      setWhSecret('')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create webhook')
    }
  }

  const handleDeleteWebhook = async (id: string) => {
    if (!confirm('Delete this webhook?')) return
    await api.delete(`/webhooks/${id}`)
    queryClient.invalidateQueries({ queryKey: ['webhooks', whProjectId] })
  }

  const handleTestWebhook = async (id: string) => {
    try {
      const resp = await api.post(`/webhooks/${id}/test`)
      alert(`Test sent. Response code: ${resp.data.response_code}`)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Test failed')
    }
  }

  const toggleEvent = (evt: string) => {
    setWhEvents(prev => prev.includes(evt) ? prev.filter(e => e !== evt) : [...prev, evt])
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-2">Settings</h1>
      <p className="text-gray-400 mb-6">Manage API keys and webhooks for DevSecOps integration</p>

      <div className="flex gap-2 mb-6 bg-white/5 p-1 rounded-xl">
        <button onClick={() => setActiveTab('api-keys')} className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium ${activeTab === 'api-keys' ? 'bg-purple-500/30 border border-purple-500 text-white' : 'text-gray-400'}`}>
          <Key className="w-4 h-4" /> API Keys
        </button>
        <button onClick={() => setActiveTab('webhooks')} className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium ${activeTab === 'webhooks' ? 'bg-purple-500/30 border border-purple-500 text-white' : 'text-gray-400'}`}>
          <Webhook className="w-4 h-4" /> Webhooks
        </button>
      </div>

      {activeTab === 'api-keys' && (
        <div className="space-y-4">
          {/* Create key */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h3 className="font-semibold text-white mb-3">Create API Key</h3>
            <p className="text-sm text-gray-400 mb-3">API keys allow CI/CD pipelines to authenticate with SecureReq AI. Use the <code className="bg-white/10 px-1 rounded">X-API-Key</code> header.</p>
            <div className="flex gap-2">
              <input value={newKeyName} onChange={e => setNewKeyName(e.target.value)} placeholder="Key name (e.g., GitHub Actions)" className="flex-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white placeholder-gray-600 text-sm" />
              <button onClick={handleCreateKey} disabled={!newKeyName} className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium text-sm">
                <Plus className="w-4 h-4" /> Create
              </button>
            </div>
          </div>

          {/* Show created key (once) */}
          {createdKey && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <span className="font-semibold text-green-300">API Key Created</span>
              </div>
              <p className="text-xs text-green-400/70 mb-2">Copy this key now. It won't be shown again.</p>
              <div className="flex gap-2">
                <code className="flex-1 bg-black/30 border border-green-500/30 px-3 py-2 rounded-lg text-green-300 text-sm font-mono break-all">{createdKey}</code>
                <button onClick={handleCopyKey} className="px-3 py-2 bg-green-600/20 hover:bg-green-600/30 text-green-300 rounded-lg text-sm border border-green-500/30">
                  {copied ? 'Copied!' : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          )}

          {/* Existing keys */}
          <div className="space-y-2">
            {apiKeys.map((k: any) => (
              <div key={k.id} className="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg p-3">
                <div>
                  <span className="text-white font-medium">{k.name}</span>
                  <div className="text-xs text-gray-500 mt-1">
                    Created: {new Date(k.created_at).toLocaleDateString()}
                    {k.last_used_at && <> | Last used: {new Date(k.last_used_at).toLocaleDateString()}</>}
                  </div>
                </div>
                <button onClick={() => handleDeleteKey(k.id)} className="px-2 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded text-xs">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
            {apiKeys.length === 0 && <p className="text-gray-500 text-sm text-center py-4">No API keys yet</p>}
          </div>

          {/* Usage example */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h3 className="font-semibold text-white mb-2 text-sm">Usage Example</h3>
            <pre className="text-xs text-gray-400 font-mono bg-black/30 p-3 rounded-lg overflow-x-auto">{`# Trigger bulk analysis from CI/CD
curl -X POST \\
  https://ai-userstory-production.up.railway.app/api/projects/{PROJECT_ID}/analyze \\
  -H "X-API-Key: srq_your_api_key_here" \\
  -H "Content-Type: application/json"`}</pre>
          </div>
        </div>
      )}

      {activeTab === 'webhooks' && (
        <div className="space-y-4">
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h3 className="font-semibold text-white mb-3">Create Webhook</h3>
            <p className="text-sm text-gray-400 mb-3">Receive notifications when analyses complete. Payloads are signed with HMAC-SHA256 in the <code className="bg-white/10 px-1 rounded">X-Signature-256</code> header.</p>
            <div className="space-y-3">
              <select value={whProjectId} onChange={e => setWhProjectId(e.target.value)} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white text-sm">
                <option value="">Select project</option>
                {projects.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input value={whUrl} onChange={e => setWhUrl(e.target.value)} placeholder="Webhook URL (https://...)" className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white placeholder-gray-600 text-sm" />
              <input value={whSecret} onChange={e => setWhSecret(e.target.value)} placeholder="Secret (for HMAC signature verification)" className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white placeholder-gray-600 text-sm" />
              <div>
                <label className="text-xs text-gray-400 block mb-2">Events</label>
                <div className="flex gap-2 flex-wrap">
                  {['analysis.completed', 'analysis.failed', 'bulk_analysis.completed'].map(evt => (
                    <button key={evt} onClick={() => toggleEvent(evt)} className={`px-3 py-1 rounded-lg text-xs font-medium border ${whEvents.includes(evt) ? 'bg-purple-500/30 border-purple-500 text-purple-300' : 'bg-white/5 border-white/10 text-gray-500'}`}>
                      {evt}
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={handleCreateWebhook} disabled={!whProjectId || !whUrl || !whSecret} className="w-full py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium text-sm">
                Create Webhook
              </button>
            </div>
          </div>

          {whProjectId && (
            <div className="space-y-2">
              {webhooks.map((wh: any) => (
                <div key={wh.id} className="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg p-3">
                  <div>
                    <div className="text-white text-sm font-mono">{wh.url}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Events: {wh.event_types?.join(', ')}
                      {wh.last_triggered_at && <> | Last fired: {new Date(wh.last_triggered_at).toLocaleString()}</>}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleTestWebhook(wh.id)} className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs hover:bg-blue-500/30">Test</button>
                    <button onClick={() => handleDeleteWebhook(wh.id)} className="px-2 py-1 bg-red-500/20 text-red-300 rounded text-xs hover:bg-red-500/30"><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>
              ))}
              {webhooks.length === 0 && <p className="text-gray-500 text-sm text-center py-4">No webhooks for this project</p>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
