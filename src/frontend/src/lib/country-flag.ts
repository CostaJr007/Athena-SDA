/**
 * Country / org code helpers for Mission board flags.
 * Linux often fails to render emoji flags — use flagcdn images instead.
 */

/** Map non-ISO catalog codes → ISO 3166-1 alpha-2 for flagcdn. */
const CODE_TO_ISO: Record<string, string> = {
  US: 'us',
  USA: 'us',
  CN: 'cn',
  CHN: 'cn',
  RU: 'ru',
  RUS: 'ru',
  DE: 'de',
  DEU: 'de',
  IT: 'it',
  ITA: 'it',
  FR: 'fr',
  FRA: 'fr',
  GB: 'gb',
  UK: 'gb',
  JP: 'jp',
  JPN: 'jp',
  IN: 'in',
  IND: 'in',
  BR: 'br',
  BRA: 'br',
  KR: 'kr',
  KOR: 'kr',
  IL: 'il',
  ISR: 'il',
  EU: 'eu',
}

export function countryLabel(code?: string | null): string {
  if (!code) return '—'
  return code.trim().toUpperCase()
}

/** Resolve catalog country code to lowercase ISO for flagcdn, or null if special. */
export function countryIso(code?: string | null): string | null {
  if (!code) return null
  const c = code.trim().toUpperCase()
  if (c === 'INTL' || c === 'INT' || c === 'INTERNATIONAL') return null
  if (CODE_TO_ISO[c]) return CODE_TO_ISO[c]
  if (/^[A-Z]{2}$/.test(c)) return c.toLowerCase()
  return null
}

/** flagcdn URL (works on Linux where emoji flags often fail). */
export function countryFlagUrl(code?: string | null, w = 20): string | null {
  const iso = countryIso(code)
  if (!iso) return null
  return `https://flagcdn.com/w${w}/${iso}.png`
}

/** Fallback emoji when no image (INTL / unknown). */
export function countryFlagEmoji(code?: string | null): string {
  if (!code) return '🏳️'
  const c = code.trim().toUpperCase()
  if (c === 'INTL' || c === 'INT' || c === 'INTERNATIONAL') return '🌐'
  if (c === 'UNK' || c === 'UNKNOWN') return '🏳️'
  // ISO → regional indicators (often blank on Linux; prefer CountryFlag img)
  if (/^[A-Z]{2}$/.test(c)) {
    try {
      return String.fromCodePoint(
        ...[...c].map((ch) => 0x1f1e6 - 65 + ch.charCodeAt(0)),
      )
    } catch {
      return '🏳️'
    }
  }
  return '🏳️'
}

/** @deprecated use CountryFlag component or countryFlagEmoji — kept for HMR/stale imports */
export const countryFlag = countryFlagEmoji
