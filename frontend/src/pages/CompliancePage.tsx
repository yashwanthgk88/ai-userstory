import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'

const STANDARD_COLORS: Record<string, string> = {
  OWASP_ASVS: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
  NIST_800_53: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
  ISO_27001: 'bg-green-500/20 text-green-300 border-green-500/40',
  PCI_DSS: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
  HIPAA: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
  SOX: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
  GDPR: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
}

export default function CompliancePage() {
  const { projectId, analysisId } = useParams<{ projectId: string; analysisId: string }>()
  const [selectedStandard, setSelectedStandard] = useState<string | null>(null)

  const { data: mappings = [] } = useQuery({
    queryKey: ['compliance', analysisId],
    queryFn: () => api.get(`/analyses/${analysisId}/compliance`).then(r => r.data),
  })

  const { data: summary = [] } = useQuery({
    queryKey: ['compliance-summary', analysisId],
    queryFn: () => api.get(`/analyses/${analysisId}/compliance/summary`).then(r => r.data),
  })

  const filtered = selectedStandard ? mappings.filter((m: any) => m.standard_name === selectedStandard) : mappings

  return (
    <div>
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-4">
        <Link to={`/projects/${projectId}`} className="hover:text-white"><ArrowLeft className="w-3 h-3 inline" /> Back</Link>
        <span>/</span><span className="text-white">Compliance Mapping</span>
      </div>

      <h1 className="text-2xl font-bold text-white mb-6">Compliance & Standards Mapping</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
        {summary.map((s: any) => (
          <button key={s.standard_name} onClick={() => setSelectedStandard(selectedStandard === s.standard_name ? null : s.standard_name)}
            className={`p-3 rounded-xl border text-center transition-all ${selectedStandard === s.standard_name ? 'ring-2 ring-purple-500' : ''} ${STANDARD_COLORS[s.standard_name] || 'bg-white/10 text-gray-300 border-white/20'}`}>
            <div className="text-lg font-bold">{s.mapped_controls}</div>
            <div className="text-xs mt-1">{s.standard_name.replace(/_/g, ' ')}</div>
          </button>
        ))}
      </div>

      {/* Mappings Table */}
      <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/5">
              <th className="text-left px-4 py-3 text-gray-400 font-medium">Requirement</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">Standard</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">Control</th>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">Title</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m: any, i: number) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                <td className="px-4 py-2 text-purple-400 font-mono text-xs">{m.requirement_id}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs border ${STANDARD_COLORS[m.standard_name] || 'bg-white/10 text-gray-300 border-white/20'}`}>
                    {m.standard_name.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-300 font-mono text-xs">{m.control_id}</td>
                <td className="px-4 py-2 text-gray-400 text-xs">{m.control_title}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="text-center py-8 text-gray-500">No compliance mappings found</div>}
      </div>
    </div>
  )
}
