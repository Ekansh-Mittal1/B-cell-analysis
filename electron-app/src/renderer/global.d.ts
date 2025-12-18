/**
 * Global type declarations for the renderer process
 */

interface DirectoryResult {
  path: string;
  fileCount: number;
  files: string[];
}

interface FileResult {
  success: boolean;
  content?: string;
  error?: string;
}

interface AppPaths {
  backend: string;
  bin: string;
  data: string;
  userData: string;
  temp: string;
}

interface DatabasePaths {
  type: string;
  v: string;
  d: string;
  j: string;
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

interface ProgressData {
  stage: string;
  percent: number;
  message: string;
}

interface LogData {
  level: string;
  message: string;
}

interface ResultData {
  artifact: string;
  path?: string;
  data?: any;
}

interface ThresholdRequestData {
  calculated: number;
}

interface CompleteData {
  success: boolean;
  error?: string;
}

interface ErrorData {
  message: string;
}

interface ElectronAPI {
  // Dialog operations
  selectDirectory: () => Promise<DirectoryResult | null>;
  selectFile: (options?: { filters?: { name: string; extensions: string[] }[] }) => Promise<string | null>;
  saveFile: (options?: { defaultPath?: string; filters?: { name: string; extensions: string[] }[] }) => Promise<string | null>;

  // App info
  getPaths: () => Promise<AppPaths>;
  getDefaultDatabases: () => Promise<DatabasePaths>;

  // Pipeline operations
  startPipeline: (config: PipelineConfig) => Promise<{ success: boolean; error?: string }>;
  sendThresholdResponse: (value: number) => Promise<void>;
  cancelPipeline: () => Promise<void>;

  // Public clone analysis
  runPublicCloneAnalysis: (config: {
    output_dir: string;
    mode: 'exact' | 'lenient' | 'custom';
    similarity_threshold?: number;
    max_mismatches?: number;
    top_n?: number;
  }) => Promise<{ success: boolean; error?: string }>;

  // Pipeline events
  onPipelineProgress: (callback: (data: ProgressData) => void) => () => void;
  onPipelineLog: (callback: (data: LogData) => void) => () => void;
  onPipelineResult: (callback: (data: ResultData) => void) => () => void;
  onThresholdRequest: (callback: (data: ThresholdRequestData) => void) => () => void;
  onPipelineComplete: (callback: (data: CompleteData) => void) => () => void;
  onPipelineError: (callback: (data: ErrorData) => void) => () => void;

  // Public clone analysis events
  onPublicCloneResult: (callback: (data: any) => void) => () => void;
  onPublicCloneComplete: (callback: (data: any) => void) => () => void;
  onPublicCloneError: (callback: (data: any) => void) => () => void;

  // File system operations
  readFile: (filePath: string) => Promise<FileResult>;
  writeFile: (filePath: string, content: string) => Promise<{ success: boolean; error?: string }>;
  copyFile: (sourcePath: string, destPath: string) => Promise<{ success: boolean; error?: string }>;
  fileExists: (filePath: string) => Promise<boolean>;
  readDir: (dirPath: string) => Promise<{ success: boolean; files?: string[]; error?: string }>;
  readImageBase64: (imagePath: string) => Promise<{ success: boolean; data?: string; error?: string }>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

export {};

