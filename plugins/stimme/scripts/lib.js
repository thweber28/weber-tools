// Gemeinsame Funktionen: Konfiguration, Text bereinigen, Sprechzeilen finden, sprechen, stoppen.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const TMP = path.join(os.tmpdir(), 'claude-stimme');
const PIDFILE = path.join(TMP, 'player.pid');

function loadConfig() {
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'config.json'), 'utf8'));
  // Optionale eigene Einstellungen überschreiben die Standardwerte (überleben Plugin-Updates).
  try {
    const own = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.claude', 'stimme.json'), 'utf8'));
    return { ...cfg, ...own, voices: { ...cfg.voices, ...(own.voices || {}) } };
  } catch { return cfg; }
}

// Regieanweisungen [..], Sprech-Tags und Markdown entfernen; die Systemstimme kann damit nichts anfangen.
function clean(text) {
  return text
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/<\/?[a-z]+[^>]*>/gi, ' ')
    .replace(/[`*_#>~|]/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/ ([.,!?;:])/g, '$1')
    .trim();
}

function spokenParts(message, cfg) {
  const parts = [];
  for (const raw of message.split(/\r?\n/)) {
    let line = raw.trim().replace(/^[>*_ ]+/, '').trim();
    if (!line.startsWith(cfg.marker)) continue;
    line = line.slice(cfg.marker.length).trim();
    let speaker = 'claude';
    const i = line.indexOf(':');
    if (i > -1 && i <= 12 && !line.slice(0, i).includes('[')) {
      const label = line.slice(0, i).trim().toLowerCase();
      speaker = Object.keys(cfg.speaker_labels).find(k => cfg.speaker_labels[k].includes(label)) || 'claude';
      line = line.slice(i + 1).trim();
    }
    line = clean(line);
    if (line) parts.push({ speaker, text: line.slice(0, cfg.max_chars) });
  }
  return parts;
}

function stop() {
  try {
    const pid = parseInt(fs.readFileSync(PIDFILE, 'utf8'), 10);
    if (pid) process.kill(pid);
  } catch { /* nichts läuft */ }
  try { fs.unlinkSync(PIDFILE); } catch { /* egal */ }
}

function speak(parts, cfg) {
  if (!parts.length) return null;
  stop();
  if (process.env.STIMME_DRYRUN) { console.log(JSON.stringify(parts)); return null; }
  fs.mkdirSync(TMP, { recursive: true });
  const job = path.join(TMP, `job-${Date.now()}.json`);
  fs.writeFileSync(job, JSON.stringify({ parts, voices: cfg.voices, rate: cfg.rate }), 'utf8');
  let cmd, args;
  if (process.platform === 'win32') {
    cmd = 'powershell.exe';
    args = ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', path.join(__dirname, 'speak.ps1'), '-JobFile', job];
  } else if (process.platform === 'darwin') {
    cmd = 'say'; args = ['-v', 'Anna', parts.map(p => p.text).join('. ')];
  } else {
    cmd = 'espeak-ng'; args = ['-v', 'de', parts.map(p => p.text).join('. ')];
  }
  const child = spawn(cmd, args, { detached: true, stdio: 'ignore', windowsHide: true });
  child.on('error', () => {});
  if (child.pid) fs.writeFileSync(PIDFILE, String(child.pid));
  child.unref();
  return child.pid;
}

function readStdinJson() {
  try { return JSON.parse(fs.readFileSync(0, 'utf8')); } catch { return {}; }
}

module.exports = { loadConfig, spokenParts, speak, stop, readStdinJson, clean };
