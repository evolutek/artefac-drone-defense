const { app, BrowserWindow } = require('electron')

function createWindow() {
  const url = process.env.ELECTRON_START_URL || 'http://127.0.0.1:3000/'

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    title: 'Artefac Drone Defense - Map',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    }
  })
  win.loadURL(url)
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})