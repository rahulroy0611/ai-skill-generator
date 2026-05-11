import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

function App() {
  const [skills, setSkills] = useState([])
  const [file, setFile] = useState(null)
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [websiteSuccess, setWebsiteSuccess] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [selectedSkill, setSelectedSkill] = useState(null)
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [querying, setQuerying] = useState(false)

  useEffect(() => {
    fetchSkills()
  }, [])

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
      setUploadSuccess(false)
    }
  }

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile?.type === 'application/pdf') {
      setFile(selectedFile)
      setUploadSuccess(false)
    }
  }

  const uploadPdf = async () => {
    if (!file) return
    setUploading(true)
    setUploadProgress(0)
    setUploadSuccess(false)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          setUploadProgress(Math.round((e.loaded * 100) / e.total))
        },
      })
      setUploadSuccess(true)
      setFile(null)
      fetchSkills()
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
    }
  }

  const uploadWebsite = async () => {
    if (!websiteUrl) return
    setUploading(true)
    setUploadProgress(0)
    setWebsiteSuccess(false)
    setStatusMessage('Starting crawl...')

    let pollInterval = null

    const startPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_URL}/crawl-progress`)
          const progress = res.data
          if (progress.in_progress) {
            setStatusMessage(`Crawling: ${progress.visited} pages visited`)
            setUploadProgress(Math.min(95, progress.visited))
          }
        } catch (err) {
          console.error('Progress poll failed:', err)
        }
      }, 2000)
    }

    startPolling()

    try {
      const res = await axios.post(`${API_URL}/upload-website`, {
        url: websiteUrl,
      })
      setUploadProgress(100)
      setStatusMessage('Complete!')
      setWebsiteSuccess(true)
      setWebsiteUrl('')
      fetchSkills()
    } catch (err) {
      console.error('Website upload failed:', err)
      alert(err.response?.data?.detail || 'Failed to extract website')
    } finally {
      if (pollInterval) clearInterval(pollInterval)
      setUploading(false)
      setTimeout(() => {
        setStatusMessage('')
        setUploadProgress(0)
      }, 2000)
    }
  }

  const askQuery = async () => {
    if (!selectedSkill || !query) return
    setQuerying(true)
    setAnswer('')

    try {
      const res = await axios.post(`${API_URL}/skills/${selectedSkill.id}/query`, {
        query,
      })
      setAnswer(res.data.answer)
    } catch (err) {
      console.error('Query failed:', err)
    } finally {
      setQuerying(false)
    }
  }

  const downloadSkill = async (skillId, format = 'skill') => {
    try {
      const link = document.createElement('a')
      link.href = `${API_URL}/skills/${skillId}/download?format=${format}`
      const ext = format === 'md' ? 'md' : format === 'json' ? 'json' : 'skill'
      link.download = `skill_${skillId}.${ext}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  const deleteSkill = async (skillId, skillName) => {
    if (!confirm(`Delete skill "${skillName}"?`)) return
    
    try {
      await axios.delete(`${API_URL}/skills/${skillId}`)
      fetchSkills()
    } catch (err) {
      console.error('Delete failed:', err)
      alert('Failed to delete skill')
    }
  }

  return (
    <div className="min-h-screen p-8 text-white">
      <div className="max-w-6xl mx-auto">
        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-bold mb-8 text-center bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent"
        >
          PDF to Skill
        </motion.h1>

        <div className="grid md:grid-cols-2 gap-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
          >
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 border border-gray-700">
              <h2 className="text-xl font-semibold mb-4 text-cyan-400">Upload PDF</h2>

              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-cyan-400 transition-colors cursor-pointer"
              >
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="fileInput"
                />
                <label htmlFor="fileInput" className="cursor-pointer">
                  {file ? (
                    <motion.p
                      initial={{ scale: 0.8 }}
                      animate={{ scale: 1 }}
                      className="text-green-400"
                    >
                      {file.name}
                    </motion.p>
                  ) : (
                    <p className="text-gray-400">
                      Drop PDF here or click to select
                    </p>
                  )}
                </label>
              </div>

              {file && (
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  onClick={uploadPdf}
                  disabled={uploading}
                  className="mt-4 w-full py-3 bg-gradient-to-r from-cyan-500 to-purple-600 rounded-lg font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {uploading ? `Uploading... ${uploadProgress}%` : 'Upload PDF'}
                </motion.button>
              )}

              {uploadSuccess && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mt-4 p-4 bg-green-500/20 border border-green-500 rounded-lg text-green-400 text-center"
                >
                  PDF uploaded successfully!
                </motion.div>
              )}

              <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 border border-gray-700 mt-6">
                <h2 className="text-xl font-semibold mb-4 text-purple-400">Or Create from Website</h2>

                <div className="flex gap-2">
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="flex-1 p-3 bg-gray-700/50 border border-gray-600 rounded-lg focus:border-purple-400 focus:outline-none text-white"
                  />
                  <button
                    onClick={uploadWebsite}
                    disabled={uploading || !websiteUrl}
                    className="px-4 py-3 bg-gradient-to-r from-purple-500 to-pink-600 rounded-lg font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    Extract
                  </button>
                </div>
