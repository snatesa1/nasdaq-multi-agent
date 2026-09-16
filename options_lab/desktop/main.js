const { app, BrowserWindow, Tray, Menu, ipcMain, dialog, session, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, exec } = require('child_process');
const http = require('http');

// ── 0. Hardware Acceleration & Windows Cold-Boot Crash Prevention ────────────
// Disable hardware acceleration to eliminate Chromium GPU rasterization hangs/black screens on reboot
app.disableHardwareAcceleration();
app.commandLine.appendSwitch('disable-gpu');
app.commandLine.appendSwitch('disable-gpu-compositing');
app.commandLine.appendSwitch('disable-software-rasterizer');
app.commandLine.appendSwitch('disable-http-cache');

// Set stable, persistent userData path in AppData to retain cookies/tokens and avoid random %TEMP% bloat
try {
  const appDataDir = app.getPath('appData');
  const persistentDataDir = path.join(appDataDir, 'OptionsLabDesktop');
  if (!fs.existsSync(persistentDataDir)) {
    fs.mkdirSync(persistentDataDir, { recursive: true });
  }
  app.setPath('userData', persistentDataDir);
} catch (err) {
  console.error('[OptionsLab Desktop] Failed to set persistent userData path:', err);
}

let mainWindow = null;
let tray = null;
let backendProcess = null;
let frontendProcess = null;
let isQuitting = false;

const BACKEND_HOST = process.env.OPTIONS_LAB_BACKEND_HOST || '127.0.0.1';
const BACKEND_PORT = Number(process.env.OPTIONS_LAB_BACKEND_PORT || 8000);
const FRONTEND_PORT = Number(process.env.OPTIONS_LAB_FRONTEND_PORT || 3000);
const BACKEND_URL = process.env.OPTIONS_LAB_BACKEND_URL || `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const FRONTEND_URL = process.env.OPTIONS_LAB_FRONTEND_URL || `http://localhost:${FRONTEND_PORT}`;

