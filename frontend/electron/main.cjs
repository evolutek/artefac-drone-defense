const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const fs = require('fs')
const os = require('os')

let gazeboHarmonic = null
let gazeboMvp = null
let websocketProc = null

function harmonicSdfPath() {
  return '/Users/dalm1/Desktop/reroll/Progra/drone-def/REROLL/artefac-drone-defense/simulation/gazebo_worlds/harmonic_heightmap.sdf'
}

function mvpSdfPath() {
  return path.join(__dirname, '..', '..', 'simulation', 'gazebo_worlds', 'model.sdf')
}

function attachProcLogs(proc) {
  if (!proc) return
  proc.stdout && proc.stdout.on('data', d => {
    console.log(`[gazebo] ${d.toString()}`)
  })
  proc.stderr && proc.stderr.on('data', d => {
    console.error(`[gazebo] ${d.toString()}`)
  })
  proc.on('exit', (code, signal) => {
    console.log(`gazebo exited code=${code} signal=${signal}`)
  })
}

function spawnGazeboForSdf(sdf, tag) {
  const projectRoot = path.join(__dirname, '..', '..')
  const resourcePaths = [
    path.join(projectRoot, 'simulation', 'gazebo_worlds'),
    path.join(projectRoot, 'simulation', 'models'),
  ].join(':')
  const env = { ...process.env, GZ_SIM_RESOURCE_PATH: resourcePaths }
  try {
    const gzProc = spawn('gz', ['sim', '-v', '4', '-s', '-r', sdf], { env })
    gzProc.on('error', () => {
      const classicProc = spawn('gazebo', [sdf, '--verbose'], { env })
      attachProcLogs(classicProc)
      console.log(`[${tag}] classic started`)
      return classicProc
    })
    attachProcLogs(gzProc)
    console.log(`[${tag}] gazebo garden started`)
    return gzProc
  } catch (e) {
    try {
      const classicProc = spawn('gazebo', [sdf, '--verbose'], { env: process.env })
      attachProcLogs(classicProc)
      console.log(`[${tag}] classic started`)
      return classicProc
    } catch (err) {
      console.error(`[${tag}] failed to spawn gazebo:`, err)
      return null
    }
  }
}

function startWebsocketServer(port = 9002) {
  try {
    const tmp = os.tmpdir()
    const ignPath = path.join(tmp, `websocket_${port}.ign`)
    const gzPath = path.join(tmp, `websocket_${port}.gzlaunch`)
    const gzContent = `<?xml version='1.0'?>\n<gz version='1.0'>\n  <plugin name='gz::launch::WebsocketServer' filename='gz-launch-websocket-server'>\n    <port>${port}</port>\n  </plugin>\n</gz>`
    fs.writeFileSync(gzPath, gzContent)
    const proc = spawn('gz', ['launch', '-v', '4', gzPath], { env: process.env })
    attachProcLogs(proc)
    console.log(`[websocket] server started on ws://localhost:${port}`)
    return proc
  } catch (err) {
    console.error('[websocket] failed to start websocket server:', err)
    return null
  }
}

function startDockerSim(worldName, tag) {
  const projectRoot = path.join(__dirname, '..', '..')
  const up = spawn('docker', ['compose', 'up', '-d', 'simulation'], {
    cwd: projectRoot,
    env: { ...process.env, PX4_GZ_WORLD: worldName }
  })
  attachProcLogs(up)
  up.on('exit', () => {
    const execCmd = `gz sim -r -v4 /root/.gz/sim/worlds/${worldName}.sdf`
    const exec = spawn('docker', ['exec', 'artefac_simulation', 'bash', '-lc', execCmd], {
      cwd: projectRoot,
      env: process.env
    })
    attachProcLogs(exec)
    console.log(`[${tag}] started via docker compose`)
  })
  return up
}

function createWindows() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    },
    title: 'MVP Simulation'
  })

  const url = process.env.ELECTRON_START_URL || 'file://' + path.join(__dirname, '..', 'dist', 'index.html')
  const urlMvp = url.includes('?') ? url + '&world=model' : url + '?world=model'
  win.loadURL(urlMvp)
  win.webContents.openDevTools({ mode: 'detach' })

  win.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[console:${level}] ${message} (${sourceId}:${line})`)
  })
  win.webContents.on('did-fail-load', (event, code, description, u) => {
    console.error(`did-fail-load code=${code} desc=${description} url=${u}`)
  })
  win.webContents.on('did-finish-load', () => {
    console.log('did-finish-load', url)
    win.setTitle('PX4_GZ_WORLD=model')
  })
  win.on('page-title-updated', (e) => {
    e.preventDefault()
    win.setTitle('PX4_GZ_WORLD=model')
  })

  if (!(process.platform === 'darwin' && process.env.NATIVE_GAZEBO === '1')) {
    const win2 = new BrowserWindow({
      width: 1280,
      height: 800,
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false
      },
      title: 'Harmonic Simulation'
    })
    const viewerUrl = url.includes('?') ? url.split('?')[0] : url
    const viewerWithWorld = viewerUrl + 'gazebo?world=harmonic_heightmap'
    win2.loadURL(viewerWithWorld)
    win2.webContents.openDevTools({ mode: 'detach' })
    win2.webContents.on('console-message', (event, level, message, line, sourceId) => {
      console.log(`[console:${level}] ${message} (${sourceId}:${line})`)
    })
    win2.webContents.on('did-fail-load', (event, code, description, u) => {
      console.error(`did-fail-load code=${code} desc=${description} url=${u}`)
    })
    win2.webContents.on('did-finish-load', () => {
      console.log('did-finish-load Gazebo web viewer')
      win2.setTitle('Gazebo Viewer (harmonic_heightmap)')
    })
    win2.on('page-title-updated', (e) => {
      e.preventDefault()
      win2.setTitle('PX4_GZ_WORLD=harmonic_heightmap')
    })
    gazeboHarmonic = null
  }
}

app.whenReady().then(createWindows)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindows()
})

app.on('before-quit', () => {
  if (gazeboMvp && typeof gazeboMvp.kill === 'function') {
    try { gazeboMvp.kill('SIGINT') } catch {}
  }
  if (gazeboHarmonic && typeof gazeboHarmonic.kill === 'function') {
    try { gazeboHarmonic.kill('SIGINT') } catch {}
  }
  if (websocketProc && typeof websocketProc.kill === 'function') {
    try { websocketProc.kill('SIGINT') } catch {}
  }
})