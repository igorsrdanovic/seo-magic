import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { crawlsAPI, urlsAPI, issuesAPI } from '../api/client'

function CrawlDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')

  // Fetch crawl details
  const { data: crawl, isLoading: crawlLoading } = useQuery({
    queryKey: ['crawl', id],
    queryFn: () => crawlsAPI.get(id).then(res => res.data),
    refetchInterval: (data) => {
      // Keep polling if crawl is running
      return data?.status === 'running' ? 2000 : false
    },
  })

  // Fetch URL summary
  const { data: urlSummary } = useQuery({
    queryKey: ['urlSummary', id],
    queryFn: () => urlsAPI.summary(id).then(res => res.data),
    enabled: !!crawl && crawl.status !== 'pending',
  })

  // Fetch issue summary
  const { data: issueSummary } = useQuery({
    queryKey: ['issueSummary', id],
    queryFn: () => issuesAPI.summary(id).then(res => res.data),
    enabled: !!crawl && crawl.status === 'completed',
  })

  // Fetch URLs list
  const { data: urls } = useQuery({
    queryKey: ['urls', id],
    queryFn: () => urlsAPI.list(id).then(res => res.data),
    enabled: activeTab === 'urls' && !!crawl,
  })

  // Fetch issues list
  const { data: issues } = useQuery({
    queryKey: ['issues', id],
    queryFn: () => issuesAPI.list(id).then(res => res.data),
    enabled: activeTab === 'issues' && !!crawl,
  })

  if (crawlLoading) {
    return (
      <div className="container">
        <div className="loading">Loading crawl details...</div>
      </div>
    )
  }

  if (!crawl) {
    return (
      <div className="container">
        <div className="error">Crawl not found</div>
      </div>
    )
  }

  return (
    <div className="container">
      {/* Header */}
      <div className="card">
        <button
          className="button button-secondary"
          onClick={() => navigate('/')}
          style={{ marginBottom: '15px' }}
        >
          ← Back to Dashboard
        </button>

        <h2>Crawl Details</h2>
        <div style={{ marginTop: '15px' }}>
          <div style={{ marginBottom: '10px' }}>
            <strong>URL:</strong>{' '}
            <a href={crawl.start_url} target="_blank" rel="noopener noreferrer" style={{ color: '#667eea' }}>
              {crawl.start_url}
            </a>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <strong>Status:</strong>{' '}
            <span className={`badge badge-${getStatusColor(crawl.status)}`}>
              {crawl.status}
            </span>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <strong>Progress:</strong> {crawl.urls_crawled} URLs crawled, {crawl.urls_discovered} discovered
          </div>
          {crawl.started_at && (
            <div style={{ marginBottom: '10px' }}>
              <strong>Started:</strong> {new Date(crawl.started_at).toLocaleString()}
            </div>
          )}
          {crawl.completed_at && (
            <div style={{ marginBottom: '10px' }}>
              <strong>Completed:</strong> {new Date(crawl.completed_at).toLocaleString()}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="card" style={{ padding: '0' }}>
        <div style={{ display: 'flex', borderBottom: '2px solid #e2e8f0' }}>
          <button
            className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={`tab-button ${activeTab === 'urls' ? 'active' : ''}`}
            onClick={() => setActiveTab('urls')}
          >
            URLs ({crawl.urls_crawled})
          </button>
          <button
            className={`tab-button ${activeTab === 'issues' ? 'active' : ''}`}
            onClick={() => setActiveTab('issues')}
          >
            Issues
          </button>
        </div>

        <div style={{ padding: '20px' }}>
          {activeTab === 'overview' && (
            <OverviewTab
              crawl={crawl}
              urlSummary={urlSummary}
              issueSummary={issueSummary}
            />
          )}
          {activeTab === 'urls' && (
            <URLsTab crawlId={id} urls={urls} />
          )}
          {activeTab === 'issues' && (
            <IssuesTab crawlId={id} issues={issues} />
          )}
        </div>
      </div>
    </div>
  )
}

function OverviewTab({ crawl, urlSummary, issueSummary }) {
  if (crawl.status === 'pending') {
    return <div style={{ color: '#666' }}>Crawl has not started yet.</div>
  }

  if (crawl.status === 'running') {
    return (
      <div>
        <h3>Crawl in Progress</h3>
        <p style={{ color: '#666', marginBottom: '20px' }}>
          The crawler is currently running. Statistics will be available when the crawl completes.
        </p>
        <div className="grid">
          <div className="stat-card">
            <h3>URLs Crawled</h3>
            <div className="value">{crawl.urls_crawled}</div>
          </div>
          <div className="stat-card">
            <h3>URLs Discovered</h3>
            <div className="value">{crawl.urls_discovered}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h3>Crawl Statistics</h3>

      {/* URL Summary */}
      {urlSummary && (
        <>
          <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>URL Status Codes</h4>
          <div className="grid">
            {Object.entries(urlSummary.by_status_code || {}).map(([code, count]) => (
              <div key={code} className="stat-card">
                <h3>Status {code}</h3>
                <div className="value">{count}</div>
              </div>
            ))}
          </div>

          <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Indexability</h4>
          <div className="grid">
            <div className="stat-card">
              <h3>Indexable</h3>
              <div className="value" style={{ color: '#22543d' }}>
                {urlSummary.indexable || 0}
              </div>
            </div>
            <div className="stat-card">
              <h3>Non-Indexable</h3>
              <div className="value" style={{ color: '#7f1d1d' }}>
                {urlSummary.non_indexable || 0}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Issue Summary */}
      {issueSummary && (
        <>
          <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Issues by Category</h4>
          <div className="grid">
            {Object.entries(issueSummary.by_category || {}).map(([category, count]) => (
              <div key={category} className="stat-card">
                <h3>{category.replace('_', ' ').toUpperCase()}</h3>
                <div className="value">{count}</div>
              </div>
            ))}
          </div>

          <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Issues by Severity</h4>
          <div className="grid">
            {Object.entries(issueSummary.by_severity || {}).map(([severity, count]) => (
              <div key={severity} className="stat-card">
                <h3>{severity}</h3>
                <div className="value" style={{ color: getSeverityColor(severity) }}>
                  {count}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function URLsTab({ crawlId, urls }) {
  if (!urls || urls.length === 0) {
    return <div style={{ color: '#666' }}>No URLs found.</div>
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h3>Crawled URLs</h3>
        <a href={urlsAPI.exportCSV(crawlId)} download>
          <button className="button button-secondary">Export CSV</button>
        </a>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>URL</th>
              <th>Status</th>
              <th>Title</th>
              <th>Indexable</th>
              <th>Response Time</th>
            </tr>
          </thead>
          <tbody>
            {urls.map((url) => (
              <tr key={url.id}>
                <td>
                  <a href={url.address} target="_blank" rel="noopener noreferrer" style={{ color: '#667eea' }}>
                    {truncateUrl(url.address)}
                  </a>
                </td>
                <td>
                  <span className={`badge badge-${getStatusCodeColor(url.status_code)}`}>
                    {url.status_code}
                  </span>
                </td>
                <td>{truncate(url.title, 50)}</td>
                <td>
                  <span className={`badge badge-${url.indexable ? 'success' : 'error'}`}>
                    {url.indexable ? 'Yes' : 'No'}
                  </span>
                </td>
                <td>{url.response_time ? `${url.response_time}ms` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function IssuesTab({ crawlId, issues }) {
  if (!issues || issues.length === 0) {
    return <div style={{ color: '#666' }}>No issues found. Great job!</div>
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h3>SEO Issues</h3>
        <a href={issuesAPI.exportCSV(crawlId)} download>
          <button className="button button-secondary">Export CSV</button>
        </a>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Severity</th>
              <th>Type</th>
              <th>Message</th>
              <th>URLs Affected</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, idx) => (
              <tr key={idx}>
                <td>
                  <span className="badge badge-info">
                    {issue.category.replace('_', ' ')}
                  </span>
                </td>
                <td>
                  <span className={`badge badge-${getSeverityBadge(issue.severity)}`}>
                    {issue.severity}
                  </span>
                </td>
                <td>{issue.issue_type.replace('_', ' ')}</td>
                <td>{issue.message}</td>
                <td>
                  {issue.url && (
                    <a href={issue.url} target="_blank" rel="noopener noreferrer" style={{ color: '#667eea' }}>
                      {truncateUrl(issue.url)}
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Helper functions
function getStatusColor(status) {
  const colors = {
    completed: 'success',
    running: 'info',
    pending: 'warning',
    failed: 'error',
  }
  return colors[status] || 'info'
}

function getStatusCodeColor(code) {
  if (code >= 200 && code < 300) return 'success'
  if (code >= 300 && code < 400) return 'warning'
  if (code >= 400) return 'error'
  return 'info'
}

function getSeverityColor(severity) {
  const colors = {
    error: '#7f1d1d',
    warning: '#78350f',
    info: '#1e3a8a',
  }
  return colors[severity] || '#666'
}

function getSeverityBadge(severity) {
  const badges = {
    error: 'error',
    warning: 'warning',
    info: 'info',
  }
  return badges[severity] || 'info'
}

function truncateUrl(url, maxLength = 60) {
  if (!url) return '-'
  if (url.length <= maxLength) return url
  return url.substring(0, maxLength) + '...'
}

function truncate(text, maxLength) {
  if (!text) return '-'
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export default CrawlDetail
