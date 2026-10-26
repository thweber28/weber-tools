#!/usr/bin/env node
// Statuszeile für Claude Code: Cache-Countdown (1h-TTL) mit Ampel, Tokens, Kosten.
// Liest das JSON von stdin (transcript_path, cost) und das Transcript (JSONL).
const fs = require('fs')
const TTL = 60 * 60 * 1000, YELLOW = 15 * 60 * 1000, RED = 5 * 60 * 1000
const k = n => (n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n))
const mmss = ms => { const s = Math.max(0, Math.floor(ms / 1000)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0') }
let raw = ''
process.stdin.on('data', d => (raw += d)).on('end', () => {
  let input = {}
  try { input = JSON.parse(raw) } catch {}
  let last = null
  const sum = { input: 0, output: 0, read: 0, write: 0 }
  const byId = new Map() // pro API-Antwort (message.id) nur der letzte Eintrag zählt
  try {
    let n = 0
    for (const line of fs.readFileSync(input.transcript_path, 'utf8').split('\n')) {
      if (!line) continue
      let e; try { e = JSON.parse(line) } catch { continue }
      const u = e && e.message && e.message.usage
      if (e.type !== 'assistant' || !u) continue
      const cur = { at: Date.parse(e.timestamp), main: !e.isSidechain, input: u.input_tokens || 0, output: u.output_tokens || 0, read: u.cache_read_input_tokens || 0, write: u.cache_creation_input_tokens || 0 }
      byId.set(e.message.id || 'n' + n++, cur)
    }
    for (const cur of byId.values()) {
      sum.input += cur.input; sum.output += cur.output; sum.read += cur.read; sum.write += cur.write
      if (cur.main) last = cur // Cache-Uhr nur Hauptthread; Summen enthalten auch Subagenten wie die Kosten
    }
  } catch {}
  let lamp = '🔴', t = 'kalt', color = '31'
  if (last && !Number.isNaN(last.at) && (last.read || last.write)) {
    const left = TTL - Math.max(0, Date.now() - last.at)
    if (left > 0) {
      t = mmss(left)
      if (left > YELLOW) { lamp = '🟢'; color = '32' } else if (left >= RED) { lamp = '🟡'; color = '33' }
    }
  }
  const ctx = last ? k(last.input + last.read + last.write) : '?'
  const cost = input.cost && typeof input.cost.total_cost_usd === 'number' ? ' · $' + input.cost.total_cost_usd.toFixed(2) : ''
  const lastTxt = last ? `letzte Antwort: in ${k(last.input)} out ${k(last.output)} lesen ${k(last.read)} schr. ${k(last.write)}` : 'noch keine Antwort'
  process.stdout.write(`\x1b[${color}m${lamp} Cache ${t}\x1b[0m · Ctx ${ctx} · ${lastTxt} · Σ in ${k(sum.input)} out ${k(sum.output)} lesen ${k(sum.read)} schr. ${k(sum.write)}${cost}`)
})
