// Stop-Hook: spricht die 🔊-Zeilen am Ende der Antwort. Kehrt sofort zurück, die Stimme läuft abgekoppelt.
const { loadConfig, spokenParts, speak, readStdinJson } = require('./lib');
const cfg = loadConfig();
const data = readStdinJson();
speak(spokenParts(data.last_assistant_message || '', cfg), cfg);
