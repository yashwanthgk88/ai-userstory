import { FileText } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/api\/?$/, '')
  : ''

export default function APIDocsPage() {
  const docsUrl = `${API_BASE}/api/docs`

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FileText className="w-7 h-7 text-purple-400" /> API Documentation
          </h1>
          <p className="text-gray-400 mt-1">Interactive Swagger UI for all SecureReq AI endpoints</p>
        </div>
        <a
          href={docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-sm text-white border border-white/20"
        >
          Open in New Tab
        </a>
      </div>
      <div className="bg-white rounded-xl overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
        <iframe
          src={docsUrl}
          title="API Documentation"
          className="w-full h-full border-0"
        />
      </div>
    </div>
  )
}
