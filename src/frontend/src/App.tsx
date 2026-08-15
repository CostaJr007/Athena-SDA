import { lazy, Suspense } from 'react'
import ErrorBoundary from './components/ErrorBoundary'

const Home = lazy(() => import('./pages/Home'))

export default function App() {
  return (
    <ErrorBoundary>
      <Suspense
        fallback={
          <div className="flex h-full items-center justify-center bg-black text-sm text-zinc-500">
            Loading mission board…
          </div>
        }
      >
        <Home />
      </Suspense>
    </ErrorBoundary>
  )
}
