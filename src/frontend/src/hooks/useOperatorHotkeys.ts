import { useEffect, type Dispatch, type SetStateAction } from 'react'
import { isTextTarget } from '@/lib/investigation'

interface OperatorHotkeys {
  selectSat: (index: number | null) => void
  graphOpen: boolean
  setGraphOpen: Dispatch<SetStateAction<boolean>>
  catalogOpen: boolean
  setCatalogOpen: Dispatch<SetStateAction<boolean>>
  paletteOpen: boolean
  setPaletteOpen: Dispatch<SetStateAction<boolean>>
  setLeftOpen: Dispatch<SetStateAction<boolean>>
  setRightOpen: Dispatch<SetStateAction<boolean>>
  openPoc: () => void
}

/** Keyboard chrome extracted from Home (T1). Behaviour unchanged. */
export function useOperatorHotkeys({
  selectSat,
  graphOpen,
  setGraphOpen,
  catalogOpen,
  setCatalogOpen,
  paletteOpen,
  setPaletteOpen,
  setLeftOpen,
  setRightOpen,
  openPoc,
}: OperatorHotkeys) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
        return
      }
      if (e.key === 'Escape') {
        if (paletteOpen) {
          setPaletteOpen(false)
          return
        }
        if (graphOpen) {
          setGraphOpen(false)
          return
        }
        if (catalogOpen) {
          setCatalogOpen(false)
          return
        }
        selectSat(null)
        return
      }
      if (isTextTarget(e.target)) return
      if (e.key === '/') {
        e.preventDefault()
        document.getElementById('athena-search')?.focus()
        return
      }
      const k = e.key.toLowerCase()
      if (k === 'g') {
        setGraphOpen((v) => !v)
        return
      }
      if (k === 'p') {
        openPoc()
        return
      }
      if (k === 'b') {
        setLeftOpen((v) => !v)
        return
      }
      if (k === 'i') {
        setRightOpen((v) => !v)
        return
      }
      if (k === 'c') {
        setCatalogOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [
    selectSat,
    graphOpen,
    catalogOpen,
    paletteOpen,
    openPoc,
    setGraphOpen,
    setCatalogOpen,
    setPaletteOpen,
    setLeftOpen,
    setRightOpen,
  ])
}
