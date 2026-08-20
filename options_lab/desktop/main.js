const { app, BrowserWindow, Tray, Menu, ipcMain, dialog, session, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, exec } = require('child_process');
const http = require('http');

// Set unique userData path to completely bypass Windows access violations or sharing locks
try {
  const uniqueSessionDir = path.join(app.getPath('temp'), 'options-lab-desktop-' + Date.now());
  if (!fs.existsSync(uniqueSessionDir)) {
    fs.mkdirSync(uniqueSessionDir, { recursive: true });
  }
  app.setPath('userData', uniqueSessionDir);
} catch (err) {
  console.error('[OptionsLab Desktop] Failed to set unique userData path:', err);
}

// Disable HTTP Cache completely to prevent loading stale JS/CSS compiled assets
app.commandLine.appendSwitch('disable-http-cache');

let mainWindow = null;
let tray = null;
let backendProcess = null;
let isQuitting = false;

const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`;

// ── 1. Backend Process Management & Health Check ────────────────────────────
function isBackendReady() {
  return new Promise((resolve) => {
    http.get(`${BACKEND_URL}/health`, (res) => {
      resolve(res.statusCode === 200);
    }).on('error', () => {
      resolve(false);
    });
  });
}

async function waitForBackend(maxAttempts = 30) {
  for (let i = 0; i < maxAttempts; i++) {
    const ready = await isBackendReady();
    if (ready) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function startBackend() {
  const rootDir = path.resolve(__dirname, '..', '..');
  console.log(`[OptionsLab Desktop] Starting FastAPI backend from ${rootDir}...`);

  // Detect local Windows virtual environment python executable
  const venvPythonPath = path.join(rootDir, 'venv_win', 'Scripts', 'python.exe');
  const pythonCmd = fs.existsSync(venvPythonPath) ? venvPythonPath : 'python';
  console.log(`[OptionsLab Desktop] Using Python interpreter: ${pythonCmd}`);

  backendProcess = spawn(pythonCmd, ['-m', 'uvicorn', 'options_lab.api.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], {
    cwd: rootDir,
    shell: true,
    stdio: 'pipe'
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend]: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend ERR]: ${data}`);
  });

  backendProcess.on('error', (err) => {
    console.error(`[Backend Spawn Error]: ${err}`);
    dialog.showErrorBox(
      'FastAPI Backend Start Failed',
      `Failed to launch the backend process using path: ${pythonCmd}\nError: ${err.message}`
    );
  });

  backendProcess.on('close', (code) => {
    console.log(`[Backend Process Closed with code ${code}]`);
    if (code !== 0 && code !== null) {
      dialog.showErrorBox(
        'FastAPI Backend Exited',
        `The backend process exited unexpectedly with code ${code}. Please verify uvicorn dependencies in your virtual environment.`
      );
    }
  });
}

function killBackend() {
  if (backendProcess) {
    console.log('[OptionsLab Desktop] Shutting down backend process...');
    if (process.platform === 'win32') {
      exec(`taskkill /pid ${backendProcess.pid} /T /F`, (err) => {
        if (err) console.error('Failed to kill backend process tree:', err);
      });
    } else {
      backendProcess.kill('SIGTERM');
    }
    backendProcess = null;
  }
}

