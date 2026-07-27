import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/** Catches render crashes so the user never sees a silent black screen. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI crash', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full w-full flex-col items-center justify-center bg-black px-6 text-center text-zinc-200">
          <div className="text-lg font-semibold tracking-wider text-rose-300">
            UI error
          </div>
          <p className="mt-3 max-w-lg text-sm leading-relaxed text-zinc-400">
            {this.state.error.message}
          </p>
          <button
            type="button"
            className="athena-btn athena-btn-active mt-6 px-4 py-2 text-xs"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
