import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { crawlsAPI } from '../api/client'

function NewCrawl() {
  const navigate = useNavigate()
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [formData, setFormData] = useState({
    start_url: '',
    max_urls: 1000,
    max_depth: 10,
    max_concurrent_requests: 5,
    request_delay_ms: 100,
    render_javascript: false,
    respect_robots_txt: true,
    stay_in_subdomain: true,
    crawl_images: true,
    store_raw_html: false,
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
        request_delay_ms: parseInt(formData.request_delay_ms),
        render_javascript: formData.render_javascript,
        respect_robots_txt: formData.respect_robots_txt,
        stay_in_subdomain: formData.stay_in_subdomain,
        crawl_images: formData.crawl_images,
        store_raw_html: formData.store_raw_html,
      },
    })
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Create New Crawl</h2>
        <p style={{ marginBottom: '20px', color: '#666' }}>
          Configure your SEO crawl. The crawler will automatically handle redirects and detect the correct domain.
        </p>

        {createMutation.isError && (
          <div className="error" style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#fee', border: '1px solid #fcc', borderRadius: '4px' }}>
            Error: {createMutation.error.message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Basic Settings */}
          <h3 style={{ marginTop: '0', marginBottom: '15px', fontSize: '18px' }}>Basic Settings</h3>

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
            <small style={{ color: '#666' }}>The URL where the crawl will begin</small>
          </div>

          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
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
              <small style={{ color: '#666' }}>1-10,000 URLs</small>
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
              <small style={{ color: '#666' }}>1-20 levels deep</small>
            </div>
          </div>

          {/* Scope Settings */}
          <h3 style={{ marginTop: '20px', marginBottom: '15px', fontSize: '18px' }}>Scope</h3>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.stay_in_subdomain}
                onChange={(e) => setFormData({ ...formData, stay_in_subdomain: e.target.checked })}
                style={{ marginRight: '8px' }}
              />
              <span>
                Stay within subdomain
                <small style={{ display: 'block', marginTop: '4px', color: '#666', fontWeight: 'normal' }}>
                  If unchecked, will crawl both www and non-www versions
                </small>
              </span>
            </label>
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.respect_robots_txt}
                onChange={(e) => setFormData({ ...formData, respect_robots_txt: e.target.checked })}
                style={{ marginRight: '8px' }}
              />
              <span>
                Respect robots.txt
                <small style={{ display: 'block', marginTop: '4px', color: '#666', fontWeight: 'normal' }}>
                  Follow robots.txt rules (recommended)
                </small>
              </span>
            </label>
          </div>

          {/* Advanced Settings */}
          <div style={{ marginTop: '20px', borderTop: '1px solid #e2e8f0', paddingTop: '20px' }}>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              style={{
                background: 'none',
                border: 'none',
                color: '#667eea',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: '500',
                padding: '0',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span style={{ transform: showAdvanced ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>▶</span>
              Advanced Options
            </button>

            {showAdvanced && (
              <div style={{ marginTop: '15px' }}>
                <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
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
                    <small style={{ color: '#666' }}>Parallel requests (1-20)</small>
                  </div>

                  <div className="form-group">
                    <label>Request Delay (ms)</label>
                    <input
                      type="number"
                      className="input"
                      value={formData.request_delay_ms}
                      onChange={(e) => setFormData({ ...formData, request_delay_ms: e.target.value })}
                      min="0"
                      max="5000"
                      step="100"
                    />
                    <small style={{ color: '#666' }}>Delay between requests</small>
                  </div>
                </div>

                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.render_javascript}
                      onChange={(e) => setFormData({ ...formData, render_javascript: e.target.checked })}
                      style={{ marginRight: '8px' }}
                    />
                    <span>
                      Render JavaScript
                      <small style={{ display: 'block', marginTop: '4px', color: '#666', fontWeight: 'normal' }}>
                        Use headless browser (slower, requires Playwright)
                      </small>
                    </span>
                  </label>
                </div>

                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.crawl_images}
                      onChange={(e) => setFormData({ ...formData, crawl_images: e.target.checked })}
                      style={{ marginRight: '8px' }}
                    />
                    <span>
                      Crawl images
                      <small style={{ display: 'block', marginTop: '4px', color: '#666', fontWeight: 'normal' }}>
                        Extract and analyze image data
                      </small>
                    </span>
                  </label>
                </div>

                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.store_raw_html}
                      onChange={(e) => setFormData({ ...formData, store_raw_html: e.target.checked })}
                      style={{ marginRight: '8px' }}
                    />
                    <span>
                      Store raw HTML
                      <small style={{ display: 'block', marginTop: '4px', color: '#666', fontWeight: 'normal' }}>
                        Save full HTML in database (increases storage)
                      </small>
                    </span>
                  </label>
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '30px' }}>
            <button
              type="submit"
              className="button"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Starting Crawl...' : 'Start Crawl'}
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

      {/* Help Card */}
      <div className="card" style={{ marginTop: '20px', backgroundColor: '#f7fafc' }}>
        <h3 style={{ marginTop: '0', fontSize: '16px' }}>💡 Tips</h3>
        <ul style={{ marginBottom: '0', paddingLeft: '20px', color: '#666' }}>
          <li><strong>Redirects handled automatically:</strong> If you crawl passged.com, it will detect the redirect to www.passged.com</li>
          <li><strong>Start with small crawls:</strong> Try 100-500 URLs first to test your settings</li>
          <li><strong>JavaScript rendering:</strong> Only enable if the site heavily relies on JS for content</li>
          <li><strong>Respect robots.txt:</strong> Always keep this enabled unless you have explicit permission</li>
        </ul>
      </div>
    </div>
  )
}

export default NewCrawl
