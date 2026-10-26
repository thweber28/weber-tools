export type Last = { at: number; input: number; output: number; read: number; write: number }
export type Totals = { input: number; output: number; read: number; write: number }

declare module 'claude-code' {
  interface PluginState {
    'cache-monitor': { last: Last | null; totals: Totals; now: number }
  }
}
