import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

function App() {
  const [skills, setSkills] = useState([])
  const [file, setFile] = useState(null)
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [pdfUploading, setPdfUploading] = useState(false)
  const [pdfProgress, setPdfProgress] = useState(0)
  const [websiteUploading, setWebsiteUploading] = useState(false)
  const [websiteProgress, setWebsiteProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState('')
  const [selectedSkill, setSelectedSkill] = useState(null)
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [querying, setQuerying] = useState(false)
  const [notification, setNotification] = useState(null)
  const [activeTab, setActiveTab] = useState('upload')
  const [exportDropdown, setExportDropdown] = useState(null)
  const exportRef = useRef(null)

  const EXPORT_AGENTS = [
    { key: 'opencode',     label: 'OpenCode',         file: 'AGENTS.md' },
    { key: 'codex',        label: 'Codex',            file: 'AGENTS.md' },
    { key: 'cursor',       label: 'Cursor',           file: '.cursorrules' },
    { key: 'copilot',      label: 'GitHub Copilot',   file: 'copilot-instructions.md' },
    { key: 'windsurf',     label: 'Windsurf',         file: '.windsurfrules' },
    { key: 'cline',        label: 'Cline',            file: '.clinerules' },
    { key: 'aider',        label: 'Aider',            file: 'CONVENTIONS.md' },
    { key: 'systemprompt', label: 'System Prompt',    file: 'system-prompt.txt' },
  ]

  useEffect(() => {
    fetchSkills()
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if (exportRef.current && !exportRef.current.contains(e.target)) {
        setExportDropdown(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [exportDropdown])

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type })
    setTimeout(() => setNotification(null), 4000)
  }

  const fetchSkills = async () => {
    try {
      const res = await axios.get(`${API_URL}/skills`)
      setSkills(res.data)
    } catch (err) {
      console.error('Failed to fetch skills:', err)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile?.type === 'application/pdf') {
      setFile(droppedFile)
    }
  }

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile?.type === 'application/pdf') {
      setFile(selectedFile)
    }
  }

  const uploadPdf = async () => {
    if (!file) return
    setPdfUploading(true)
    setPdfProgress(0)

    const formData = new FormData()
    formData.append('file', file)

    try {
      await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          setPdfProgress(Math.round((e.loaded * 100) / e.total))
        },
      })
      setFile(null)
      fetchSkills()
      showNotification('Skill created successfully')
    } catch (err) {
      showNotification('Upload failed: ' + (err.response?.data?.detail || 'Unknown error'), 'error')
    } finally {
      setPdfUploading(false)
      setPdfProgress(0)
    }
  }

  const uploadWebsite = async () => {
    if (!websiteUrl) return
    setWebsiteUploading(true)
    setWebsiteProgress(0)
    setStatusMessage('Initializing crawler...')

    let pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/crawl-progress`)
        const progress = res.data
        if (progress.in_progress) {
          setStatusMessage(`Crawling: ${progress.visited} pages`)
          setWebsiteProgress(Math.min(95, progress.visited * 5))
        }
      } catch (err) {
        console.error('Progress poll failed:', err)
      }
    }, 2000)

    try {
      await axios.post(`${API_URL}/upload-website`, { url: websiteUrl })
      setWebsiteProgress(100)
      setWebsiteUrl('')
      fetchSkills()
      showNotification('Website skill created successfully')
    } catch (err) {
      showNotification('Failed: ' + (err.response?.data?.detail || 'Unknown error'), 'error')
    } finally {
      clearInterval(pollInterval)
      setWebsiteUploading(false)
      setTimeout(() => {
        setStatusMessage('')
        setWebsiteProgress(0)
      }, 2000)
    }
  }

  const askQuery = async () => {
    if (!selectedSkill || !query) return
    setQuerying(true)
    setAnswer('')

    try {
      const res = await axios.post(`${API_URL}/skills/${selectedSkill.id}/query`, { query })
      setAnswer(res.data.answer)
    } catch (err) {
      showNotification('Query failed', 'error')
    } finally {
      setQuerying(false)
    }
  }

  const downloadSkill = async (skillId, format) => {
    try {
      const link = document.createElement('a')
      link.href = `${API_URL}/skills/${skillId}/download?format=${format}`
      link.download = `skill_${skillId}.${format === 'json' ? 'json' : format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      showNotification('Download failed', 'error')
    }
  }

  const deleteSkill = async (skillId, skillName) => {
    if (!confirm(`Delete "${skillName}"?`)) return
    try {
      await axios.delete(`${API_URL}/skills/${skillId}`)
      if (selectedSkill?.id === skillId) setSelectedSkill(null)
      fetchSkills()
      showNotification('Skill deleted')
    } catch (err) {
      showNotification('Delete failed', 'error')
    }
  }

  const exportSkill = (skillId, agentKey) => {
    const link = document.createElement('a')
    link.href = `${API_URL}/skills/${skillId}/export?agent=${agentKey}`
    link.download = ''
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setExportDropdown(null)
    showNotification(`Exported for ${EXPORT_AGENTS.find(a => a.key === agentKey)?.label}`)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="text-lg font-semibold text-white">AI Skill Generator</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400">{skills.length} skills</span>
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            <span className="text-sm text-emerald-400">Connected</span>
          </div>
        </div>
      </nav>

      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`fixed top-20 left-1/2 -translate-x-1/2 px-4 py-3 rounded-lg border z-50 ${
              notification.type === 'error'
                ? 'bg-red-950/90 border-red-800 text-red-300'
                : 'bg-emerald-950/90 border-emerald-800 text-emerald-300'
            }`}
          >
            {notification.message}
          </motion.div>
        )}
      </AnimatePresence>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-3">
            <nav className="space-y-1">
              <button
                onClick={() => setActiveTab('upload')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === 'upload'
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Create Skill</span>
              </button>
              <button
                onClick={() => setActiveTab('skills')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === 'skills'
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span>My Skills</span>
                <span className="ml-auto px-2 py-0.5 bg-slate-700 rounded text-xs">{skills.length}</span>
              </button>
              <button
                onClick={() => setActiveTab('api')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === 'api'
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                <span>API Reference</span>
              </button>
            </nav>
          </div>

          <div className="col-span-9">
            <AnimatePresence mode="wait">
              {activeTab === 'upload' && (
                <motion.div
                  key="upload"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-2 gap-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                      <h2 className="text-lg font-medium text-white mb-4">Upload PDF Document</h2>
                      <div
                        onDrop={handleDrop}
                        onDragOver={(e) => e.preventDefault()}
                        className="border-2 border-dashed border-slate-700 rounded-lg p-8 text-center hover:border-slate-600 transition-colors"
                      >
                        <input
                          type="file"
                          accept=".pdf"
                          onChange={handleFileSelect}
                          className="hidden"
                          id="fileInput"
                        />
                        <label htmlFor="fileInput" className="cursor-pointer">
                          <svg className="w-12 h-12 mx-auto text-slate-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          {file ? (
                            <div>
                              <p className="text-emerald-400 font-medium">{file.name}</p>
                              <p className="text-slate-500 text-sm mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                            </div>
                          ) : (
                            <div>
                              <p className="text-slate-400">Drop PDF here or click to browse</p>
                              <p className="text-slate-600 text-sm mt-1">Max file size: 50MB</p>
                            </div>
                          )}
                        </label>
                      </div>
                      {file && (
                        <>
                        {pdfUploading && (
                          <div className="mt-3 space-y-1">
                            <div className="flex justify-between text-xs text-slate-500">
                              <span>Uploading...</span>
                              <span>{pdfProgress}%</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1">
                              <div className="bg-indigo-500 h-1 rounded-full transition-all duration-300" style={{ width: `${pdfProgress}%` }} />
                            </div>
                          </div>
                        )}
                        <button
                          onClick={uploadPdf}
                          disabled={pdfUploading}
                          className="mt-4 w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                        >
                          {pdfUploading ? (
                            <>
                              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                              </svg>
                              Processing...
                            </>
                          ) : 'Create Skill'}
                        </button>
                        </>
                      )}
                    </div>

                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                      <h2 className="text-lg font-medium text-white mb-4">Extract from Website</h2>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm text-slate-400 mb-2">Website URL</label>
                          <input
                            type="url"
                            value={websiteUrl}
                            onChange={(e) => setWebsiteUrl(e.target.value)}
                            placeholder="https://docs.example.com"
                            className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg focus:border-indigo-500 focus:outline-none text-white placeholder-slate-500"
                          />
                        </div>
                        <button
                          onClick={uploadWebsite}
                          disabled={websiteUploading || !websiteUrl}
                          className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                        >
                          {websiteUploading ? (
                            <>
                              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                              </svg>
                              Extracting...
                            </>
                          ) : 'Extract & Create'}
                        </button>
                        {websiteUploading && (
                          <div className="space-y-2">
                            <div className="flex justify-between text-xs text-slate-500">
                              <span>{statusMessage}</span>
                              <span>{websiteProgress}%</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1">
                              <div className="bg-indigo-500 h-1 rounded-full transition-all duration-300" style={{ width: `${websiteProgress}%` }} />
                            </div>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-4">Extracts content from all pages under the given URL.</p>
                    </div>
                  </div>
                </motion.div>
              )}

              {activeTab === 'skills' && (
                <motion.div
                  key="skills"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <div className="bg-slate-900 border border-slate-800 rounded-xl">
                    <div className="px-6 py-4 border-b border-slate-800">
                      <h2 className="text-lg font-medium text-white">All Skills</h2>
                    </div>
                    <div className="divide-y divide-slate-800">
                      {skills.length === 0 ? (
                        <div className="px-6 py-16 text-center">
                          <svg className="w-16 h-16 mx-auto text-slate-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                          </svg>
                          <p className="text-slate-500">No skills yet. Create your first skill from the Upload tab.</p>
                        </div>
                      ) : (
                        skills.map((skill) => (
                          <div
                            key={skill.id}
                            className={`px-6 py-4 hover:bg-slate-800/50 transition-colors cursor-pointer ${
                              selectedSkill?.id === skill.id ? 'bg-slate-800/50 border-l-2 border-indigo-500' : ''
                            }`}
                            onClick={() => setSelectedSkill(skill)}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-3">
                                  <h3 className="font-medium text-white">{skill.name}</h3>
                                  <span className="px-2 py-0.5 bg-slate-800 text-slate-400 text-xs rounded uppercase">{skill.skill_type}</span>
                                </div>
                                <p className="text-sm text-slate-500 mt-1">
                                  {new Date(skill.created_at).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                </p>
                              </div>
                              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                <button
                                  onClick={() => downloadSkill(skill.id, 'skill')}
                                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition-colors"
                                >
                                  .skill
                                </button>
                                <button
                                  onClick={() => downloadSkill(skill.id, 'md')}
                                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition-colors"
                                >
                                  .md
                                </button>
                                {/* Export for AI agents dropdown */}
                                <div className="relative" ref={exportDropdown === skill.id ? exportRef : null}>
                                  <button
                                    onClick={() => setExportDropdown(exportDropdown === skill.id ? null : skill.id)}
                                    className="px-3 py-1.5 bg-indigo-900/50 hover:bg-indigo-800/60 text-indigo-300 text-xs rounded transition-colors flex items-center gap-1"
                                  >
                                    Export
                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                  </button>
                                  {exportDropdown === skill.id && (
                                    <div className="absolute right-0 top-8 z-50 w-52 bg-slate-900 border border-slate-700 rounded-lg shadow-xl py-1">
                                      <p className="px-3 py-1.5 text-xs text-slate-500 uppercase tracking-wider font-medium border-b border-slate-700 mb-1">Export for AI Agent</p>
                                      {EXPORT_AGENTS.map((agent) => (
                                        <button
                                          key={agent.key}
                                          onClick={() => exportSkill(skill.id, agent.key)}
                                          className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 transition-colors flex items-center justify-between"
                                        >
                                          <span>{agent.label}</span>
                                          <span className="text-xs text-slate-500 font-mono">{agent.file}</span>
                                        </button>
                                      ))}
                                    </div>
                                  )}
                                </div>
                                <button
                                  onClick={() => deleteSkill(skill.id, skill.name)}
                                  className="px-3 py-1.5 bg-red-950/50 hover:bg-red-900/50 text-red-400 text-xs rounded transition-colors"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {selectedSkill && (
                    <div className="bg-slate-900 border border-slate-800 rounded-xl mt-6">
                      <div className="px-6 py-4 border-b border-slate-800">
                        <div className="flex items-center justify-between">
                          <div>
                            <h2 className="text-lg font-medium text-white">Query: {selectedSkill.name}</h2>
                            <p className="text-sm text-slate-500">Ask questions about this skill using RAG</p>
                          </div>
                          <button onClick={() => setSelectedSkill(null)} className="text-slate-500 hover:text-white">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      <div className="p-6 space-y-4">
                        <textarea
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder="Ask a question about this skill..."
                          className="w-full p-4 bg-slate-800 border border-slate-700 rounded-lg resize-none h-24 focus:border-indigo-500 focus:outline-none text-white placeholder-slate-500"
                        />
                        <button
                          onClick={askQuery}
                          disabled={querying || !query}
                          className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 text-white rounded-lg font-medium transition-colors"
                        >
                          {querying ? 'Generating answer...' : 'Ask Question'}
                        </button>
                        {answer && (
                          <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
                            <h4 className="text-sm text-slate-400 mb-2">Answer</h4>
                            <p className="text-white whitespace-pre-wrap">{answer}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}

              {activeTab === 'api' && (
                <motion.div
                  key="api"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <div className="bg-slate-900 border border-slate-800 rounded-xl">
                    <div className="px-6 py-4 border-b border-slate-800">
                      <h2 className="text-lg font-medium text-white">API Reference</h2>
                      <p className="text-sm text-slate-500 mt-1">Query skills programmatically from other agents or applications</p>
                    </div>
                    <div className="p-6 space-y-6">
                      <div>
                        <div className="flex items-center gap-2 mb-3">
                          <span className="px-2 py-1 bg-emerald-600 text-white text-xs font-medium rounded">POST</span>
                          <code className="text-indigo-400">/skills/{'{skill_id}'}/query</code>
                        </div>
                        <div className="bg-slate-950 rounded-lg p-4">
                          <p className="text-xs text-slate-500 mb-2">Request Body</p>
                          <pre className="text-sm text-slate-300">{`{
  "query": "What is the main topic?"
}`}</pre>
                        </div>
                      </div>
                      <div>
                        <h3 className="text-white font-medium mb-3">Other Endpoints</h3>
                        <div className="space-y-2">
                          {[
                            { method: 'GET', path: '/skills', desc: 'List all skills' },
                            { method: 'POST', path: '/upload', desc: 'Upload PDF' },
                            { method: 'POST', path: '/upload-website', desc: 'Extract from URL' },
                            { method: 'DELETE', path: '/skills/{id}', desc: 'Delete skill' },
                                            { method: 'GET', path: '/skills/{id}/download', desc: 'Download skill file (.skill / .md / .json)' },
                                            { method: 'GET', path: '/skills/{id}/export?agent=opencode', desc: 'Export for AI agent (opencode, codex, cursor, copilot, windsurf, cline, aider, systemprompt)' },
                          ].map((endpoint) => (
                            <div key={endpoint.path} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
                              <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                endpoint.method === 'GET' ? 'bg-blue-600 text-white' :
                                endpoint.method === 'POST' ? 'bg-emerald-600 text-white' :
                                'bg-red-600 text-white'
                              }`}>{endpoint.method}</span>
                              <code className="text-slate-300">{endpoint.path}</code>
                              <span className="text-slate-500 text-sm">{endpoint.desc}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App