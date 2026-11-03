// Kleiner lokaler Server für das Untertitelfenster (nur 127.0.0.1). Beendet sich still, wenn der Port belegt ist.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { loadConfig, TMP } = require('./lib');
const port = loadConfig().caption_port || 4790;
const page = path.join(__dirname, '..', 'web', 'index.html');
http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  if (url === '/state.json') {
    let body = '{"id":0,"parts":[],"idx":0,"pos":-1,"len":0,"done":true}';
    try { body = fs.readFileSync(path.join(TMP, 'state.json'), 'utf8'); } catch {}
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    return res.end(body);
  }
  if (url === '/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(fs.readFileSync(page));
  }
  res.writeHead(404); res.end();
}).on('error', () => process.exit(0)).listen(port, '127.0.0.1');
