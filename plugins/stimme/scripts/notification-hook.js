// Notification-Hook: kurze Ansage, wenn Claude eine Freigabe braucht oder wartet.
const { loadConfig, speak, readStdinJson } = require('./lib');
const cfg = loadConfig();
const msg = (readStdinJson().message || '').toLowerCase();
const lines = cfg.notification_lines;
const text = msg.includes('permission') ? lines.permission : (msg.includes('waiting') || msg.includes('idle')) ? lines.idle : null;
if (text) speak([{ speaker: 'claude', text }], cfg);
