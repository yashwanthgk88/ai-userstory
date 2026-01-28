import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { Play, RotateCcw, Loader2, Cpu, Zap, FileText, AlertTriangle, Shield } from 'lucide-react'

export default function AIConsolePage() {
  const [systemPrompt, setSystemPrompt] = useState('')
  const [userPromptTemplate, setUserPromptTemplate] = useState('')
  const [model, setModel] = useState('')
  const [maxTokens, setMaxTokens] = useState(4096)

  // Test inputs
  const [testTitle, setTestTitle] = useState('')
  const [testDesc, setTestDesc] = useState('')
  const [testCriteria, setTestCriteria] = useState('')

  // Results
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const [activeResultTab, setActiveResultTab] = useState<'parsed' | 'raw'>('parsed')

  const { data: config } = useQuery({
    queryKey: ['ai-config'],
    queryFn: () => api.get('/ai-config').then(r => r.data),
  })

  useEffect(() => {
    if (config) {
      setSystemPrompt(config.system_prompt)
      setUserPromptTemplate(config.user_prompt_template)
      setModel(config.model)
      setMaxTokens(config.max_tokens)
    }
  }, [config])

  const handleReset = () => {
    if (config) {
      setSystemPrompt(config.system_prompt)
      setUserPromptTemplate(config.user_prompt_template)
      setModel(config.model)
      setMaxTokens(config.max_tokens)
    }
  }

  const handleRunTest = async () => {
    if (!testTitle || !testDesc) return
    setRunning(true)
    setError('')
    setResult(null)
    try {
      const resp = await api.post('/ai-console/test', {
        title: testTitle,
        description: testDesc,
        acceptance_criteria: testCriteria || null,
        system_prompt: systemPrompt !== config?.system_prompt ? systemPrompt : null,
        user_prompt_template: userPromptTemplate !== config?.user_prompt_template ? userPromptTemplate : null,
        model: model !== config?.model ? model : null,
        max_tokens: maxTokens !== config?.max_tokens ? maxTokens : null,
      })
      setResult(resp.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'AI analysis failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Cpu className="w-7 h-7 text-purple-400" /> AI Console
          </h1>
          <p className="text-gray-400 mt-1">View, test, and fine-tune AI security analysis prompts</p>
        </div>
        <button onClick={handleReset} className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20">
          <RotateCcw className="w-4 h-4" /> Reset Defaults
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Prompts */}
        <div className="space-y-4">
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-white text-sm uppercase tracking-wide">System Prompt</h3>
              <span className="text-xs text-gray-500">{systemPrompt.length} chars</span>
            </div>
            <textarea
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              rows={10}
              className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-gray-300 text-sm font-mono resize-y"
            />
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-white text-sm uppercase tracking-wide">User Prompt Template</h3>
              <span className="text-xs text-gray-500">{userPromptTemplate.length} chars</span>
            </div>
            <textarea
              value={userPromptTemplate}
              onChange={e => setUserPromptTemplate(e.target.value)}
              rows={14}
              className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-gray-300 text-sm font-mono resize-y"
            />
            <p className="text-xs text-gray-600 mt-2">Variables: {'{title}'}, {'{description}'}, {'{acceptance_criteria_section}'}, {'{custom_standards_section}'}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
              <label className="text-xs text-gray-400 block mb-2">Model</label>
              <select value={model} onChange={e => setModel(e.target.value)} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white text-sm">
                <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
                <option value="claude-haiku-4-20250414">Claude Haiku 4</option>
                <option value="claude-opus-4-20250514">Claude Opus 4</option>
              </select>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
              <label className="text-xs text-gray-400 block mb-2">Max Tokens</label>
              <input type="number" value={maxTokens} onChange={e => setMaxTokens(Number(e.target.value))} className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white text-sm" />
            </div>
          </div>
        </div>

        {/* Right: Test & Results */}
        <div className="space-y-4">
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h3 className="font-semibold text-white text-sm uppercase tracking-wide mb-3">Test Story</h3>
            <div className="space-y-3">
              <input
                value={testTitle}
                onChange={e => setTestTitle(e.target.value)}
                placeholder="Story title"
                className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white placeholder-gray-600 text-sm"
              />
              <textarea
                value={testDesc}
                onChange={e => setTestDesc(e.target.value)}
                placeholder="As a [user], I want to [action] so that [benefit]"
                rows={3}
                className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white placeholder-gray-600 text-sm"
              />
              <input
                value={testCriteria}
                onChange={e => setTestCriteria(e.target.value)}
                placeholder="Acceptance criteria (optional)"
                className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white placeholder-gray-600 text-sm"
              />
              <button
                onClick={handleRunTest}
                disabled={running || !testTitle || !testDesc}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium"
              >
                {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {running ? 'Running Analysis...' : 'Run Test Analysis'}
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-300 text-sm">{error}</div>
          )}

          {result && (
            <>
              {/* Stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-3 text-center">
                  <AlertTriangle className="w-5 h-5 text-orange-400 mx-auto mb-1" />
                  <div className="text-lg font-bold text-orange-400">{result.abuse_case_count}</div>
                  <div className="text-xs text-orange-300">Abuse Cases</div>
                </div>
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-center">
                  <Zap className="w-5 h-5 text-red-400 mx-auto mb-1" />
                  <div className="text-lg font-bold text-red-400">{result.stride_threat_count}</div>
                  <div className="text-xs text-red-300">STRIDE Threats</div>
                </div>
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3 text-center">
                  <Shield className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                  <div className="text-lg font-bold text-purple-400">{result.requirement_count}</div>
                  <div className="text-xs text-purple-300">Requirements</div>
                </div>
              </div>

              {/* Token usage */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center justify-between text-sm">
                <span className="text-gray-400">Model: <span className="text-white">{result.model}</span></span>
                <span className="text-gray-400">Tokens: <span className="text-green-400">{result.input_tokens} in</span> / <span className="text-blue-400">{result.output_tokens} out</span></span>
                <span className="text-gray-400">Risk: <span className={`font-bold ${result.risk_score >= 70 ? 'text-red-400' : result.risk_score >= 40 ? 'text-orange-400' : 'text-green-400'}`}>{result.risk_score}</span></span>
              </div>

              {/* Tabs */}
              <div className="flex gap-2 bg-white/5 p-1 rounded-xl">
                <button onClick={() => setActiveResultTab('parsed')} className={`flex-1 py-2 rounded-lg text-sm font-medium ${activeResultTab === 'parsed' ? 'bg-purple-500/30 border border-purple-500 text-white' : 'text-gray-400'}`}>
                  Parsed Results
                </button>
                <button onClick={() => setActiveResultTab('raw')} className={`flex-1 py-2 rounded-lg text-sm font-medium ${activeResultTab === 'raw' ? 'bg-purple-500/30 border border-purple-500 text-white' : 'text-gray-400'}`}>
                  Raw Response
                </button>
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl p-4 max-h-[500px] overflow-y-auto">
                {activeResultTab === 'parsed' ? (
                  <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                    {JSON.stringify(result.parsed, null, 2)}
                  </pre>
                ) : (
                  <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                    {result.raw_response}
                  </pre>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
