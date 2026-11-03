// Notification-Hook: kurze Ansage, wenn Claude eine Freigabe braucht oder wartet.
const { loadConfig, speak, readStdinJson } = require('./lib');
const cfg = loadConfig();
const data = readStdinJson();
const msg = (data.message || '').toLowerCase();
const type = data.notification_type || '';
const lines = cfg.notification_lines;
const text = (type === 'permission_prompt' || msg.includes('permission')) ? lines.permission : (type === 'idle_prompt' || msg.includes('waiting') || msg.includes('idle')) ? lines.idle : null;
if (text) speak([{ speaker: 'claude', text }], cfg);