// ── 2. Create Native Desktop Window ─────────────────────────────────────────
async function createWindow() {
  // Clear any cached HTTP/DOM states
  try {
    if (session.defaultSession) {
      await session.defaultSession.clearCache();
      await session.defaultSession.clearStorageData();

      // Configure hardened Content Security Policy (No unsafe-eval)
      session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
        callback({
          responseHeaders: {
            ...details.responseHeaders,
            'Content-Security-Policy': [
              "default-src 'self' 'unsafe-inline' http://127.0.0.1:* http://localhost:* https: data: blob:; " +
              "script-src 'self' 'unsafe-inline' http://127.0.0.1:* http://localhost:* https:; " +
              "style-src 'self' 'unsafe-inline' https: fonts.googleapis.com; " +
              "font-src 'self' data: https: fonts.gstatic.com; " +
              "img-src 'self' data: blob: https:; " +
              "connect-src 'self' http://127.0.0.1:* http://localhost:* https: ws: wss:; " +
              "frame-src 'self' https:;"
            ]
          }
        });
      });
    }
  } catch (e) {}

  mainWindow = new BrowserWindow({
    width: 1360,
    height: 880,
    minWidth: 1024,
    minHeight: 700,
    title: 'OptionsLab — Institutional Broker Gateway',
    backgroundColor: '#F3F3F9',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      cache: false
    }
  });


  const isDev = process.argv.includes('--dev');
  const isHidden = process.argv.includes('--hidden');

  // Check if backend is already running or start it
  const alreadyRunning = await isBackendReady();
  if (!alreadyRunning) {
    startBackend();
    await waitForBackend();
  }

  // Check if frontend dev server is running on 3000
  let targetUrl = `${BACKEND_URL}/`;
  try {
    const isFrontendUp = await new Promise((resolve) => {
      http.get(FRONTEND_URL, (res) => resolve(res.statusCode >= 200 && res.statusCode < 400)).on('error', () => resolve(false));
    });
    if (isFrontendUp || isDev) {
      targetUrl = FRONTEND_URL;
    }
  } catch (e) {
    targetUrl = `${BACKEND_URL}/`;
  }

  console.log(`[OptionsLab Desktop] Loading application at ${targetUrl}...`);

  mainWindow.loadURL(targetUrl).catch(() => {
    // If static mount or dev server is booting, retry
    setTimeout(() => mainWindow.loadURL(targetUrl), 2000);
  });

  // Open external links (Saxo OAuth, etc.) in system default browser (Chrome)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http') && !url.includes('127.0.0.1') && !url.includes('localhost')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  // Also intercept navigation to external sites
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith('http') && !url.includes('127.0.0.1') && !url.includes('localhost')) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  // Stream all renderer console logs and errors directly to terminal & logs
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    const levelLabels = ['LOG', 'INFO', 'WARN', 'ERROR'];
    const label = levelLabels[level] || 'LOG';
    const cleanSource = sourceId ? path.basename(sourceId) : 'renderer';
    const logLine = `[Frontend ${label}] (${cleanSource}:${line}) ${message}`;
    
    if (level === 3) {
      console.error(`\x1b[31m${logLine}\x1b[0m`);
    } else if (level === 2) {
      console.warn(`\x1b[33m${logLine}\x1b[0m`);
    } else {
      console.log(logLine);
    }
  });

  // Enable F12 and Ctrl+Shift+I for DevTools inspection
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i')) {
      mainWindow.webContents.toggleDevTools();
      event.preventDefault();
    }
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.webContents.reloadIgnoringCache();
    if (!isHidden) {
      mainWindow.show();
      mainWindow.focus();
    }
  });


  mainWindow.on('close', (event) => {

    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      if (tray) {
        tray.displayBalloon({
          title: 'OptionsLab Minimized',
          content: 'OptionsLab is continuing in the background. Click the tray icon to restore.'
        });
      }
    }
  });
}

// ── 3. System Tray Setup ───────────────────────────────────────────────────
function createTray() {
  // Use a default icon or generate clean tray menu
  tray = new Tray(path.join(__dirname, 'tray_icon.png'));
  tray.setToolTip('OptionsLab Trading Gateway');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open OptionsLab',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: 'Broker Health Status',
      click: async () => {
        const ready = await isBackendReady();
        dialog.showMessageBox({
          type: 'info',
          title: 'Broker Status',
          message: ready ? 'FastAPI Broker Gateway is connected and active on port 8000.' : 'FastAPI Broker Gateway is offline.'
        });
      }
    },
    { type: 'separator' },
    {
      label: 'Auto-Start with Windows',
      type: 'checkbox',
      checked: app.getLoginItemSettings().openAtLogin,
      click: (item) => {
        app.setLoginItemSettings({
          openAtLogin: item.checked,
          args: ['--hidden']
        });
      }
    },
    { type: 'separator' },
    {
      label: 'Quit OptionsLab',
      click: () => {
        isQuitting = true;
        killBackend();
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) mainWindow.hide();
      else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

const gotTheLock = true;

if (!gotTheLock) {
  app.quit();
} else {
  // Setup second instance callback if lock is acquired (optional)
  try {
    app.requestSingleInstanceLock();
  } catch (e) {}
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.setAlwaysOnTop(true);
      mainWindow.focus();
      mainWindow.setAlwaysOnTop(false);
    }
  });

  app.whenReady().then(() => {

    // Enable auto-launch by default on Windows
    app.setLoginItemSettings({
      openAtLogin: true,
      path: process.execPath,
      args: ['--hidden']
    });

    createTray();
    createWindow();
  });

  app.on('before-quit', () => {
    isQuitting = true;
    killBackend();
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      // Keep running in tray on Windows unless user explicitly chooses Quit
    }
  });
}
