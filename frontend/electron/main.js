const { app, BrowserWindow } = require('electron')

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  const url = process.env.ELECTRON_START_URL || 'file://' + require('path').join(__dirname, '..', 'dist', 'index.html')
  win.loadURL(url)

  win.webContents.openDevTools({ mode: 'detach' })

  win.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[console:${level}] ${message} (${sourceId}:${line})`)
  })
  win.webContents.on('did-fail-load', (event, code, description, url) => {
    console.error(`did-fail-load code=${code} desc=${description} url=${url}`)
  })
  win.webContents.on('did-finish-load', () => {
    console.log('did-finish-load', url)
  })
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})