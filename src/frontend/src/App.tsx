import Home from './pages/Home'
import ErrorBoundary from './components/ErrorBoundary'

export default function App() {
  return (
    <ErrorBoundary>
      <Home />
    </ErrorBoundary>
  )
}
