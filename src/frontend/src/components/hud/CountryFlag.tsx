import { useState } from 'react'
import {
  countryFlagEmoji,
  countryFlagUrl,
  countryLabel,
} from '@/lib/country-flag'

interface CountryFlagProps {
  code?: string | null
  className?: string
  /** Pixel width of flag image (height scales ~3/4). */
  size?: number
}

/**
 * Country flag badge — uses flagcdn PNG (reliable on Linux).
 * Falls back to emoji/globe for INTL or load errors.
 */
export default function CountryFlag({
  code,
  className = '',
  size = 18,
}: CountryFlagProps) {
  const [failed, setFailed] = useState(false)
  const url = countryFlagUrl(code, size >= 24 ? 40 : 20)
  const label = countryLabel(code)
  const h = Math.round(size * 0.75)

  if (!url || failed) {
    return (
      <span
        className={`inline-flex shrink-0 items-center justify-center text-[14px] leading-none ${className}`}
        title={label}
        aria-label={label}
      >
        {countryFlagEmoji(code)}
      </span>
    )
  }

  return (
    <img
      src={url}
      alt={label}
      title={label}
      width={size}
      height={h}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className={`inline-block shrink-0 rounded-[1px] object-cover shadow-[0_0_0_1px_rgba(255,255,255,0.15)] ${className}`}
      style={{ width: size, height: h }}
    />
  )
}
