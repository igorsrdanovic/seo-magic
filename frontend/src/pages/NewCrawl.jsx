import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { crawlsAPI } from '../api/client'

function NewCrawl() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    start_url: '',
    max_urls: 100,
    max_depth: 3,
    max_concurrent_requests: 5,
    render_javascript: false,
  })

  const createMutation = useMutation({
    mutationFn: (data) => crawlsAPI.create(data),
    onSuccess: async (response) => {
      const crawlId = response.data.id
      // Start the crawl
      await crawlsAPI.start(crawlId)
      // Navigate to detail page
      navigate(`/crawl/${crawlId}`)
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate({
      start_url: formData.start_url,
      config: {
        max_urls: parseInt(formData.max_urls),
        max_depth: parseInt(formData.max_depth),
        max_concurrent_requests: parseInt(formData.max_concurrent_requests),
        render_javascript: formData.render_javascript,
        respect_robots_txt: true,
        stay_in_subdomain: true,
      },
    })
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Create New Crawl</h2>
        <p style={{ marginBottom: '20px', color: '#666' }}>
          Configure your website crawl. The crawler will respect robots.txt and stay within the same subdomain.
        </p>

        {createMutation.isError && (
          <div className="error">
            Error creating crawl: {createMutation.error.message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Start URL *</label>
            <input
              type="url"
              className="input"
              placeholder="https://example.com"
              value={formData.start_url}
              onChange={(e) => setFormData({ ...formData, start_url: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>Max URLs</label>
            <input
              type="number"
              className="input"
              value={formData.max_urls}
              onChange={(e) => setFormData({ ...formData, max_urls: e.target.value })}
              min="1"
              max="10000"
            />
            <small style={{ color: '#666' }}>Maximum number of URLs to crawl (1-10,000)</small>
          </div>

          <div className="form-group">
            <label>Max Depth</label>
            <input
              type="number"
              className="input"
              value={formData.max_depth}
              onChange={(e) => setFormData({ ...formData, max_depth: e.target.value })}
              min="1"
              max="20"
            />
            <small style={{ color: '#666' }}>How deep to crawl from start URL (1-20)</small>
          </div>

          <div className="form-group">
            <label>Concurrent Requests</label>
            <input
              type="number"
              className="input"
              value={formData.max_concurrent_requests}
              onChange={(e) => setFormData({ ...formData, max_concurrent_requests: e.target.value })}
              min="1"
              max="20"
            />
            <small style={{ color: '#666' }}>Number of simultaneous requests (1-20)</small>
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.render_javascript}
                onChange={(e) => setFormData({ ...formData, render_javascript: e.target.checked })}
                style={{ marginRight: '8px' }}
              />
              Render JavaScript (slower, requires Playwright)
            </label>
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
            <button
              type="submit"
              className="button"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Start Crawl'}
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={() => navigate('/')}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default NewCrawl
