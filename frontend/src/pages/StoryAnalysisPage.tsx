import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { riskColor, priorityColor } from '../lib/utils'
import { ArrowLeft, Play, Download, Send, FileSpreadsheet, FileText, FileDown, Loader2 } from 'lucide-react'

export default function StoryAnalysisPage() {
  const { projectId, storyId } = useParams<{ projectId: string; storyId: string }>()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'threats' | 'requirements' | 'stride'>('threats')
  const [showExport, setShowExport] = useState(false)
  const [exportLoading, setExportLoading] = useState('')

  // Export integration state
  const [showPush, setShowPush] = useState<'jira' | 'ado' | 'servicenow' | null>(null)
  const [pushUrl, setPushUrl] = useState('')
  const [pushProject, setPushProject] = useState('')
  const [pushToken, setPushToken] = useState('')
  const [pushEmail, setPushEmail] = useState('')
  const [pushTable, setPushTable] = useState('rm_story')
  const [pushUser, setPushUser] = useState('')
  const [pushPass, setPushPass] = useState('')
  const [pushIntegrationId, setPushIntegrationId] = useState('')

  const { data: story } = useQuery({
    queryKey: ['story', storyId],
    queryFn: () => api.get(`/stories/${storyId}`).then(r => r.data),
  })

  const { data: analyses = [] } = useQuery({
    queryKey: ['analyses', storyId],
    queryFn: () => api.get(`/stories/${storyId}/analyses`).then(r => r.data),
  })

  const { data: integrations = [] } = useQuery({
    queryKey: ['integrations', projectId],
    queryFn: () => api.get(`/projects/${projectId}/integrations`).then(r => r.data),
    enabled: !!projectId,
  })

  const latestAnalysisId = analyses.length > 0 ? analyses[0].id : null

  const { data: analysis } = useQuery({
    queryKey: ['analysis', latestAnalysisId],
    queryFn: () => api.get(`/analyses/${latestAnalysisId}`).then(r => r.data),
    enabled: !!latestAnalysisId,
  })

  const analyzeMutation = useMutation({
    mutationFn: () => api.post(`/stories/${storyId}/analyze`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analyses', storyId] })
      queryClient.invalidateQueries({ queryKey: ['analysis'] })
    },
  })

  const handleExport = async (format: string) => {
    if (!latestAnalysisId) return
    setExportLoading(format)
    try {
      const resp = await api.post(`/analyses/${latestAnalysisId}/export/${format}`, {}, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      const ext = format === 'excel' ? 'xlsx' : format
      a.download = `security_analysis.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      alert('Export failed')
    } finally {
      setExportLoading('')
    }
  }

  const handlePush = async () => {
    if (!latestAnalysisId || !showPush) return
    setExportLoading(showPush)
    try {
      let body: any = {}
      if (pushIntegrationId) {
        body = { integration_id: pushIntegrationId }
      } else if (showPush === 'jira') {
        body = { jira_url: pushUrl, project_key: pushProject, api_token: pushToken, email: pushEmail }
      } else if (showPush === 'ado') {
        body = { org_url: pushUrl, project: pushProject, pat: pushToken }
      } else {
        body = { instance_url: pushUrl, username: pushUser, password: pushPass, table: pushTable }
      }
      const resp = await api.post(`/analyses/${latestAnalysisId}/export/${showPush}`, body)
      alert(resp.data.message)
      setShowPush(null)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Push failed')
    } finally {
      setExportLoading('')
    }
  }

  const filteredIntegrations = showPush ? integrations.filter((i: any) => i.integration_type === showPush) : []

  const risk = analysis ? riskColor(analysis.risk_score) : null

  return (
    <div>
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-4">
        <Link to="/" className="hover:text-white">Projects</Link><span>/</span>
        <Link to={`/projects/${projectId}`} className="hover:text-white"><ArrowLeft className="w-3 h-3 inline" /> Back</Link><span>/</span>
        <span className="text-white">{story?.title}</span>
      </div>

      {/* Story Info */}
      <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white mb-2">{story?.title}</h1>
            <p className="text-gray-400 text-sm">{story?.description}</p>
            {story?.acceptance_criteria && <p className="text-gray-500 text-xs mt-2">Acceptance: {story.acceptance_criteria}</p>}
          </div>
          <div className="flex gap-2 ml-4">
            <button onClick={() => analyzeMutation.mutate()} disabled={analyzeMutation.isPending} className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 px-4 py-2.5 rounded-xl text-white font-medium">
              {analyzeMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {analyzeMutation.isPending ? 'Analyzing...' : analyses.length > 0 ? 'Re-Analyze' : 'Run Analysis'}
            </button>
          </div>
        </div>
        {analyses.length > 0 && (
          <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
            <span>Version {analyses[0].version}</span>
            <span>Model: {analyses[0].ai_model_used}</span>
            <span>{new Date(analyses[0].created_at).toLocaleString()}</span>
          </div>
        )}
      </div>

      {!analysis ? (
        <div className="text-center py-16 bg-white/5 border border-white/10 rounded-2xl">
          <div className="text-6xl mb-4">🛡️</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Analysis Yet</h3>
          <p className="text-gray-400">Click "Run Analysis" to generate security requirements using AI</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Stats Row */}
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-orange-400">{analysis.abuse_cases?.length || 0}</div>
              <div className="text-xs text-orange-300">Abuse Cases</div>
            </div>
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-red-400">{analysis.stride_threats?.length || 0}</div>
              <div className="text-xs text-red-300">STRIDE Threats</div>
            </div>
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-purple-400">{analysis.security_requirements?.length || 0}</div>
              <div className="text-xs text-purple-300">Requirements</div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
              <div className={`text-2xl font-bold ${risk?.text}`}>{analysis.risk_score}</div>
              <div className={`text-xs ${risk?.text}`}>{risk?.label}</div>
            </div>
          </div>

          {/* Risk Bar */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <div className="flex justify-between mb-2">
              <span className="text-gray-400 text-sm">Risk Score</span>
              <span className={`font-bold ${risk?.text}`}>{risk?.label}</span>
            </div>
            <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
              <div className={`h-full ${risk?.bar} transition-all duration-1000`} style={{ width: `${analysis.risk_score}%` }} />
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 bg-white/5 p-1 rounded-xl">
            {(['threats', 'requirements', 'stride'] as const).map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${activeTab === tab ? 'bg-purple-500/30 border border-purple-500 text-white' : 'text-gray-400 hover:text-white'}`}>
                {tab === 'threats' ? '⚠️ Abuse Cases' : tab === 'requirements' ? '🛡️ Requirements' : '📊 STRIDE'}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4 max-h-[500px] overflow-y-auto">
            {activeTab === 'threats' && (
              <div className="space-y-3">
                {analysis.abuse_cases?.map((ac: any, i: number) => (
                  <div key={i} className={`bg-white/5 rounded-lg p-3 border-l-4 ${ac.impact === 'Critical' ? 'border-red-500' : ac.impact === 'High' ? 'border-orange-500' : 'border-yellow-500'}`}>
                    <div className="flex items-start justify-between mb-2">
                      <span className="font-medium text-white">{ac.threat}</span>
                      <span className={`px-2 py-0.5 text-xs font-bold rounded text-white ${priorityColor(ac.impact)}`}>{ac.impact}</span>
                    </div>
                    <p className="text-sm text-gray-400 mb-2">{ac.description}</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div><span className="text-gray-500">Actor:</span> <span className="text-gray-300">{ac.actor}</span></div>
                      <div><span className="text-gray-500">Likelihood:</span> <span className="text-gray-300">{ac.likelihood}</span></div>
                      <div className="col-span-2"><span className="text-gray-500">Attack Vector:</span> <span className="text-gray-300">{ac.attack_vector}</span></div>
                      <div><span className="text-gray-500">STRIDE:</span> <span className="text-purple-400">{ac.stride_category}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {activeTab === 'requirements' && (
              <div className="space-y-3">
                {analysis.security_requirements?.map((req: any, i: number) => (
                  <div key={i} className="bg-white/5 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 text-xs font-bold rounded text-white ${priorityColor(req.priority)}`}>{req.priority}</span>
                      <span className="text-xs font-mono text-purple-400">{req.id}</span>
                      <span className="text-xs text-gray-500">{req.category}</span>
                    </div>
                    <p className="text-sm text-gray-300">{req.text}</p>
                    <p className="text-xs text-gray-500 mt-1">{req.details}</p>
                  </div>
                ))}
              </div>
            )}
            {activeTab === 'stride' && (
              <div className="space-y-3">
                {analysis.stride_threats?.map((st: any, i: number) => (
                  <div key={i} className="bg-white/5 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 text-xs font-bold rounded text-white ${priorityColor(st.risk_level)}`}>{st.risk_level}</span>
                      <span className="font-medium text-purple-300">{st.category}</span>
                    </div>
                    <p className="text-sm font-medium text-white">{st.threat}</p>
                    <p className="text-xs text-gray-400 mt-1">{st.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Export & Push */}
          <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-xl p-4">
            <h3 className="font-semibold mb-3 text-white flex items-center gap-2"><Download className="w-5 h-5" /> Export & Push</h3>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              <button onClick={() => handleExport('excel')} disabled={!!exportLoading} className="flex items-center justify-center gap-1 py-2 bg-green-600/20 hover:bg-green-600/30 text-green-300 rounded-lg text-sm border border-green-500/30">
                <FileSpreadsheet className="w-4 h-4" /> Excel
              </button>
              <button onClick={() => handleExport('pdf')} disabled={!!exportLoading} className="flex items-center justify-center gap-1 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-300 rounded-lg text-sm border border-red-500/30">
                <FileText className="w-4 h-4" /> PDF
              </button>
              <button onClick={() => handleExport('csv')} disabled={!!exportLoading} className="flex items-center justify-center gap-1 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 rounded-lg text-sm border border-blue-500/30">
                <FileDown className="w-4 h-4" /> CSV
              </button>
              <button onClick={() => { setShowPush('jira'); setPushIntegrationId('') }} className="flex items-center justify-center gap-1 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded-lg text-sm border border-blue-500/30">
                <Send className="w-4 h-4" /> Jira
              </button>
              <button onClick={() => { setShowPush('ado'); setPushIntegrationId('') }} className="flex items-center justify-center gap-1 py-2 bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 rounded-lg text-sm border border-sky-500/30">
                <Send className="w-4 h-4" /> ADO
              </button>
              <button onClick={() => { setShowPush('servicenow'); setPushIntegrationId('') }} className="flex items-center justify-center gap-1 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 rounded-lg text-sm border border-emerald-500/30">
                <Send className="w-4 h-4" /> ServiceNow
              </button>
            </div>
            <Link to={`/projects/${projectId}/compliance/${latestAnalysisId}`} className="block mt-3 text-center py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg text-sm border border-purple-500/30">
              📋 View Compliance Mapping
            </Link>
          </div>

          {/* Push Modal */}
          {showPush && (
            <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-slate-800 border border-white/20 rounded-2xl max-w-lg w-full p-6">
                <h2 className="text-xl font-bold text-white mb-4">Push to {showPush === 'jira' ? 'Jira' : showPush === 'ado' ? 'Azure DevOps' : 'ServiceNow'}</h2>

                {/* Saved integrations dropdown */}
                {filteredIntegrations.length > 0 && (
                  <div className="mb-4">
                    <label className="text-xs text-gray-400 mb-1 block">Use saved integration</label>
                    <select value={pushIntegrationId} onChange={e => setPushIntegrationId(e.target.value)} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white">
                      <option value="">Enter credentials manually</option>
                      {filteredIntegrations.map((i: any) => (
                        <option key={i.id} value={i.id}>{i.name} ({i.config?.url})</option>
                      ))}
                    </select>
                  </div>
                )}

                {!pushIntegrationId && (
                  <div className="space-y-3">
                    {showPush === 'servicenow' ? (
                      <>
                        <input value={pushUrl} onChange={e => setPushUrl(e.target.value)} placeholder="Instance URL (https://instance.service-now.com)" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                        <input value={pushUser} onChange={e => setPushUser(e.target.value)} placeholder="Username" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                        <input type="password" value={pushPass} onChange={e => setPushPass(e.target.value)} placeholder="Password" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                        <input value={pushTable} onChange={e => setPushTable(e.target.value)} placeholder="Table (e.g., rm_story)" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                      </>
                    ) : (
                      <>
                        <input value={pushUrl} onChange={e => setPushUrl(e.target.value)} placeholder={showPush === 'jira' ? 'https://your-company.atlassian.net' : 'https://dev.azure.com/your-org'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                        <input value={pushProject} onChange={e => setPushProject(e.target.value)} placeholder={showPush === 'jira' ? 'Project Key' : 'Project Name'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                        {showPush === 'jira' && <input value={pushEmail} onChange={e => setPushEmail(e.target.value)} placeholder="Email" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />}
                        <input type="password" value={pushToken} onChange={e => setPushToken(e.target.value)} placeholder={showPush === 'jira' ? 'API Token' : 'Personal Access Token'} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500" />
                      </>
                    )}
                  </div>
                )}

                <div className="flex gap-2 mt-4">
                  <button onClick={handlePush} disabled={!!exportLoading} className="flex-1 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium">
                    {exportLoading ? 'Pushing...' : `Push ${(analysis.abuse_cases?.length || 0) + (analysis.security_requirements?.length || 0)} items`}
                  </button>
                  <button onClick={() => setShowPush(null)} className="px-4 py-2 bg-white/10 text-white rounded-lg">Cancel</button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