// ── 1. Backend & Frontend Process Management & Health Checks ────────────────
function isBackendReady() {
  return new Promise((resolve) => {
    const req = http.get(`${BACKEND_URL}/api/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => {
      resolve(false);
    });
    req.setTimeout(1500, () => {
      req.abort();
      resolve(false);
    });
  });
}

async function waitForBackend(maxAttempts = 60, onProgress = null) {
  console.log(`[OptionsLab Desktop] Waiting for Python backend on ${BACKEND_URL} (max ${maxAttempts}s)...`);
  for (let i = 0; i < maxAttempts; i++) {
    const ready = await isBackendReady();
    if (ready) {
      console.log(`[OptionsLab Desktop] Backend confirmed healthy on attempt ${i + 1}!`);
      return true;
    }
    if (onProgress) {
      onProgress(i + 1, maxAttempts);
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  console.warn(`[OptionsLab Desktop] Backend failed to respond after ${maxAttempts}s.`);
  return false;
}

function startBackend() {
  const rootDir = path.resolve(__dirname, '..', '..');
  console.log(`[OptionsLab Desktop] Starting FastAPI backend from ${rootDir}...`);

  // Detect local Windows virtual environment python executable
  const venvPythonPath = path.join(rootDir, 'venv_win', 'Scripts', 'python.exe');
  const pythonCmd = fs.existsSync(venvPythonPath) ? venvPythonPath : 'python';
  console.log(`[OptionsLab Desktop] Using Python interpreter: ${pythonCmd}`);

  backendProcess = spawn(pythonCmd, ['-m', 'uvicorn', 'options_lab.api.main:app', '--host', '0.0.0.0', '--port', String(BACKEND_PORT), '--reload', '--reload-dir', 'options_lab'], {
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
  });
}

function killBackend() {
  if (backendProcess) {
    console.log('[OptionsLab Desktop] Shutting down backend process...');
    if (process.platform === 'win32') {
      exec(`taskkill /pid ${backendProcess.pid} /T /F`, () => {});
    } else {
      backendProcess.kill('SIGTERM');
    }
    backendProcess = null;
  }
}

function isFrontendReady() {
  return new Promise((resolve) => {
    http.get(FRONTEND_URL, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    }).on('error', () => {
      resolve(false);
    });
  });
}

async function waitForFrontend(maxAttempts = 40) {
  for (let i = 0; i < maxAttempts; i++) {
    const ready = await isFrontendReady();
    if (ready) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function startFrontend() {
  const frontendDir = path.resolve(__dirname, '..', 'frontend');
  console.log(`[OptionsLab Desktop] Starting Next.js frontend dev server from ${frontendDir}...`);

  frontendProcess = spawn('npm.cmd', ['run', 'dev'], {
    cwd: frontendDir,
    shell: true,
    stdio: 'pipe'
  });

  frontendProcess.stdout.on('data', (data) => {
    console.log(`[Frontend]: ${data}`);
  });

  frontendProcess.stderr.on('data', (data) => {
    console.error(`[Frontend ERR]: ${data}`);
  });
}

function killFrontend() {
  if (frontendProcess) {
    console.log('[OptionsLab Desktop] Shutting down frontend process...');
    if (process.platform === 'win32') {
      exec(`taskkill /pid ${frontendProcess.pid} /T /F`, () => {});
    } else {
      frontendProcess.kill('SIGTERM');
    }
    frontendProcess = null;
  }
}

function killAllProcesses() {
  killBackend();
  killFrontend();
}

// ── 2. Create Native Desktop Window ─────────────────────────────────────────
async function createWindow() {
  try {
    if (session.defaultSession) {
      await session.defaultSession.clearCache();

      // Hardened Content Security Policy
      session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
        callback({
          responseHeaders: {
            ...details.responseHeaders,
            'Content-Security-Policy': [
              "default-src 'self' 'unsafe-inline' 'unsafe-eval' http://127.0.0.1:* http://localhost:* https: data: blob:; " +
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://127.0.0.1:* http://localhost:* https:; " +
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
    backgroundColor: '#0f172a',
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

  // Immediately show window with the splash screen so the user never sees a black/blank viewport
  const splashPath = path.join(__dirname, 'splash.html');
  mainWindow.loadFile(splashPath);
  if (!isHidden) {
    mainWindow.show();
    mainWindow.focus();
  }

  // 1. Ensure Backend is active on port 8000
  const backendUp = await isBackendReady();
  if (!backendUp) {
    startBackend();
    const ready = await waitForBackend(60, (attempt, max) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.executeJavaScript(`
          const el = document.getElementById('statusText');
          if (el) el.innerText = 'Starting Python quantitative engines & broker gateway... (${attempt}/${max}s)';
        `).catch(() => {});
      }
    });

    if (!ready) {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.loadFile(splashPath, {
          query: {
            error: `Failed to connect to OptionsLab backend on ${BACKEND_URL} within 60 seconds. Please check if Python dependencies are installed or run .\\restart_backend.ps1.`
          }
        });
      }
      return;
    }
  }

  // 2. Resolve target URL (Dev server if --dev, otherwise fast static mount via FastAPI)
  let targetUrl = `${BACKEND_URL}/`;
  if (isDev) {
    const frontendUp = await isFrontendReady();
    if (!frontendUp) {
      startFrontend();
      await waitForFrontend(40);
    }
    const isNextReady = await isFrontendReady();
    if (isNextReady) {
      targetUrl = FRONTEND_URL;
    }
  }

  console.log(`[OptionsLab Desktop] Backend is healthy! Loading application at ${targetUrl}...`);

  // Load target URL with automatic retry and did-fail-load recovery
  mainWindow.loadURL(targetUrl).catch((err) => {
    console.warn(`[OptionsLab Desktop] Initial loadURL caught error: ${err}. Retrying in 2s...`);
    setTimeout(() => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.loadURL(targetUrl);
      }
    }, 2000);
  });

  // Handle load failure gracefully without leaving user on a dead black screen
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.error(`[OptionsLab Desktop] did-fail-load: code ${errorCode} (${errorDescription}) on ${validatedURL}`);
    if (validatedURL && validatedURL.includes(String(BACKEND_PORT))) {
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.loadFile(splashPath, {
            query: {
              error: `Unable to render ${validatedURL} (${errorDescription}). Backend may be restarting. Click Retry below.`
            }
          });
        }
      }, 1500);
    }
  });

  // Recover from renderer process crash
  mainWindow.webContents.on('render-process-gone', (event, details) => {
    console.error(`[OptionsLab Desktop] Renderer process crashed:`, details);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.reload();
    }
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http') && !url.includes('127.0.0.1') && !url.includes('localhost')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith('http') && !url.includes('127.0.0.1') && !url.includes('localhost')) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  // Console message streaming
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

  // Automated Saxo OAuth 2.0 Interceptor (Zero Copy-Paste)
  ipcMain.handle('open-saxo-oauth', async (event, authUrl) => {
    return new Promise((resolve, reject) => {
      const authWin = new BrowserWindow({
        width: 600,
        height: 750,
        title: 'Saxo Bank MFA Authorization',
        parent: mainWindow,
        modal: true,
        webPreferences: { nodeIntegration: false, contextIsolation: true }
      });

      let handled = false;
      const handleRedirect = async (targetUrl) => {
        if (handled) return;
        if (targetUrl.includes('code=') || targetUrl.includes('Akpegis-Agent.com.sg') || targetUrl.includes('callback')) {
          try {
            const urlObj = new URL(targetUrl);
            const code = urlObj.searchParams.get('code');
            if (code) {
              handled = true;
              console.log('[Electron OAuth] Captured Saxo code automatically:', code);
              const postData = JSON.stringify({ code: code });
              const req = http.request({
                hostname: BACKEND_HOST,
                port: BACKEND_PORT,
                path: '/api/broker/oauth/set-token',
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Content-Length': Buffer.byteLength(postData)
                }
              }, (res) => {
                authWin.close();
                if (mainWindow) {
                  mainWindow.webContents.send('saxo-auth-success');
                }
                resolve({ success: true, code });
              });
              req.on('error', (err) => {
                console.error('[Electron OAuth] Error posting token:', err);
                authWin.close();
                reject(err);
              });
              req.write(postData);
              req.end();
            }
          } catch (e) {
            console.error('[Electron OAuth] Parse error:', e);
          }
        }
      };

      authWin.webContents.on('will-navigate', (event, url) => handleRedirect(url));
      authWin.webContents.on('will-redirect', (event, url) => handleRedirect(url));
      authWin.webContents.on('did-navigate', (event, url) => handleRedirect(url));

      authWin.loadURL(authUrl);
    });
  });

  // F12 and Ctrl+Shift+I DevTools
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i')) {
      mainWindow.webContents.toggleDevTools();
      event.preventDefault();
    }
  });

  mainWindow.once('ready-to-show', () => {
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
      label: 'Quit OptionsLab',
      click: () => {
        isQuitting = true;
        killAllProcesses();
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
  createTray();
  createWindow();
});

app.on('before-quit', () => {
  isQuitting = true;
  killAllProcesses();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Keep running in tray on Windows
  }
});
