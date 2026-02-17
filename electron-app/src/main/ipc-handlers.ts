/**
 * IPC Handlers
 * 
 * Handles inter-process communication between main and renderer processes
 */

import { ipcMain, dialog, BrowserWindow, app } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { BackendRunner } from './backend-runner';
import { loadResultsFromDisk } from './results-loader';

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
  ipcMain.removeHandler('pipeline:stageFiles');
  ipcMain.removeHandler('pipeline:loadResults');
  ipcMain.removeHandler('pipeline:runPublicCloneAnalysis');
  
  // Dialog: Select directory
  // Detects folder structure:
  //   Flat:    selected_dir/*.fasta  → files returned directly
  //   2-level: selected_dir/subdir/*.fasta → each subdir is a timepoint
  // No staging occurs here – staging happens at pipeline start.
  ipcMain.handle('dialog:selectDirectory', async (event) => {
    try {
      console.log('[IPC] dialog:selectDirectory called');
      const window = BrowserWindow.fromWebContents(event.sender) || mainWindow;
      
      if (!window) {
        console.error('[IPC] No window available for dialog');
        return null;
      }
      
      const result = await dialog.showOpenDialog(window, {
        properties: ['openDirectory'],
        title: 'Select FASTA Files Directory'
      });
      
      if (result.canceled || result.filePaths.length === 0) {
        return null;
      }
      
      const dirPath = result.filePaths[0];
      const isFasta = (f: string) => !f.startsWith('.') && (f.endsWith('.fasta') || f.endsWith('.fa'));
      const isDir = (p: string) => { try { return fs.statSync(p).isDirectory(); } catch { return false; } };
      
      // 1. Check for FASTA files directly in the selected directory
      const topFiles = fs.readdirSync(dirPath).filter(isFasta);
      
      if (topFiles.length > 0) {
        // Flat structure — FASTA files directly in directory (no timepoint subfolders)
        return {
          path: dirPath,
          fileCount: topFiles.length,
          files: topFiles
        };
      }
      
      // 2. No FASTA files at top level — scan subdirectories as timepoints
      const topEntries = fs.readdirSync(dirPath)
        .filter(e => !e.startsWith('.') && isDir(path.join(dirPath, e)))
        .sort();
      
      if (topEntries.length === 0) {
        return { path: dirPath, fileCount: 0, files: [] };
      }
      
      // Each subdirectory with FASTA files becomes a timepoint
      interface DetectedTP { label: string; dir: string; files: string[]; }
      const detectedTimepoints: DetectedTP[] = [];
      let totalFiles = 0;
      
      for (const entry of topEntries) {
        const subPath = path.join(dirPath, entry);
        const subFasta = fs.readdirSync(subPath).filter(isFasta);
        if (subFasta.length > 0) {
          detectedTimepoints.push({
            label: entry,
            dir: subPath,
            files: subFasta
          });
          totalFiles += subFasta.length;
        }
      }
      
      if (detectedTimepoints.length === 0) {
        return { path: dirPath, fileCount: 0, files: [] };
      }
      
      console.log(`[IPC] Detected ${detectedTimepoints.length} timepoint subfolders with ${totalFiles} total FASTA files`);
      
      return {
        path: dirPath,
        fileCount: totalFiles,
        files: [],
        detectedTimepoints
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

  // Get bundled CoV-AbDab database path
  ipcMain.handle('app:getCovidDatabase', async () => {
    const covidDbPath = path.join(paths.dataDir, 'internal_data', 'CoV-AbDab_080224.csv');
    if (fs.existsSync(covidDbPath)) {
      return covidDbPath;
    }
    return null;
  });

  // Stage timepoint files into a flat directory for the pipeline.
  // Called right before pipeline:start. Returns the staging dir path.
  ipcMain.handle('pipeline:stageFiles', async (_event, timepoints: { label: string; files: string[] }[], studyName: string) => {
    try {
      const baseOuts = path.join(paths.backendDir, '..', 'geneGUI', 'outs');
      if (!fs.existsSync(baseOuts)) fs.mkdirSync(baseOuts, { recursive: true });

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const uniqueId = Math.random().toString(36).slice(2, 6);
      const stagingDir = path.join(baseOuts, `staging_${timestamp}_${uniqueId}`);
      fs.mkdirSync(stagingDir, { recursive: true });

      const timepointMapping: Record<string, { timepoint: string; originalFile: string }> = {};
      const usedNames = new Set<string>();

      for (const tp of timepoints) {
        for (const filePath of tp.files) {
          const originalName = path.basename(filePath);
          
          // Always prefix with timepoint label for consistency
          let destName = `${tp.label}_${originalName}`;
          
          // Handle collision if same filename appears multiple times in same timepoint
          let counter = 2;
          while (usedNames.has(destName)) {
            destName = `${tp.label}_${counter}_${originalName}`;
            counter++;
          }
          usedNames.add(destName);

          const destFile = path.join(stagingDir, destName);
          if (fs.existsSync(filePath)) {
            fs.copyFileSync(filePath, destFile);
            timepointMapping[destName] = {
              timepoint: tp.label,
              originalFile: originalName
            };
          }
        }
      }

      // Save timepoint_mapping.json in staging dir (will be moved to output dir later)
      const mappingPath = path.join(stagingDir, 'timepoint_mapping.json');
      fs.writeFileSync(mappingPath, JSON.stringify(timepointMapping, null, 2), 'utf-8');

      // Save study_name.txt for reference
      fs.writeFileSync(path.join(stagingDir, 'study_name.txt'), studyName, 'utf-8');

      console.log(`[IPC] Staged ${Object.keys(timepointMapping).length} files from ${timepoints.length} timepoints into ${stagingDir}`);

      return { success: true, stagingDir, timepointMapping };
    } catch (error: any) {
      console.error('[IPC] Failed to stage files:', error);
      return { success: false, error: error.message };
    }
  });

  // Start analysis pipeline
  ipcMain.handle('pipeline:start', async (event, config: any) => {
    return new Promise((resolve, reject) => {
      // Create a unique output directory per run so sessions don't overwrite each other
      const baseOuts = path.join(paths.backendDir, '..', 'geneGUI', 'outs');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const uniqueId = Math.random().toString(36).slice(2, 6);
      const outputDir = path.join(baseOuts, `run_${timestamp}_${uniqueId}`);
      const configWithOutput = { ...config, output_dir: outputDir };
      console.log('[IPC] Pipeline output_dir:', outputDir);

      // Copy timepoint_mapping.json and study_name.txt from staging dir to output dir if present
      const fastaDir = config.fasta_dir;
      if (fastaDir) {
        if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
        const srcMapping = path.join(fastaDir, 'timepoint_mapping.json');
        if (fs.existsSync(srcMapping)) {
          fs.copyFileSync(srcMapping, path.join(outputDir, 'timepoint_mapping.json'));
          console.log('[IPC] Copied timepoint_mapping.json to output dir');
        }
        const srcStudy = path.join(fastaDir, 'study_name.txt');
        if (fs.existsSync(srcStudy)) {
          fs.copyFileSync(srcStudy, path.join(outputDir, 'study_name.txt'));
        }
      }

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
        // After pipeline completes, emit timepoint_mapping if it exists
        const tpMappingPath = path.join(outputDir, 'timepoint_mapping.json');
        if (fs.existsSync(tpMappingPath)) {
          try {
            const tpContent = fs.readFileSync(tpMappingPath, 'utf-8');
            const tpMapping = JSON.parse(tpContent);
            console.log('[IPC] Emitting timepoint_mapping artifact with', Object.keys(tpMapping).length, 'entries');
            mainWindow?.webContents.send('pipeline:result', {
              artifact: 'timepoint_mapping',
              data: tpMapping
            });
          } catch (e) {
            console.warn('[IPC] Failed to emit timepoint_mapping:', e);
          }
        }
        
        mainWindow?.webContents.send('pipeline:complete', data);
        resolve(data);
      };
      
      const onError = (error: Error) => {
        mainWindow?.webContents.send('pipeline:error', { message: error.message });
        reject(error);
      };

      // Start the backend runner
      backendRunner.run(configWithOutput, {
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
  ipcMain.handle('pipeline:thresholdResponse', async (_, value: number | Record<string, number>) => {
    console.log('[IPC] Received threshold response:', value);
    backendRunner.sendThresholdResponse(value);
  });

  // Cancel pipeline
  ipcMain.handle('pipeline:cancel', async () => {
    backendRunner.cancel();
  });

  // Load results from disk (restore after sleep/minimize)
  // Uses pure Node/TS loader - no Python subprocess, guarantees correct directory
  // Optional: save previous session's study design before loading (outputDir + design)
  ipcMain.handle('pipeline:loadResults', async (event, outputDir: string, savePrevious?: { outputDir: string; design: any }) => {
    const webContents = event.sender;
    const resolvedDir = path.resolve(outputDir);

    // Save previous session's study design in main process (guarantees correct path)
    if (savePrevious?.outputDir && savePrevious?.design) {
      try {
        const prevDir = path.resolve(savePrevious.outputDir);
        const designPath = path.join(prevDir, 'study_design.json');
        fs.writeFileSync(designPath, JSON.stringify(savePrevious.design, null, 2), 'utf-8');
        console.log('[IPC] Saved study design to', designPath);
      } catch (e) {
        console.warn('[IPC] Failed to save previous study design:', e);
      }
    }

    console.log('[IPC] Load results for:', resolvedDir);

    return new Promise((resolve, reject) => {
      const send = (channel: string, data: any) => {
        try { webContents.send(channel, data); } catch (e) { console.warn('[IPC] Failed to send', channel, e); }
      };
      const onProgress = (data: any) => send('pipeline:progress', data);
      const onLog = (data: any) => send('pipeline:log', data);
      const onResult = (data: any) => send('pipeline:result', data);
      const onComplete = (data: any) => {
        send('pipeline:complete', data);
        resolve(data);
      };

      try {
        loadResultsFromDisk(resolvedDir, {
          onProgress,
          onLog,
          onResult,
          onComplete
        });
      } catch (err: any) {
        console.error('[IPC] Load results error:', err);
        send('pipeline:error', { message: err?.message ?? String(err) });
        send('pipeline:complete', { success: false, error: err?.message ?? String(err) });
        resolve({ success: false, error: err?.message ?? String(err) });
      }
    });
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
      console.log('[IPC] Reading file:', filePath);
      const data = fs.readFileSync(filePath, 'utf-8');
      console.log('[IPC] Successfully read file, length:', data.length);
      return { success: true, data };
    } catch (error: any) {
      console.error('[IPC] Failed to read file:', error.message);
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

