/**
 * IPC Handlers
 * 
 * Handles inter-process communication between main and renderer processes
 */

import { ipcMain, dialog, BrowserWindow, app } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { BackendRunner } from './backend-runner';

interface AppPaths {
  backendDir: string;
  binDir: string;
  dataDir: string;
}

export function setupIpcHandlers(
  mainWindow: BrowserWindow | null,
  backendRunner: BackendRunner,
  paths: AppPaths
): void {
  
  // Remove existing handlers to avoid duplicates
  ipcMain.removeHandler('dialog:selectDirectory');
  ipcMain.removeHandler('dialog:selectFile');
  ipcMain.removeHandler('dialog:saveFile');
  ipcMain.removeHandler('pipeline:runPublicCloneAnalysis');
  
  // Dialog: Select directory
  ipcMain.handle('dialog:selectDirectory', async (event) => {
    try {
      console.log('[IPC] dialog:selectDirectory called');
      const window = BrowserWindow.fromWebContents(event.sender) || mainWindow;
      console.log('[IPC] Window:', window ? 'found' : 'not found');
      
      if (!window) {
        console.error('[IPC] No window available for dialog');
        return null;
      }
      
      const result = await dialog.showOpenDialog(window, {
        properties: ['openDirectory'],
        title: 'Select FASTA Files Directory'
      });
      
      console.log('[IPC] Dialog result:', result);
      
      if (result.canceled || result.filePaths.length === 0) {
        return null;
      }
      
      const dirPath = result.filePaths[0];
      
      // Count FASTA files in directory
      const files = fs.readdirSync(dirPath).filter(f => 
        !f.startsWith('.') && (f.endsWith('.fasta') || f.endsWith('.fa'))
      );
      
      return {
        path: dirPath,
        fileCount: files.length,
        files: files
      };
    } catch (error) {
      console.error('[IPC] Error in dialog:selectDirectory:', error);
      return null;
    }
  });

  // Dialog: Select file
  ipcMain.handle('dialog:selectFile', async (event, options?: { filters?: { name: string, extensions: string[] }[] }) => {
    const window = BrowserWindow.fromWebContents(event.sender) || mainWindow;
    if (!window) {
      console.error('[IPC] No window available for file dialog');
      return null;
    }
    const result = await dialog.showOpenDialog(window, {
      properties: ['openFile'],
      filters: options?.filters || [
        { name: 'FASTA Files', extensions: ['fasta', 'fa'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    
    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }
    
    return result.filePaths[0];
  });

  // Dialog: Save file
  ipcMain.handle('dialog:saveFile', async (event, options?: { defaultPath?: string, filters?: { name: string, extensions: string[] }[] }) => {
    const window = BrowserWindow.fromWebContents(event.sender) || mainWindow;
    if (!window) {
      console.error('[IPC] No window available for save dialog');
      return null;
    }
    const result = await dialog.showSaveDialog(window, {
      defaultPath: options?.defaultPath,
      filters: options?.filters || [
        { name: 'TSV Files', extensions: ['tsv'] },
        { name: 'CSV Files', extensions: ['csv'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    
    if (result.canceled || !result.filePath) {
      return null;
    }
    
    return result.filePath;
  });

  // Get app paths
  ipcMain.handle('app:getPaths', async () => {
    return {
      backend: paths.backendDir,
      bin: paths.binDir,
      data: paths.dataDir,
      userData: app.getPath('userData'),
      temp: app.getPath('temp')
    };
  });

  // Get default database paths
  ipcMain.handle('app:getDefaultDatabases', async () => {
    const imgtDir = path.join(paths.dataDir, 'IMGT_Human_Database');
    
    return {
      type: 'IMGT',
      v: path.join(imgtDir, 'Human_V.fasta'),
      d: path.join(imgtDir, 'Human_D.fasta'),
      j: path.join(imgtDir, 'Human_J.fasta')
    };
  });

  // Start analysis pipeline
  ipcMain.handle('pipeline:start', async (event, config: any) => {
    return new Promise((resolve, reject) => {
      // Set up event forwarding to renderer
      const onProgress = (data: any) => {
        mainWindow?.webContents.send('pipeline:progress', data);
      };
      
      const onLog = (data: any) => {
        mainWindow?.webContents.send('pipeline:log', data);
      };
      
      const onResult = (data: any) => {
        mainWindow?.webContents.send('pipeline:result', data);
      };
      
      const onThresholdRequest = (data: any) => {
        console.log('[IPC] onThresholdRequest callback called with:', data);
        mainWindow?.webContents.send('pipeline:threshold-request', data);
        console.log('[IPC] Sent pipeline:threshold-request to renderer');
      };
      
      const onComplete = (data: any) => {
        mainWindow?.webContents.send('pipeline:complete', data);
        resolve(data);
      };
      
      const onError = (error: Error) => {
        mainWindow?.webContents.send('pipeline:error', { message: error.message });
        reject(error);
      };

      // Start the backend runner
      backendRunner.run(config, {
        onProgress,
        onLog,
        onResult,
        onThresholdRequest,
        onComplete,
        onError
      });
    });
  });

  // Send threshold response to pipeline
  ipcMain.handle('pipeline:thresholdResponse', async (_, value: number) => {
    console.log('[IPC] Received threshold response:', value);
    backendRunner.sendThresholdResponse(value);
  });

  // Cancel pipeline
  ipcMain.handle('pipeline:cancel', async () => {
    backendRunner.cancel();
  });

  // Run public clone analysis
  ipcMain.handle('pipeline:runPublicCloneAnalysis', async (event, config: any) => {
    console.log('[IPC] Running public clone analysis with config:', config);
    
    return new Promise((resolve, reject) => {
      // Set up event forwarding
      const onResult = (data: any) => {
        console.log('[IPC] Public clone result:', data);
        mainWindow?.webContents.send('pipeline:publicCloneResult', data);
      };
      
      const onComplete = (data: any) => {
        console.log('[IPC] Public clone analysis complete');
        mainWindow?.webContents.send('pipeline:publicCloneComplete', data);
        resolve(data);
      };
      
      const onError = (error: string) => {
        console.error('[IPC] Public clone analysis error:', error);
        mainWindow?.webContents.send('pipeline:publicCloneError', error);
        reject(new Error(error));
      };
      
      // Run with action: public_clones
      backendRunner.runPublicCloneAnalysis(config, { onResult, onComplete, onError });
    });
  });

  // Read file contents
  ipcMain.handle('fs:readFile', async (_, filePath: string) => {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      return { success: true, content };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  });

  // Write file contents
  ipcMain.handle('fs:writeFile', async (_, filePath: string, content: string) => {
    try {
      fs.writeFileSync(filePath, content, 'utf-8');
      return { success: true };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  });

  // Copy file
  ipcMain.handle('fs:copyFile', async (_, sourcePath: string, destPath: string) => {
    try {
      fs.copyFileSync(sourcePath, destPath);
      return { success: true };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  });

  // Check if file exists
  ipcMain.handle('fs:exists', async (_, filePath: string) => {
    return fs.existsSync(filePath);
  });

  // Read directory
  ipcMain.handle('fs:readDir', async (_, dirPath: string) => {
    try {
      const files = fs.readdirSync(dirPath);
      return { success: true, files };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  });

  // Get image as base64
  ipcMain.handle('fs:readImageBase64', async (_, imagePath: string) => {
    try {
      const buffer = fs.readFileSync(imagePath);
      const base64 = buffer.toString('base64');
      const ext = path.extname(imagePath).toLowerCase();
      const mimeType = ext === '.png' ? 'image/png' : 
                       ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' : 
                       'image/png';
      return { success: true, data: `data:${mimeType};base64,${base64}` };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  });
}

