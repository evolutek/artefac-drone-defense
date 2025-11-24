use tauri::Manager;
#[tauri::command]
fn compose_up_all() -> Result<(), String> {
  let mut cmd = std::process::Command::new("docker");
  cmd.args(["compose", "up", "-d", "mqtt", "backend", "frontend", "simulation", "ros2_integration"]);
  let out = cmd.output().map_err(|e| e.to_string())?;
  if !out.status.success() { return Err(String::from_utf8_lossy(&out.stderr).to_string()); }
  Ok(())
}

#[tauri::command]
fn compose_down_all() -> Result<(), String> {
  let mut cmd = std::process::Command::new("docker");
  cmd.args(["compose", "down"]);
  let out = cmd.output().map_err(|e| e.to_string())?;
  if !out.status.success() { return Err(String::from_utf8_lossy(&out.stderr).to_string()); }
  Ok(())
}

#[tauri::command]
fn compose_ps() -> Result<serde_json::Value, String> {
  let out = std::process::Command::new("docker").args(["compose", "ps"]).output().map_err(|e| e.to_string())?;
  if !out.status.success() { return Err(String::from_utf8_lossy(&out.stderr).to_string()); }
  let text = String::from_utf8_lossy(&out.stdout);
  let mut map = serde_json::Map::new();
  for line in text.lines().skip(2) {
    let parts: Vec<&str> = line.split_whitespace().collect();
    if parts.len() >= 5 {
      map.insert(parts[0].to_string(), serde_json::Value::String(parts[4..].join(" ")));
    }
  }
  Ok(serde_json::json!({"services": map}))
}

#[tauri::command]
fn capture_console(level: String, message: String) {
  println!("[{}] {}", level, message);
}

#[tauri::command]
fn capture_error(message: String, stack: Option<String>) {
  eprintln!("[error] {} {}", message, stack.unwrap_or_default());
}

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        for w in app.windows().values() {
          w.open_devtools();
          let _ = w.eval("location.href='http://127.0.0.1:8080'");
          let _ = w.eval("(function(){const api=window.__TAURI__;if(!api||!api.invoke)return;const inv=api.invoke;function send(l,m){try{inv('capture_console',{level:l,message:String(m)})}catch(e){}}['log','info','warn','error'].forEach(k=>{const o=console[k].bind(console);console[k]=function(){try{send(k,Array.from(arguments).map(a=>{try{return JSON.stringify(a)}catch(e){return String(a)}}).join(' '))}catch(e){}o.apply(console,arguments)}});window.addEventListener('error',e=>{try{inv('capture_error',{message:String(e.message||e.error||e),stack:e.error&&e.error.stack?String(e.error.stack):null})}catch(_){}});window.addEventListener('unhandledrejection',e=>{try{inv('capture_error',{message:String(e.reason),stack:null})}catch(_){}});console.log('tauri-console-hook-ready')})();");
        }
      }
      Ok(())
    })
    .on_page_load(|window, _| {
      if cfg!(debug_assertions) {
        window.open_devtools();
      }
      println!("Loaded window {}", window.label());
    })
    .invoke_handler(tauri::generate_handler![compose_up_all, compose_down_all, compose_ps, capture_console, capture_error])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}