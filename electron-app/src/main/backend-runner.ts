/**
 * Backend Runner
 * 
 * Spawns Python pipeline process and handles NDJSON communication
 */

import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as readline from 'readline';

interface BackendRunnerOptions {
  backendDir: string;
  binDir: string;
  dataDir: string;
  pythonPath?: string;
}

interface PipelineConfig {
  fasta_dir: string;
  clean_fasta: boolean;
  database_type: 'IMGT' | 'Custom';
  database_v?: string;
  database_d?: string;
  database_j?: string;
  output_dir?: string;
}

interface RunCallbacks {
  onProgress: (data: { stage: string; percent: number; message: string }) => void;
  onLog: (data: { level: string; message: string }) => void;
  onResult: (data: { artifact: string; path?: string; data?: any }) => void;
  onThresholdRequest: (data: { calculated: number }) => void;
  onComplete: (data: { success: boolean; error?: string }) => void;
  onError: (error: Error) => void;
}

export class BackendRunner {
  private options: BackendRunnerOptions;
  private process: ChildProcess | null = null;
  private rl: readline.Interface | null = null;

  constructor(options: BackendRunnerOptions) {
    this.options = {
      pythonPath: 'python3',
      ...options
    };
  }

  /**
   * Run the analysis pipeline
   */
  run(config: PipelineConfig, callbacks: RunCallbacks): void {
    const pipelineScript = path.join(this.options.backendDir, 'pipeline_runner.py');
    
    // Prepare environment
    const env = {
      ...process.env,
      PATH: `${this.options.binDir}:${process.env.PATH}`,
      IGDATA: this.options.dataDir
    };

    // Spawn Python process
    this.process = spawn(this.options.pythonPath!, [pipelineScript], {
      cwd: this.options.backendDir,
      env,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    if (!this.process.stdout || !this.process.stdin) {
      callbacks.onError(new Error('Failed to create process streams'));
      return;
    }

    // Set up line reader for NDJSON output
    this.rl = readline.createInterface({
      input: this.process.stdout,
      crlfDelay: Infinity
    });

    // Handle each line of NDJSON output
    this.rl.on('line', (line: string) => {
      this.handleMessage(line, callbacks);
    });

    // Handle stderr for debugging
    this.process.stderr?.on('data', (data: Buffer) => {
      const message = data.toString();
      console.error('[Backend stderr]:', message);
      // Forward as log message
      callbacks.onLog({ level: 'debug', message: `[stderr] ${message}` });
    });

    // Handle process exit
    this.process.on('exit', (code: number | null, signal: string | null) => {
      console.log(`Backend process exited with code ${code}, signal ${signal}`);
      this.cleanup();
      
      if (code !== 0 && code !== null) {
        callbacks.onComplete({ 
          success: false, 
          error: `Process exited with code ${code}` 
        });
      }
    });

    // Handle process errors
    this.process.on('error', (error: Error) => {
      console.error('Backend process error:', error);
      callbacks.onError(error);
      this.cleanup();
    });

    // Send the configuration to start the pipeline
    const startMessage = JSON.stringify({
      action: 'run',
      config: {
        ...config,
        backend_dir: this.options.backendDir,
        bin_dir: this.options.binDir,
        data_dir: this.options.dataDir
      }
    });

    this.process.stdin.write(startMessage + '\n');
  }

  /**
   * Handle a single NDJSON message from the backend
   */
  private handleMessage(line: string, callbacks: RunCallbacks): void {
    // Skip empty lines
    if (!line || !line.trim()) {
      return;
    }
    
    try {
      const message = JSON.parse(line);
      console.log('[BackendRunner] Parsed message type:', message.type);
      
      switch (message.type) {
        case 'progress':
          callbacks.onProgress({
            stage: message.stage,
            percent: message.percent,
            message: message.message
          });
          break;
          
        case 'log':
          callbacks.onLog({
            level: message.level,
            message: message.message
          });
          break;
          
        case 'result':
          callbacks.onResult({
            artifact: message.artifact,
            path: message.path,
            data: message.data
          });
          break;
          
        case 'threshold_request':
          console.log('[BackendRunner] Received threshold_request message:', message);
          callbacks.onThresholdRequest({
            calculated: message.calculated
          });
          break;
          
        case 'complete':
          callbacks.onComplete({
            success: message.success,
            error: message.error
          });
          break;
          
        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (error) {
      // Not valid JSON, might be raw output
      console.log('[Backend raw]:', line);
    }
  }

  /**
   * Send threshold response to the backend
   */
  sendThresholdResponse(value: number): void {
    console.log('[BackendRunner] Sending threshold response:', value);
    if (this.process?.stdin && !this.process.stdin.destroyed) {
      const response = JSON.stringify({
        type: 'threshold_response',
        value
      });
      console.log('[BackendRunner] Writing to stdin:', response);
      this.process.stdin.write(response + '\n', (err) => {
        if (err) {
          console.error('[BackendRunner] Error writing to stdin:', err);
        } else {
          console.log('[BackendRunner] Successfully wrote threshold response to stdin');
        }
      });
    } else {
      console.error('[BackendRunner] ERROR: No stdin available or stdin destroyed!');
    }
  }

  /**
   * Run public clone analysis
   */
  runPublicCloneAnalysis(
    config: any,
    handlers: { onResult: Function; onComplete: Function; onError: Function }
  ): void {
    const pipelineScript = path.join(this.options.backendDir, 'pipeline_runner.py');
    
    // Prepare environment
    const env = {
      ...process.env,
      PATH: `${this.options.binDir}:${process.env.PATH}`,
      IGDATA: this.options.dataDir
    };

    // Spawn Python process
    this.process = spawn(this.options.pythonPath!, [pipelineScript], {
      cwd: this.options.backendDir,
      env,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    if (!this.process.stdout || !this.process.stdin) {
      handlers.onError('Failed to create process streams');
      return;
    }

    // Set up line reader for NDJSON output
    this.rl = readline.createInterface({
      input: this.process.stdout,
      crlfDelay: Infinity
    });

    // Handle each line of NDJSON output
    this.rl.on('line', (line: string) => {
      if (!line || !line.trim()) return;
      
      try {
        const message = JSON.parse(line);
        console.log('[PublicClones] Message type:', message.type);
        
        if (message.type === 'result' && message.artifact === 'public_clones') {
          handlers.onResult(message);
        } else if (message.type === 'complete') {
          handlers.onComplete(message);
        } else if (message.type === 'log') {
          console.log(`[PublicClones ${message.level}]:`, message.message);
        } else if (message.type === 'progress') {
          console.log(`[PublicClones Progress]: ${message.percent}% - ${message.message}`);
        }
      } catch (error) {
        console.log('[PublicClones raw]:', line);
      }
    });

    // Handle stderr
    this.process.stderr?.on('data', (data: Buffer) => {
      console.error('[PublicClones stderr]:', data.toString());
    });

    // Handle process exit
    this.process.on('exit', (code: number | null) => {
      console.log(`PublicClones process exited with code ${code}`);
      this.cleanup();
      
      if (code !== 0 && code !== null) {
        handlers.onError(`Process exited with code ${code}`);
      }
    });

    // Handle process errors
    this.process.on('error', (error: Error) => {
      console.error('PublicClones process error:', error);
      handlers.onError(error.message);
      this.cleanup();
    });

    // Send the configuration
    const startMessage = JSON.stringify({
      action: 'public_clones',
      config: {
        output_dir: config.output_dir,
        mode: config.mode || 'lenient',
        similarity_threshold: config.similarity_threshold || 0.85,
        max_mismatches: config.max_mismatches || 2,
        top_n: config.top_n || 10
      }
    });

    console.log('[PublicClones] Sending config:', startMessage);
    this.process.stdin.write(startMessage + '\n');
  }

  /**
   * Cancel the running pipeline
   */
  cancel(): void {
    if (this.process) {
      // Send cancel message
      try {
        this.process.stdin?.write(JSON.stringify({ type: 'cancel' }) + '\n');
      } catch (e) {
        // Ignore write errors during cancellation
      }
      
      // Give it a moment to clean up, then force kill
      setTimeout(() => {
        if (this.process) {
          this.process.kill('SIGTERM');
          setTimeout(() => {
            if (this.process) {
              this.process.kill('SIGKILL');
            }
          }, 2000);
        }
      }, 1000);
    }
    
    this.cleanup();
  }

  /**
   * Clean up resources
   */
  private cleanup(): void {
    if (this.rl) {
      this.rl.close();
      this.rl = null;
    }
    this.process = null;
  }

  /**
   * Check if a process is running
   */
  isRunning(): boolean {
    return this.process !== null;
  }
}

