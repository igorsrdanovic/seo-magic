import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { crawlsAPI } from '../api/client'

function Dashboard() {
  const { data: crawls, isLoading, error } = useQuery({
    queryKey: ['crawls'],
    queryFn: () => crawlsAPI.list().then(res => res.data),
    refetchInterval: 5000, // Refetch every 5 seconds for running crawls
  })

  if (isLoading) return <div className="container"><div className="loading">Loading crawls...</div></div>
  if (error) return <div className="container"><div className="error">Error loading crawls: {error.message}</div></div>

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>Your Crawls</h2>
          <Link to="/crawl/new">
            <button className="button">+ New Crawl</button>
          </Link>
        </div>

        {crawls && crawls.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            <p style={{ marginBottom: '20px' }}>No crawls yet. Create your first crawl to get started!</p>
            <Link to="/crawl/new">
              <button className="button">Create First Crawl</button>
            </Link>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>URL</th>
                <th>Status</th>
                <th>URLs Crawled</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {crawls && crawls.map((crawl) => (
                <tr key={crawl.id}>
                  <td>{crawl.id}</td>
                  <td>
                    <a href={crawl.start_url} target="_blank" rel="noopener noreferrer" style={{ color: '#667eea' }}>
                      {crawl.start_url}
                    </a>
                  </td>
                  <td>
                    <span className={`badge badge-${getStatusColor(crawl.status)}`}>
                      {crawl.status}
                    </span>
                  </td>
                  <td>{crawl.urls_crawled} / {crawl.urls_discovered}</td>
                  <td>{new Date(crawl.created_at).toLocaleString()}</td>
                  <td>
                    <Link to={`/crawl/${crawl.id}`}>
                      <button className="button button-secondary">View Details</button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function getStatusColor(status) {
  const colors = {
    completed: 'success',
    running: 'info',
    pending: 'warning',
    failed: 'error',
  }
  return colors[status] || 'info'
}

export default Dashboard
