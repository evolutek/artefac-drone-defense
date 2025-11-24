export const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__ !== undefined

export async function invoke<T>(cmd: string, args?: Record<string, any>): Promise<T> {
  if (!isTauri) throw new Error('tauri unavailable')
  const tauri = (window as any).__TAURI__
  const fn = tauri?.invoke || tauri?.core?.invoke
  if (typeof fn !== 'function') throw new Error('tauri invoke unavailable')
  return fn(cmd, args)
}

export async function startAll(): Promise<void> {
  await invoke('compose_up_all')
}

export async function stopAll(): Promise<void> {
  await invoke('compose_down_all')
}

export async function status(): Promise<{ services: Record<string, string> }>{
  return invoke('compose_ps')
}