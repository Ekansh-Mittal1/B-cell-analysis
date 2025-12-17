/**
 * Electron Main Process
 * 
 * Handles window management, app lifecycle, and IPC communication
 */

import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { setupIpcHandlers } from './ipc-handlers';
import { BackendRunner } from './backend-runner';

// Keep a global reference of the window object to prevent garbage collection
let mainWindow: BrowserWindow | null = null;
let backendRunner: BackendRunner | null = null;

// Determine if we're in development mode
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function getResourcesPath(): string {
  if (isDev) {
    return path.join(__dirname, '..', '..');
  }
  return process.resourcesPath;
}

function getBackendPath(): string {
  const resourcesPath = getResourcesPath();
  if (isDev) {
    return path.join(resourcesPath, '..', 'backend');
  }
  return path.join(resourcesPath, 'backend');
}

function getBinPath(): string {
  const resourcesPath = getResourcesPath();
  if (isDev) {
    return path.join(resourcesPath, '..', 'geneGUI', 'bin');
  }
  return path.join(resourcesPath, 'bin');
}

function getDataPath(): string {
  const resourcesPath = getResourcesPath();
  if (isDev) {
    return path.join(resourcesPath, '..', 'geneGUI', 'data');
  }
  return path.join(resourcesPath, 'data');
}

function createWindow(): void {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    backgroundColor: '#ffffff',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 20, y: 20 },
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: (() => {
        const preloadPath = path.resolve(__dirname, '..', 'preload', 'index.js');
        if (!fs.existsSync(preloadPath)) {
          // Fallback for dev mode
          const fallback = path.join(process.cwd(), 'dist', 'preload', 'index.js');
          if (fs.existsSync(fallback)) {
            console.log('[Main] Using fallback preload path:', fallback);
            return fallback;
          }
        }
        return preloadPath;
      })(),
      sandbox: false
    },
    show: false // Don't show until ready
  });

  // Log preload path for debugging
  const preloadPath = path.resolve(__dirname, '..', 'preload', 'index.js');
  console.log('[Main] Preload path:', preloadPath);
  console.log('[Main] Preload exists:', fs.existsSync(preloadPath));
  console.log('[Main] __dirname:', __dirname);
  console.log('[Main] isDev:', isDev);
  
  if (!fs.existsSync(preloadPath)) {
    console.error('[Main] ERROR: Preload script not found at:', preloadPath);
    // Try alternative paths
    const altPath1 = path.join(process.cwd(), 'dist', 'preload', 'index.js');
    const altPath2 = path.join(__dirname, 'preload', 'index.js');
    console.log('[Main] Trying alternative path 1:', altPath1, 'exists:', fs.existsSync(altPath1));
    console.log('[Main] Trying alternative path 2:', altPath2, 'exists:', fs.existsSync(altPath2));
  }
  
  // Load the app
  if (isDev) {
    // In development, load from Vite dev server
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // In production, load from built files
    mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  }
  
  // Debug: Check if preload script loaded
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('[Main] Window finished loading');
    // Wait a moment for preload to finish
    setTimeout(() => {
      mainWindow?.webContents.executeJavaScript(`
        console.log('[Renderer] window.electronAPI:', window.electronAPI);
        console.log('[Renderer] typeof window.electronAPI:', typeof window.electronAPI);
        console.log('[Renderer] window keys:', Object.keys(window));
        if (window.electronAPI) {
          console.log('[Renderer] electronAPI methods:', Object.keys(window.electronAPI));
        } else {
          console.error('[Renderer] ERROR: electronAPI is not available!');
        }
      `).catch(err => console.error('[Main] Error executing debug script:', err));
    }, 500);
  });
  
  // Check for preload script errors - this is the key event!
  mainWindow.webContents.on('preload-error', (event, preloadPath, error) => {
    console.error('[Main] ===== PRELOAD SCRIPT ERROR =====');
    console.error('[Main] Preload path:', preloadPath);
    console.error('[Main] Error:', error);
    console.error('[Main] =================================');
  });
  
  // Listen for all console messages
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    const source = sourceId ? String(sourceId) : 'unknown';
    if (source.includes('preload') || message.includes('[Preload]')) {
      console.log(`[Preload ${level}]:`, message);
    }
  });
  
  // Also log when the preload script starts
  mainWindow.webContents.on('did-attach-webview', () => {
    console.log('[Main] Webview attached');
  });

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
    // Kill any running backend process
    if (backendRunner) {
      backendRunner.cancel();
      backendRunner = null;
    }
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// Initialize the backend runner
function initBackendRunner(): void {
  const backendPath = getBackendPath();
  const binPath = getBinPath();
  const dataPath = getDataPath();
  
  backendRunner = new BackendRunner({
    backendDir: backendPath,
    binDir: binPath,
    dataDir: dataPath,
    pythonPath: 'python3' // Will be configurable later for bundled env
  });
}

// App lifecycle
app.whenReady().then(() => {
  initBackendRunner();
  
  // Create window first
  createWindow();
  
  // Setup IPC handlers with the created window
  setupIpcHandlers(mainWindow, backendRunner!, {
    backendDir: getBackendPath(),
    binDir: getBinPath(),
    dataDir: getDataPath()
  });

  app.on('activate', () => {
    // On macOS, re-create window when dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Clean up before quitting
app.on('before-quit', () => {
  if (backendRunner) {
    backendRunner.cancel();
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
});

export { mainWindow, backendRunner };

