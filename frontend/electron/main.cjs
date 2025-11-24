const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let gazeboHarmonic = null
let gazeboMvp = null

function harmonicSdfPath() {
  return path.join(__dirname, '..', '..', 'simulation', 'gazebo_worlds', 'harmonic_heightmap.sdf')
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
  try {
    const gzProc = spawn('gz', ['sim', sdf], { env: process.env })
    gzProc.on('error', () => {
      const classicProc = spawn('gazebo', [sdf, '--verbose'], { env: process.env })
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
  win.loadURL(url)
  win.webContents.openDevTools({ mode: 'detach' })

  win.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[console:${level}] ${message} (${sourceId}:${line})`)
  })
  win.webContents.on('did-fail-load', (event, code, description, u) => {
    console.error(`did-fail-load code=${code} desc=${description} url=${u}`)
  })
  win.webContents.on('did-finish-load', () => {
    console.log('did-finish-load', url)
  })

  const win2 = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    },
    title: 'Harmonic Simulation'
  })
  win2.loadURL(url)
  win2.webContents.openDevTools({ mode: 'detach' })
  win2.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[console:${level}] ${message} (${sourceId}:${line})`)
  })
  win2.webContents.on('did-fail-load', (event, code, description, u) => {
    console.error(`did-fail-load code=${code} desc=${description} url=${u}`)
  })
  win2.webContents.on('did-finish-load', () => {
    console.log('did-finish-load', url)
  })

  gazeboMvp = spawnGazeboForSdf(mvpSdfPath(), 'gazebo-mvp')
  gazeboHarmonic = spawnGazeboForSdf(harmonicSdfPath(), 'gazebo-harmonic')
  if (!gazeboMvp) {
    gazeboMvp = startDockerSim('model', 'gazebo-mvp')
  }
  if (!gazeboHarmonic) {
    gazeboHarmonic = startDockerSim('harmonic_heightmap', 'gazebo-harmonic')
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
})