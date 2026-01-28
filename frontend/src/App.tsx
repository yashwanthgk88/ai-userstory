import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './stores/authStore'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import StoryAnalysisPage from './pages/StoryAnalysisPage'
import CompliancePage from './pages/CompliancePage'
import CustomStandardsPage from './pages/CustomStandardsPage'
import HistoryPage from './pages/HistoryPage'
import AIConsolePage from './pages/AIConsolePage'
import SettingsPage from './pages/SettingsPage'
import APIDocsPage from './pages/APIDocsPage'
import AppShell from './components/layout/AppShell'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuthStore()
  if (loading) return <div className="flex items-center justify-center h-screen text-white">Loading...</div>
  if (!token) return <Navigate to="/login" />
  return <>{children}</>
}

export default function App() {
  const { token, loadUser } = useAuthStore()

  useEffect(() => {
    if (token) loadUser()
  }, [token, loadUser])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="projects/:projectId/stories/:storyId" element={<StoryAnalysisPage />} />
        <Route path="projects/:projectId/compliance/:analysisId" element={<CompliancePage />} />
        <Route path="projects/:projectId/standards" element={<CustomStandardsPage />} />
        <Route path="projects/:projectId/history" element={<HistoryPage />} />
        <Route path="ai-console" element={<AIConsolePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="api-docs" element={<APIDocsPage />} />
      </Route>
    </Routes>
  )
}
