import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Last, Totals } from '../types'

// Cache-TTL: 1 Stunde (Anthropic Prompt Caching, erweiterte TTL); jeder Treffer erneuert sie.
const TTL_MS = 60 * 60 * 1000
const YELLOW_MS = 15 * 60 * 1000
const RED_MS = 5 * 60 * 1000
const TICK_MS = 10000
const PANE = 'cache-monitor'

const ZERO: Totals = { input: 0, output: 0, read: 0, write: 0 }
const last = atom({ plugin: 'cache-monitor', key: 'last' } as const, null)
const totals = atom({ plugin: 'cache-monitor', key: 'totals' } as const, ZERO)
const clock = atom({ plugin: 'cache-monitor', key: 'now' } as const, 0)

const k = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`)

const mmss = (ms: number) => {
  const s = Math.max(0, Math.floor(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

// Ohne Cache-Schreiben/-Lesen im letzten Turn gilt der Cache als kalt.
const lamp = (l: Last | null, now: number) => {
  if (l === null || (l.read === 0 && l.write === 0)) return { c: 'error', s: '🔴', t: 'kalt' }
  const left = TTL_MS - Math.max(0, now - l.at)
  if (left <= 0) return { c: 'error', s: '🔴', t: 'kalt' }
  if (left < RED_MS) return { c: 'error', s: '🔴', t: mmss(left) }
  if (left <= YELLOW_MS) return { c: 'warning', s: '🟡', t: mmss(left) }
  return { c: 'success', s: '🟢', t: mmss(left) }
}

const summary = (l: Last | null, t: Totals, now: number, tokens: number | undefined, window: number, percent: number | undefined, usd: number | undefined) => {
  const p = lamp(l, now)
  const ctx = `Ctx ${tokens === undefined ? '?' : k(tokens)}/${k(window)} (${percent === undefined ? '?' : Math.round(percent)}%)`
  const turn = l === null ? 'Turn: –' : `Turn in ${k(l.input)} out ${k(l.output)} lesen ${k(l.read)} schreiben ${k(l.write)}`
  const sum = `Σ in ${k(t.input)} out ${k(t.output)} lesen ${k(t.read)} schreiben ${k(t.write)}`
  const cost = usd === undefined ? '' : ` · $${usd.toFixed(2)}`
  return { p, text: `${p.s} Cache ${p.t} · ${ctx} · ${turn} · ${sum}${cost}` }
}

async function refresh($: any) {
  try {
    const now: number = await $.clock.now()
    await update($, clock, () => now)
    const u = await $.session.usage()
    const s = summary(await read($, last), await read($, totals), now, u.context.tokens, u.context.window, u.context.percent, u.cost?.usd)
    $.ui.status(s.text)
  } catch {
    // Anzeige darf nie die Sitzung stören.
  }
}

let timer: { cancel: () => void } | undefined

// Timer auch starten, wenn die Mod mitten in einer Sitzung geladen wird (kein session.start).
let isCommandRegistered = false

async function currentText($: any): Promise<string> {
  const now: number = await $.clock.now()
  const u = await $.session.usage()
  const l = await read($, last)
  return summary(l, await read($, totals), Math.max(now, l?.at ?? 0), u.context.tokens, u.context.window, u.context.percent, u.cost?.usd).text
}

function ensureTimer($: any) {
  if (!timer) timer = $.clock.every(TICK_MS, () => void refresh($))
  if (!isCommandRegistered) {
    isCommandRegistered = true
    void $.command.register({ name: 'cache', description: 'Cache-Countdown, Tokens und Kosten anzeigen' })
    void $.ui.open({ id: PANE, title: 'Cache-Monitor' })
  }
}

export const register: Register = (on) => {
  on('session.start', async ($, e, next) => {
    timer?.cancel()
    timer = undefined
    ensureTimer($)
    await refresh($)
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    timer?.cancel()
    timer = undefined
    return next(e)
  })

  // Auf jeder Oberfläche: /cache zeigt die Ampel als Text.
  on('command.run', { command: 'cache' }, async ($) => {
    ensureTimer($)
    try {
      void $.ui.open({ id: PANE, title: 'Cache-Monitor' })
      return { text: await currentText($) }
    } catch {
      return { text: 'Cache-Daten derzeit nicht verfügbar.' }
    }
  })

  // Dauer-Anzeige als Pane (Terminal, Desktop, VS Code, App); die Uhr-Atom-Lesung hält sie aktuell.
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const l = await read($, last)
    const t = await read($, totals)
    let u: any
    try {
      u = await $.session.usage()
    } catch {
      return <Text dimColor>Daten derzeit nicht verfügbar.</Text>
    }
    const now = Math.max(await read($, clock), await $.clock.now(), l?.at ?? 0)
    const p = lamp(l, now)
    const tokens: number | undefined = u.context.tokens
    return (
      <Box flexDirection="column">
        <Text color={p.c}>{p.s} Cache {p.t}</Text>
        <Text>Kontext {tokens === undefined ? '?' : k(tokens)}/{k(u.context.window)} ({u.context.percent === undefined ? '?' : Math.round(u.context.percent)}%)</Text>
        <Text dimColor>Letzter Turn: in {k(l?.input ?? 0)} out {k(l?.output ?? 0)}</Text>
        <Text dimColor>Cache lesen {k(l?.read ?? 0)} schreiben {k(l?.write ?? 0)}</Text>
        <Text dimColor>Σ seit Mod-Start: in {k(t.input)} out {k(t.output)}</Text>
        <Text dimColor>Σ Cache lesen {k(t.read)} schreiben {k(t.write)}</Text>
        {u.cost ? <Text>Kosten Sitzung ${u.cost.usd.toFixed(2)}</Text> : null}
      </Box>
    )
  })

  // Nach Compact ist der Cache kalt; Zähler der Sitzung bleiben.
  on('session.compact', async ($, e, next) => {
    await update($, last, () => null)
    return next(e)
  })

  // Ende eines Turns (Hauptthread): Cache-TTL beginnt neu, Summen laufen weiter.
  on('turn.complete', async ($, e, next) => {
    const r = await next(e)
    ensureTimer($)
    const u = e.usage ?? r.usage
    if (u) {
      const at: number = await $.clock.now()
      const cur: Last = {
        at,
        input: u.input_tokens ?? 0,
        output: u.output_tokens ?? 0,
        read: u.cache_read_input_tokens ?? 0,
        write: u.cache_creation_input_tokens ?? 0,
      }
      // Cache-Uhr nur für den Hauptthread; Summen auch für Subagenten (Kosten enthalten sie).
      if (!e.agentId) await update($, last, () => cur)
      await update($, totals, (t) => ({
        input: t.input + cur.input,
        output: t.output + cur.output,
        read: t.read + cur.read,
        write: t.write + cur.write,
      }))
      await refresh($)
    }
    return r
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    ensureTimer($)
    const l = await read($, last)
    let u: any
    try {
      u = await $.session.usage()
    } catch {
      return next(e)
    }
    const now = Math.max(await read($, clock), await $.clock.now(), l?.at ?? 0)
    const s = summary(l, await read($, totals), now, u.context.tokens, u.context.window, u.context.percent, u.cost?.usd)
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box>
        <Text color={s.p.c}>{s.text}</Text>
      </Box>
    )
  })
}
