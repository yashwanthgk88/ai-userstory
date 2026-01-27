import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { ArrowLeft, BarChart3, Clock } from 'lucide-react'
import { riskColor } from '../lib/utils'

export default function HistoryPage() {
  const { projectId } = useParams<{ projectId: string }>()

  const { data: stories = [] } = useQuery({
    queryKey: ['stories', projectId],
    queryFn: () => api.get(`/projects/${projectId}/stories`).then(r => r.data),
  })

  // For each story that has analyses, fetch analysis summaries
  const storiesWithAnalyses = stories.filter((s: any) => s.analysis_count > 0)

  return (
    <div>
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-4">
        <Link to={`/projects/${projectId}`} className="hover:text-white"><ArrowLeft className="w-3 h-3 inline" /> Back</Link>
        <span>/</span><span className="text-white">Analysis History</span>
      </div>

      <h1 className="text-2xl font-bold text-white mb-2">Analysis Archive</h1>
      <p className="text-gray-400 mb-6">Browse all past security analyses for this project. Click any story to view or re-run analysis.</p>

      {storiesWithAnalyses.length === 0 ? (
        <div className="text-center py-16 bg-white/5 border border-white/10 rounded-2xl">
          <Clock className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No analysis history</h3>
          <p className="text-gray-400">Run your first analysis on a user story to start building history</p>
        </div>
      ) : (
        <div className="space-y-4">
          {storiesWithAnalyses.map((story: any) => (
            <StoryHistoryCard key={story.id} story={story} projectId={projectId!} />
          ))}
        </div>
      )}
    </div>
  )
}

function StoryHistoryCard({ story, projectId }: { story: any; projectId: string }) {
  const { data: analyses = [] } = useQuery({
    queryKey: ['analyses', story.id],
    queryFn: () => api.get(`/stories/${story.id}/analyses`).then(r => r.data),
  })

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
      <Link to={`/projects/${projectId}/stories/${story.id}`} className="block mb-3 hover:text-purple-300">
        <h3 className="font-semibold text-white">{story.title}</h3>
        <p className="text-gray-400 text-sm mt-1 line-clamp-1">{story.description}</p>
      </Link>
      <div className="space-y-2">
        {analyses.map((a: any) => {
          const risk = riskColor(a.risk_score)
          return (
            <div key={a.id} className="flex items-center justify-between bg-white/5 rounded-lg px-4 py-2.5">
              <div className="flex items-center gap-4">
                <span className="text-xs font-mono text-gray-500">v{a.version}</span>
                <span className="text-xs text-gray-500">{a.ai_model_used}</span>
                <span className="text-xs text-gray-500">{new Date(a.created_at).toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs text-gray-400"><BarChart3 className="w-3 h-3 inline" /> {a.abuse_case_count} threats, {a.requirement_count} requirements</span>
                <span className={`text-xs font-bold ${risk.text}`}>{a.risk_score}/100</span>
                <Link to={`/projects/${projectId}/compliance/${a.id}`} className="text-xs text-purple-400 hover:text-purple-300">Compliance</Link>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