<p className="text-gray-400 text-sm mt-2">
                  Extract content from any website URL
                </p>

                {uploading && (
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>{statusMessage || 'Processing...'}</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-purple-500 to-pink-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {websiteSuccess && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mt-4 p-4 bg-green-500/20 border border-green-500 rounded-lg text-green-400 text-center"
                >
                  Website skill built successfully!
                </motion.div>
              )}
            </div>

            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 border border-gray-700 mt-6">
              <h2 className="text-xl font-semibold mb-4 text-purple-400">Your Skills</h2>

              <div className="space-y-3 max-h-80 overflow-y-auto">
                <AnimatePresence>
                  {skills.length === 0 ? (
                    <p className="text-gray-400 text-center py-4">
                      No skills yet. Upload a PDF to build one.
                    </p>
                  ) : (
                    skills.map((skill) => (
                      <motion.div
                        key={skill.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        onClick={() => setSelectedSkill(skill)}
                        className={`p-4 rounded-lg cursor-pointer transition-all ${
                          selectedSkill?.id === skill.id
                            ? 'bg-gradient-to-r from-cyan-500/30 to-purple-500/30 border border-cyan-400'
                            : 'bg-gray-700/50 border border-gray-600 hover:border-gray-500'
                        }`}
                      >
                        <h3 className="font-semibold">{skill.name}</h3>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="px-2 py-1 bg-gray-600 rounded text-xs">
                            {skill.skill_type}
                          </span>
                          <span className="text-gray-400 text-xs">
                            {new Date(skill.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            downloadSkill(skill.id, 'skill')
                          }}
                          className="mt-2 mr-2 px-3 py-1 bg-purple-600 rounded text-xs hover:bg-purple-500"
                        >
                          .skill
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            downloadSkill(skill.id, 'md')
                          }}
                          className="mt-2 mr-2 px-3 py-1 bg-blue-600 rounded text-xs hover:bg-blue-500"
                        >
                          .md
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            downloadSkill(skill.id, 'json')
                          }}
                          className="mt-2 mr-2 px-3 py-1 bg-green-600 rounded text-xs hover:bg-green-500"
                        >
                          .json
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            if (confirm(`Delete "${skill.name}"?`)) {
                              axios.delete(`${API_URL}/skills/${skill.id}`).then(() => fetchSkills())
                            }
                          }}
                          className="mt-2 px-3 py-1 bg-red-600 rounded text-xs hover:bg-red-500"
                        >
                          Delete
                        </button>
                      </motion.div>
                    ))
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 border border-gray-700">
              <h2 className="text-xl font-semibold mb-4 text-green-400">Try Skill</h2>

              {!selectedSkill ? (
                <p className="text-gray-400 text-center py-8">
                  Select a skill from the left to query it.
                </p>
              ) : (
                <>
                  <div className="mb-4 p-3 bg-gray-700/50 rounded-lg">
                    <span className="text-gray-400">Selected: </span>
                    <span className="font-semibold text-cyan-400">
                      {selectedSkill.name}
                    </span>
                  </div>

                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask a question about this skill..."
                    className="w-full p-4 bg-gray-700/50 border border-gray-600 rounded-lg resize-none h-32 focus:border-cyan-400 focus:outline-none"
                  />

                  <button
                    onClick={askQuery}
                    disabled={querying || !query}
                    className="mt-4 w-full py-3 bg-gradient-to-r from-green-500 to-cyan-500 rounded-lg font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {querying ? 'Querying...' : 'Ask Question'}
                  </button>

                  {answer && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-4 p-4 bg-gray-700/50 border border-gray-600 rounded-lg"
                    >
                      <h4 className="text-gray-400 text-sm mb-2">Answer:</h4>
                      <p>{answer}</p>
                    </motion.div>
                  )}
                </>
              )}
            </div>

            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 border border-gray-700 mt-6">
              <h2 className="text-xl font-semibold mb-4 text-yellow-400">API Integration</h2>
              <p className="text-gray-400 text-sm mb-4">
                Other agents can query skills via API:
              </p>
              <code className="block p-3 bg-gray-900 rounded text-xs text-green-400 overflow-x-auto">
                POST /skills/{'{skill_id}'}/query
                <br />
                {"{ \"query\": \"your question\" }"}
              </code>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

export default App