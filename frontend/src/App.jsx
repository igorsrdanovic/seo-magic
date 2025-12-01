import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import CrawlDetail from './pages/CrawlDetail'
import NewCrawl from './pages/NewCrawl'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="app">
          <header className="header">
            <div className="container">
              <h1>🕷️ SEO Spider</h1>
              <p>Web-based SEO auditing tool - Crawl, analyze, and optimize your website</p>
            </div>
          </header>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/crawl/new" element={<NewCrawl />} />
            <Route path="/crawl/:id" element={<CrawlDetail />} />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App
