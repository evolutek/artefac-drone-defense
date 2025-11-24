import { invoke as tauriInvoke } from '@tauri-apps/api/tauri'

export const isTauri = true

export async function invoke<T>(cmd: string, args?: Record<string, any>): Promise<T> {
  return tauriInvoke(cmd, args)
}

export async function startAll(): Promise<void> {
  await invoke('compose_up_all');
}

export async function stopAll(): Promise<void> {
  await invoke('compose_down_all');
}

export async function status(): Promise<{ services: Record<string, string> }>{
  return invoke('compose_ps');
}