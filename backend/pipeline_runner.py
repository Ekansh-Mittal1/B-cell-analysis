#!/usr/bin/env python3
"""
Pipeline Runner - NDJSON interface for B-Cell Repertoire Analysis

This module provides a CLI interface that communicates via stdin/stdout using
newline-delimited JSON (NDJSON) for seamless integration with Electron.

Message Types (stdout):
    - progress: {"type": "progress", "stage": "...", "percent": 0-100, "message": "..."}
    - log: {"type": "log", "level": "info|warn|error", "message": "..."}
    - threshold_request: {"type": "threshold_request", "calculated": float}
    - result: {"type": "result", "artifact": "...", "path": "...", "data": {...}}
    - complete: {"type": "complete", "success": bool, "error": "..."}

Input (stdin):
    - config: {"action": "run", "config": {...}}
    - threshold_response: {"type": "threshold_response", "value": float}
    - cancel: {"type": "cancel"}
"""

import sys
import os
import json
import glob
import io
import traceback
from typing import Optional, Dict, Any, List

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import existing utilities
from utils import clean as cl
from utils import blast
from utils import clonality as clone
from utils.clonalityFunctions import make_db, define_clonality, create_germline, findDist

# Try to import DL clustering (optional)
try:
    from utils import dl_clustering
    DL_CLUSTERING_AVAILABLE = True
except ImportError:
    DL_CLUSTERING_AVAILABLE = False
    print("Warning: DL clustering not available")


class NDJSONEmitter:
    """Utility class for emitting NDJSON messages to stdout."""
    
    log_file = None  # Will be set by PipelineRunner
    
    @staticmethod
    def emit(message: Dict[str, Any]):
        """Emit a single NDJSON message."""
        sys.stdout.write(json.dumps(message) + '\n')
        sys.stdout.flush()
        
        # Also write to log file if available
        if NDJSONEmitter.log_file and message.get('type') == 'log':
            try:
                with open(NDJSONEmitter.log_file, 'a') as f:
                    f.write(f"[{message.get('level', 'info').upper()}] {message.get('message', '')}\n")
            except:
                pass  # Don't fail if logging fails
    
    @staticmethod
    def progress(stage: str, percent: int, message: str):
        """Emit a progress update."""
        NDJSONEmitter.emit({
            "type": "progress",
            "stage": stage,
            "percent": percent,
            "message": message
        })
    
    @staticmethod
    def log(level: str, message: str):
        """Emit a log message."""
        NDJSONEmitter.emit({
            "type": "log",
            "level": level,
            "message": message
        })
    
    @staticmethod
    def result(artifact: str, path: Optional[str] = None, data: Optional[Dict] = None):
        """Emit a result artifact."""
        msg = {"type": "result", "artifact": artifact}
        if path:
            msg["path"] = path
        if data:
            msg["data"] = data
        NDJSONEmitter.emit(msg)
    
    @staticmethod
    def threshold_request(calculated: float):
        """Request threshold confirmation from user."""
        msg = {
            "type": "threshold_request",
            "calculated": calculated
        }
        print(f"[DEBUG] Emitting threshold_request: {msg}", file=sys.stderr)
        NDJSONEmitter.emit(msg)
        sys.stdout.flush()  # Ensure it's sent immediately
    
    @staticmethod
    def complete(success: bool, error: Optional[str] = None):
        """Emit completion status."""
        msg = {"type": "complete", "success": success}
        if error:
            msg["error"] = error
        NDJSONEmitter.emit(msg)


class PipelineRunner:
    """Main pipeline runner that orchestrates the analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.emit = NDJSONEmitter
        
        # Extract configuration
        self.fasta_dir = config.get('fasta_dir', '')
        self.clean_fasta = config.get('clean_fasta', False)
        self.database_type = config.get('database_type', 'IMGT')  # IMGT or Custom
        self.database_v = config.get('database_v', '')
        self.database_d = config.get('database_d', '')
        self.database_j = config.get('database_j', '')
        self.output_dir = config.get('output_dir', '')
        self.backend_dir = config.get('backend_dir', backend_dir)
        
        # Set up paths
        self.bin_dir = os.path.join(self.backend_dir, '..', 'geneGUI', 'bin')
        self.data_dir = os.path.join(self.backend_dir, '..', 'geneGUI', 'data')
        
        # Create output directory
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
        else:
            self.output_dir = os.path.join(self.backend_dir, '..', 'geneGUI', 'outs')
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Normalize the output directory path to absolute and resolve any ../
        self.output_dir = os.path.abspath(self.output_dir)
        
        # Set up persistent log file
        NDJSONEmitter.log_file = os.path.join(self.output_dir, 'pipeline.log')
        try:
            # Clear old log file
            with open(NDJSONEmitter.log_file, 'w') as f:
                f.write(f"=== Pipeline Started ===\n")
        except:
            NDJSONEmitter.log_file = None
        
        # State
        self.fasta_paths: List[str] = []
        self.combined_fasta: Optional[str] = None
        self.cancelled = False
    
    def check_cancelled(self):
        """Check if cancellation was requested."""
        # Non-blocking check for cancel message on stdin
        # In a real implementation, this would use select() or threading
        return self.cancelled
    
    def load_fasta_files(self) -> bool:
        """Load FASTA files from the specified directory."""
        self.emit.progress("loading", 5, "Loading FASTA files...")
        
        if not os.path.isdir(self.fasta_dir):
            self.emit.log("error", f"FASTA directory does not exist: {self.fasta_dir}")
            return False
        
        # Get all fasta files
        self.fasta_paths = [
            os.path.join(self.fasta_dir, f) 
            for f in os.listdir(self.fasta_dir) 
            if not f.startswith('.') and (f.endswith('.fasta') or f.endswith('.fa'))
        ]
        
        if not self.fasta_paths:
            self.emit.log("error", f"No FASTA files found in: {self.fasta_dir}")
            return False
        
        self.emit.log("info", f"Found {len(self.fasta_paths)} FASTA file(s)")
        self.emit.result("fasta_count", data={"count": len(self.fasta_paths), "files": [os.path.basename(f) for f in self.fasta_paths]})
        
        return True
    
    def clean_fasta_files(self) -> bool:
        """Clean FASTA files if requested."""
        if not self.clean_fasta:
            return True
        
        self.emit.progress("cleaning", 10, "Cleaning FASTA files...")
        
        clean_fasta_dir = os.path.join(self.output_dir, 'clean_fasta')
        os.makedirs(clean_fasta_dir, exist_ok=True)
        
        cleaned_paths = []
        for i, fasta_path in enumerate(self.fasta_paths):
            filename = os.path.basename(fasta_path)
            dot_idx = filename.find('.')
            if dot_idx == -1:
                clean_name = filename + '_clean'
            else:
                clean_name = filename[:dot_idx] + '_clean' + filename[dot_idx:]
            
            clean_path = os.path.join(clean_fasta_dir, clean_name)
            
            # Check if clean file already exists and is valid
            if os.path.exists(clean_path) and os.path.getsize(clean_path) > 0:
                self.emit.log("info", f"Using existing cleaned file: {clean_name}")
            else:
                try:
                    cl.clean_imgt(fasta_path, clean_path)
                    self.emit.log("info", f"Cleaned: {filename}")
                except Exception as e:
                    self.emit.log("warn", f"Failed to clean {filename}: {str(e)}")
                    continue
            
            cleaned_paths.append(clean_path)
            
            # Update progress
            progress = 10 + int((i + 1) / len(self.fasta_paths) * 5)
            self.emit.progress("cleaning", progress, f"Cleaned {i + 1}/{len(self.fasta_paths)} files")
        
        self.fasta_paths = cleaned_paths
        return len(self.fasta_paths) > 0
    
    def setup_databases(self) -> bool:
        """Set up database paths."""
        self.emit.progress("setup", 15, "Setting up databases...")
        
        if self.database_type == 'IMGT':
            imgt_dir = os.path.join(self.data_dir, 'IMGT_Human_Database')
            self.database_v = os.path.join(imgt_dir, 'Human_V.fasta')
            self.database_d = os.path.join(imgt_dir, 'Human_D.fasta')
            self.database_j = os.path.join(imgt_dir, 'Human_J.fasta')
        
        # Verify databases exist
        for db_name, db_path in [('V', self.database_v), ('D', self.database_d), ('J', self.database_j)]:
            if not os.path.exists(db_path):
                self.emit.log("error", f"Database {db_name} not found: {db_path}")
                return False
        
        # Clean database files
        clean_db_dir = os.path.join(self.output_dir, 'clean_db_files')
        os.makedirs(clean_db_dir, exist_ok=True)
        
        # Remove old clean db files
        for f in glob.glob(os.path.join(clean_db_dir, "*")):
            try:
                os.remove(f)
            except:
                pass
        
        # Clean V database
        vname = os.path.basename(self.database_v)
        self.database_v_clean = os.path.join(clean_db_dir, vname.replace('.fasta', '_clean.fasta'))
        cl.clean_imgt(self.database_v, self.database_v_clean)
        
        # Clean D database
        dname = os.path.basename(self.database_d)
        self.database_d_clean = os.path.join(clean_db_dir, dname.replace('.fasta', '_clean.fasta'))
        cl.clean_imgt(self.database_d, self.database_d_clean)
        
        # Clean J database
        jname = os.path.basename(self.database_j)
        self.database_j_clean = os.path.join(clean_db_dir, jname.replace('.fasta', '_clean.fasta'))
        cl.clean_imgt(self.database_j, self.database_j_clean)
        
        self.emit.log("info", "Database files cleaned and ready")
        return True
    
    def combine_fasta_files(self) -> bool:
        """Combine all FASTA files into one."""
        self.emit.progress("combining", 18, "Combining FASTA files...")
        
        self.combined_fasta = os.path.join(self.output_dir, 'combined.fasta')
        
        with open(self.combined_fasta, 'w') as outfile:
            for fasta_path in self.fasta_paths:
                base = os.path.basename(fasta_path)
                with open(fasta_path, 'r') as infile:
                    for line in infile:
                        if line.startswith('>'):
                            # Use ||| as delimiter to avoid conflicts with underscores in filenames
                            outfile.write(line.rstrip() + '|||' + base + '\n')
                        else:
                            outfile.write(line)
        
        self.emit.log("info", f"Combined {len(self.fasta_paths)} files into {self.combined_fasta}")
        return True
    
    def build_blast_databases(self) -> bool:
        """Build BLAST databases from cleaned database files."""
        self.emit.progress("blast_db", 20, "Building BLAST databases...")
        
        makeblastdb_path = os.path.join(self.bin_dir, 'makeblastdb')
        db_files_dir = os.path.join(self.data_dir, 'Database-Files')
        os.makedirs(db_files_dir, exist_ok=True)
        
        import subprocess
        
        for db_type, clean_path in [('V', self.database_v_clean), ('D', self.database_d_clean), ('J', self.database_j_clean)]:
            db_name = os.path.basename(clean_path)
            db_out = os.path.join(db_files_dir, db_name)
            
            cmd = f"{makeblastdb_path} -parse_seqids -dbtype nucl -in {clean_path} -out {db_out}"
            result = os.system(cmd)
            
            if result != 0:
                self.emit.log("warn", f"makeblastdb for {db_type} returned non-zero exit code")
            
            # Store the database path for later use
            setattr(self, f'igblast_db_{db_type.lower()}', db_out)
        
        self.emit.log("info", "BLAST databases built successfully")
        return True
    
    def run_igblast(self) -> bool:
        """Run IgBLAST analysis."""
        self.emit.progress("igblast", 25, "Running IgBLAST analysis...")
        
        try:
            df, raw_output = blast.blast_get_top_hits_v(
                input_fp=self.combined_fasta,
                db_V_fp=self.igblast_db_v,
                db_D_fp=self.igblast_db_d,
                db_J_fp=self.igblast_db_j,
                bin_dir=self.bin_dir,
                data_dir=self.data_dir,
                output_dir=self.output_dir
            )
            
            # Save results
            outdata_path = os.path.join(self.output_dir, 'outdata.csv')
            df.to_csv(outdata_path)
            
            self.emit.log("info", f"IgBLAST analysis complete, found {len(df)} hits")
            self.emit.result("igblast_output", path=outdata_path)
            
            self.blast_df = df
            return True
            
        except Exception as e:
            self.emit.log("error", f"IgBLAST failed: {str(e)}")
            return False
    
    def calculate_threshold(self) -> Optional[float]:
        """Calculate distance threshold using R script."""
        self.emit.progress("threshold", 35, "Calculating distance threshold...")
        
        try:
            # Run MakeDb first
            fmt7_path = os.path.join(self.output_dir, "ig_out_data.fmt7")
            db_pass_path = os.path.join(self.output_dir, "ig_out_data_db-pass.tsv")
            
            # Update outs_dir in clonalityFunctions to use our output_dir
            import utils.clonalityFunctions as clonalityFunctions
            # Temporarily update the global outs_dir
            original_outs_dir = clonalityFunctions.outs_dir
            clonalityFunctions.outs_dir = self.output_dir
            
            try:
                make_db(fmt7_path, self.database_j, self.database_v, self.database_d, self.combined_fasta)
                
                # Calculate distribution using R script
                script_path = os.path.join(self.backend_dir, 'scripts', 'calculateDistribution.R')
                plot_path = os.path.join(self.output_dir, 'distributionPlot.png')
                calculated_dist = findDist(db_pass_path, pathToScript=script_path, pathToPlot=plot_path)
            finally:
                # Restore original outs_dir
                clonalityFunctions.outs_dir = original_outs_dir
            
            self.emit.log("info", f"Calculated distance threshold: {calculated_dist}")
            
            # Request user confirmation
            self.emit.threshold_request(calculated_dist)
            self.emit.log("info", f"Waiting for threshold response from user (calculated: {calculated_dist})")
            
            # Flush stdout to ensure the request is sent
            sys.stdout.flush()
            
            # Wait for response from stdin
            # Note: This will block until a line is received
            try:
                response_line = sys.stdin.readline()
                self.emit.log("debug", f"Received line from stdin: {response_line[:100] if response_line else 'None'}")
            except Exception as e:
                self.emit.log("error", f"Error reading from stdin: {str(e)}")
                response_line = None
            
            if response_line:
                try:
                    response = json.loads(response_line.strip())
                    self.emit.log("info", f"Parsed threshold response: {response}")
                    if response.get('type') == 'threshold_response':
                        threshold_value = float(response.get('value', calculated_dist))
                        self.emit.log("info", f"Using threshold value: {threshold_value}")
                        return threshold_value
                    elif response.get('type') == 'cancel':
                        self.cancelled = True
                        self.emit.log("info", "User cancelled threshold confirmation")
                        return None
                except json.JSONDecodeError as e:
                    self.emit.log("warn", f"Failed to parse threshold response JSON: {response_line[:100]}, error: {str(e)}")
            
            # If no response or invalid response, use calculated value
            self.emit.log("info", f"No valid threshold response received, using calculated value: {calculated_dist}")
            return calculated_dist
            
        except Exception as e:
            self.emit.log("error", f"Threshold calculation failed: {str(e)}")
            return 0.1  # Default threshold
    
    def run_clonality_analysis(self, threshold: float) -> bool:
        """Run clonality analysis."""
        self.emit.progress("clonality", 50, "Running clonality analysis...")
        
        try:
            import utils.clonalityFunctions as clonalityFunctions
            # Update outs_dir to use our output_dir
            original_outs_dir = clonalityFunctions.outs_dir
            clonalityFunctions.outs_dir = self.output_dir
            
            try:
                db_pass_path = os.path.join(self.output_dir, "ig_out_data_db-pass.tsv")
                clone_pass_path = os.path.join(self.output_dir, "ig_out_data_db-pass_clone-pass.tsv")
                
                # Define clones
                define_clonality(db_pass_path, str(threshold))
                self.emit.log("info", "Clone definition complete")
                
                # Create germlines
                create_germline(clone_pass_path, self.database_v, self.database_d, self.database_j)
                self.emit.log("info", "Germline creation complete")
            finally:
                # Restore original outs_dir
                clonalityFunctions.outs_dir = original_outs_dir
            
            germ_pass_path = os.path.join(self.output_dir, "ig_out_data_db-pass_clone-pass_germ-pass.tsv")
            self.emit.result("clonality_output", path=germ_pass_path)
            
            return True
            
        except Exception as e:
            self.emit.log("error", f"Clonality analysis failed: {str(e)}")
            return False
    
    def build_trees(self) -> bool:
        """Build phylogenetic trees."""
        self.emit.log("info", "=" * 60)
        self.emit.log("info", "STARTING TREE BUILDING STEP")
        self.emit.log("info", "=" * 60)
        self.emit.progress("trees", 70, "Building phylogenetic trees...")
        
        try:
            import pandas as pd
            import glob
            import subprocess
            
            # CLEAN OLD TREE FILES FIRST - before doing anything else
            trees_dir = os.path.join(self.output_dir, 'trees')
            os.makedirs(trees_dir, exist_ok=True)
            
            self.emit.log("info", f"Cleaning old tree files from {trees_dir}...")
            old_trees = glob.glob(os.path.join(trees_dir, '*.png')) + glob.glob(os.path.join(trees_dir, '*.newick'))
            removed_count = 0
            for old_tree in old_trees:
                try:
                    os.remove(old_tree)
                    removed_count += 1
                except Exception as e:
                    self.emit.log("warn", f"Could not remove old tree file {old_tree}: {e}")
            
            if removed_count > 0:
                self.emit.log("info", f"Removed {removed_count} old tree file(s) from previous runs")
            else:
                self.emit.log("info", "No old tree files found to clean")
            
            germ_pass_path = os.path.join(self.output_dir, "ig_out_data_db-pass_clone-pass_germ-pass.tsv")
            
            if not os.path.exists(germ_pass_path):
                self.emit.log("warn", "Germline pass file not found, skipping tree building")
                # Send empty result to frontend so it knows there are no trees
                self.emit.result("tree_images", data={
                    "images": [],
                    "tree_metadata": []
                })
                return True
            
            # Read clone data
            clonedf = pd.read_table(germ_pass_path)
            
            # Sort by clone_id frequency
            clonedf['clone_freq'] = clonedf.groupby('clone_id')['sequence_id'].transform('count')
            clonedf.sort_values('clone_freq', inplace=True, ascending=False)
            
            # Get top clones for tree building (by clone size)
            # First, identify clones by size and filter to only those with >= 3 sequences
            clone_sizes = clonedf.groupby('clone_id').size().sort_values(ascending=False)
            
            # Filter to only clones with >= 3 sequences (required for tree building)
            valid_clones = clone_sizes[clone_sizes >= 3]
            
            # Get top 20 clones that have >= 3 sequences
            top_clones = valid_clones.head(20).index.tolist()
            
            if len(top_clones) == 0:
                self.emit.log("warn", "No clones with >= 3 sequences found, skipping tree building")
                # Still send empty result to frontend
                self.emit.result("tree_images", data={
                    "images": [],
                    "tree_metadata": []
                })
                return True
            
            self.emit.log("info", f"Found {len(top_clones)} clones with >= 3 sequences (top {min(20, len(valid_clones))} selected)")
            
            # Write ALL sequences from these top clones to build-trees-input.tsv
            tempdf = clonedf[clonedf['clone_id'].isin(top_clones)].copy()
            
            # Drop the clone_freq column if it exists (was only for sorting)
            if 'clone_freq' in tempdf.columns:
                tempdf = tempdf.drop(columns=['clone_freq'])
            
            build_trees_input_path = os.path.join(self.output_dir, 'build-trees-input.tsv')
            tempdf.to_csv(build_trees_input_path, sep="\t", index=False)
            
            # Verify the file was created and has data
            if not os.path.exists(build_trees_input_path):
                self.emit.log("error", f"Failed to create build-trees-input.tsv file!")
                # Send empty result to frontend
                self.emit.result("tree_images", data={
                    "images": [],
                    "tree_metadata": []
                })
                return True
            
            file_size = os.path.getsize(build_trees_input_path)
            self.emit.log("info", f"Prepared {len(tempdf)} sequences from {len(top_clones)} clones for tree building")
            self.emit.log("info", f"Created build-trees-input.tsv ({file_size} bytes) with clones: {top_clones[:10]}{'...' if len(top_clones) > 10 else ''}")
            
            # Create sequence count mapping BEFORE BuildTrees collapses sequences
            # Count how many times each unique sequence appears WITHIN EACH CLONE
            # BuildTrees collapses identical sequences, so we need to count by sequence content
            # CRITICAL: Store counts per clone to avoid cross-clone contamination
            from Bio import SeqIO
            sequence_counts_by_clone = {}  # {clone_id: {seq_id: count}}
            combined_fasta = os.path.join(self.output_dir, 'combined.fasta')
            
            if os.path.exists(combined_fasta):
                # Create a mapping of sequence_id -> sequence content
                seq_content_map = {}
                for record in SeqIO.parse(combined_fasta, "fasta"):
                    # Normalize sequence: uppercase and remove gaps
                    seq_content = str(record.seq).upper().replace('-', '').replace('N', '')
                    seq_content_map[str(record.id)] = seq_content
                
                # Count sequences by their actual DNA content (not just ID) per clone
                # Store counts by SEQUENCE CONTENT, not by ID, because BuildTrees collapses identical sequences
                for clone_id in top_clones:
                    clone_seqs = clonedf[clonedf['clone_id'] == clone_id]
                    # Group by sequence content to count duplicates within this clone
                    content_counts = {}
                    for _, row in clone_seqs.iterrows():
                        seq_id = str(row['sequence_id'])
                        if seq_id in seq_content_map:
                            seq_content = seq_content_map[seq_id]
                            if seq_content not in content_counts:
                                content_counts[seq_content] = 0
                            content_counts[seq_content] += 1
                    
                    # Store counts BY CONTENT for this clone
                    # The R script will match sequences by content, not by ID
                    sequence_counts_by_clone[str(clone_id)] = content_counts
            else:
                # Fallback: count by sequence_id (won't catch duplicates with different IDs)
                for clone_id in top_clones:
                    clone_seqs = clonedf[clonedf['clone_id'] == clone_id]
                    sequence_counts_by_clone[str(clone_id)] = {}
                    for seq_id in clone_seqs['sequence_id']:
                        seq_id_str = str(seq_id)
                        if seq_id_str not in sequence_counts_by_clone[str(clone_id)]:
                            sequence_counts_by_clone[str(clone_id)][seq_id_str] = 1
            
            # Save sequence counts to a JSON file for R script to read
            import json
            sequence_counts_path = os.path.join(self.output_dir, 'sequence_counts.json')
            with open(sequence_counts_path, 'w') as f:
                json.dump(sequence_counts_by_clone, f)
            
            # Run BuildTrees (without IgPhyML)
            build_trees_dir = os.path.join(self.output_dir, 'build-trees-input')
            os.system(f"rm -rf {build_trees_dir}")
            
            self.emit.log("info", f"Running BuildTrees.py on {build_trees_input_path}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(self.output_dir)
                # Build trees with BuildTrees (removed --collapse to keep more unique sequences)
                # --clean all: only remove sequences with ambiguous nucleotides
                # This preserves more phylogenetic information for lineage reconstruction
                # Log to file for debugging
                debug_log = os.path.join(self.output_dir, 'tree_building_debug.log')
                with open(debug_log, 'w') as f:
                    f.write(f"Running BuildTrees.py at {os.getcwd()}\n")
                    f.write(f"Command: BuildTrees.py -d build-trees-input.tsv --clean all\n\n")
                
                build_trees_result = subprocess.run(
                    ['BuildTrees.py', '-d', 'build-trees-input.tsv', '--clean', 'all'],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                # Append results to debug log
                with open(debug_log, 'a') as f:
                    f.write(f"Return code: {build_trees_result.returncode}\n\n")
                    f.write(f"STDOUT:\n{build_trees_result.stdout}\n\n")
                    f.write(f"STDERR:\n{build_trees_result.stderr}\n")
                
                if build_trees_result.returncode != 0:
                    self.emit.log("error", f"BuildTrees.py failed! See {debug_log} for details")
                    self.emit.log("error", f"BuildTrees stderr: {build_trees_result.stderr[:500] if build_trees_result.stderr else 'no stderr'}")
                else:
                    self.emit.log("info", f"BuildTrees.py completed successfully (log: {debug_log})")
                
                # Check if FASTA files were created
                if os.path.exists(build_trees_dir):
                    fasta_count = len(glob.glob(os.path.join(build_trees_dir, '*.fasta')))
                    self.emit.log("info", f"BuildTrees created {fasta_count} FASTA file(s) in {build_trees_dir}")
                else:
                    self.emit.log("warn", f"BuildTrees directory {build_trees_dir} was not created!")
                    
            finally:
                os.chdir(original_cwd)
            
            # Build trees using IQ-TREE2 (Maximum Likelihood) with fallback to Neighbor-Joining
            # IQ-TREE2 provides better phylogenetic inference than NJ, closer to IgPhyML quality
            # Automatically falls back to NJ if IQ-TREE2 is not installed
            # (subprocess already imported at top of try block)
            
            # trees_dir already created and cleaned above
            
            # Use the new IQ-TREE2 script (with automatic NJ fallback)
            build_trees_r = os.path.join(backend_dir, 'scripts', 'build-trees-iqtree.R')
            
            # Estimate time: ~20-40 minutes for 20 trees, more with many clones
            # With parallel processing: ~5-10 minutes on 8-core system
            self.emit.log("info", "Building phylogenetic trees... This may take 10-30 minutes for large datasets")
            self.emit.log("info", "Tree building is parallelized across CPU cores for faster processing")
            
            # Set up R environment explicitly to avoid "cannot find system Renviron" error
            r_env = os.environ.copy()
            r_env['R_HOME'] = '/Library/Frameworks/R.framework/Resources'
            r_env['R_SHARE_DIR'] = '/Library/Frameworks/R.framework/Resources/share'
            r_env['R_INCLUDE_DIR'] = '/Library/Frameworks/R.framework/Resources/include'
            r_env['R_DOC_DIR'] = '/Library/Frameworks/R.framework/Resources/doc'
            # Set editor to avoid "invalid value for 'editor'" error
            r_env['EDITOR'] = '/usr/bin/nano'
            # Try to use the direct R binary path to bypass wrapper issues
            r_cmd = '/Library/Frameworks/R.framework/Versions/4.5-arm64/Resources/bin/Rscript'
            
            result = subprocess.run(
                [r_cmd, build_trees_r, self.output_dir],
                capture_output=True,
                text=True,
                timeout=3600,  # Increased to 60 minutes (was 300 seconds = 5 min)
                env=r_env
            )
            
            if result.returncode != 0:
                self.emit.log("error", f"Tree building R script failed with return code {result.returncode}")
                self.emit.log("error", f"R script stderr: {result.stderr[:500] if result.stderr else 'no stderr'}")
                self.emit.log("error", f"R script stdout: {result.stdout[:500] if result.stdout else 'no stdout'}")
                # Send empty result to frontend
                self.emit.result("tree_images", data={
                    "images": [],
                    "tree_metadata": []
                })
                return True  # Non-fatal
            
            # Count generated trees (only from this run)
            tree_files = glob.glob(os.path.join(trees_dir, '*.newick'))
            self.emit.log("info", f"Tree building complete. Found {len(tree_files)} Newick file(s) in {trees_dir}")
            
            if len(tree_files) == 0:
                self.emit.log("warn", f"No tree files generated! Check R script output above.")
                self.emit.log("info", f"R script stdout: {result.stdout[:1000] if result.stdout else 'no stdout'}")
            elif len(tree_files) > len(top_clones):
                self.emit.log("warn", f"Generated {len(tree_files)} trees but expected max {len(top_clones)}. Some clones may have been split or had multiple trees.")
            elif len(tree_files) < len(top_clones):
                self.emit.log("info", f"Generated {len(tree_files)} trees from {len(top_clones)} clones (some clones may have been skipped due to < 3 sequences after cleaning)")
            else:
                self.emit.log("info", f"Successfully built {len(tree_files)} phylogenetic trees for {len(top_clones)} clones")
            return True
            
        except Exception as e:
            self.emit.log("warn", f"Tree building failed (non-fatal): {str(e)}")
            # Send empty result to frontend so it knows there are no trees
            self.emit.result("tree_images", data={
                "images": [],
                "tree_metadata": []
            })
            return True  # Non-fatal
    
    def visualize_trees(self) -> bool:
        """Generate tree visualizations."""
        self.emit.log("info", "=" * 60)
        self.emit.log("info", "STARTING TREE VISUALIZATION STEP")
        self.emit.log("info", "=" * 60)
        self.emit.progress("visualize", 85, "Generating tree visualizations...")
        
        try:
            import subprocess
            
            trees_dir = os.path.join(self.output_dir, 'trees')
            os.makedirs(trees_dir, exist_ok=True)
            
            visualize_script = os.path.join(backend_dir, 'scripts', 'visualize-tree.R')
            
            self.emit.log("info", f"Running tree visualization script: {visualize_script}")
            self.emit.log("info", f"Output directory: {self.output_dir}")
            
            # Set up R environment explicitly
            r_env = os.environ.copy()
            r_env['R_HOME'] = '/Library/Frameworks/R.framework/Resources'
            r_env['R_SHARE_DIR'] = '/Library/Frameworks/R.framework/Resources/share'
            r_env['R_INCLUDE_DIR'] = '/Library/Frameworks/R.framework/Resources/include'
            r_env['R_DOC_DIR'] = '/Library/Frameworks/R.framework/Resources/doc'
            r_env['EDITOR'] = '/usr/bin/nano'
            r_cmd = '/Library/Frameworks/R.framework/Versions/4.5-arm64/Resources/bin/Rscript'
            
            result = subprocess.run(
                [r_cmd, visualize_script, self.output_dir],
                capture_output=True,
                text=True,
                timeout=300,
                env=r_env
            )
            
            if result.returncode != 0:
                self.emit.log("error", f"Tree visualization failed with return code {result.returncode}")
                self.emit.log("error", f"R script stderr: {result.stderr[:500] if result.stderr else 'no stderr'}")
                self.emit.log("error", f"R script stdout: {result.stdout[:500] if result.stdout else 'no stdout'}")
            else:
                self.emit.log("info", f"Tree visualization script completed successfully")
                if result.stdout:
                    self.emit.log("info", f"Visualization output: {result.stdout[:200]}")
            
            # List generated tree images and sort by clone size (largest first)
            # Only include trees that have both PNG and Newick files (ensures they're complete and from current run)
            all_tree_images = glob.glob(os.path.join(trees_dir, '*.png'))
            all_tree_newicks = {os.path.basename(f).replace('.newick', '') for f in glob.glob(os.path.join(trees_dir, '*.newick'))}
            
            # Filter to only include PNGs that have corresponding Newick files
            tree_images = [
                img for img in all_tree_images
                if os.path.basename(img).replace('.png', '') in all_tree_newicks
            ]
            
            if len(all_tree_images) > len(tree_images):
                self.emit.log("warn", f"Found {len(all_tree_images)} PNG files but only {len(tree_images)} have corresponding Newick files. Filtering incomplete trees.")
            
            self.emit.log("info", f"Found {len(tree_images)} complete tree(s) (PNG + Newick)")
            
            if tree_images:
                # Load clone sizes for sorting
                try:
                    import pandas as pd
                    clone_pass_path = os.path.join(self.output_dir, 'ig_out_data_db-pass_clone-pass_germ-pass.tsv')
                    
                    if os.path.exists(clone_pass_path):
                        clone_df = pd.read_table(clone_pass_path)
                        
                        # Calculate clone sizes
                        clone_sizes = {}
                        for clone_id in clone_df['clone_id'].unique():
                            if pd.notna(clone_id):
                                clone_sizes[int(clone_id)] = len(clone_df[clone_df['clone_id'] == clone_id])
                        
                        # Sort tree images by clone size (extract clone ID from filename)
                        def get_clone_size(tree_path):
                            # Extract clone ID from filename like "tree_192.png" -> 192
                            basename = os.path.basename(tree_path)
                            match = basename.replace('tree_', '').replace('.png', '')
                            try:
                                clone_id = int(match)
                                return clone_sizes.get(clone_id, 0)
                            except:
                                return 0
                        
                        # Sort by clone size descending (largest first)
                        tree_images.sort(key=get_clone_size, reverse=True)
                        
                        self.emit.log("info", f"Sorted {len(tree_images)} trees by clone size (largest first)")
                    else:
                        # Fallback: sort alphabetically
                        tree_images.sort()
                        self.emit.log("info", f"Generated {len(tree_images)} tree visualization(s)")
                        
                except Exception as e:
                    # Fallback: sort alphabetically
                    tree_images.sort()
                    self.emit.log("warn", f"Could not sort trees by clone size: {str(e)}")
                
                # Send tree images with clone size metadata for better display
                # Use absolute paths to avoid path resolution issues
                tree_data = []
                for tree_path in tree_images:
                    # Normalize to absolute path
                    abs_tree_path = os.path.abspath(tree_path)
                    basename = os.path.basename(abs_tree_path)
                    match = basename.replace('tree_', '').replace('.png', '')
                    try:
                        clone_id = int(match)
                        clone_size = clone_sizes.get(clone_id, 0) if 'clone_sizes' in locals() else 0
                        tree_data.append({
                            'path': abs_tree_path,
                            'clone_id': clone_id,
                            'clone_size': clone_size
                        })
                    except:
                        tree_data.append({
                            'path': abs_tree_path,
                            'clone_id': None,
                            'clone_size': 0
                        })
                
                self.emit.result("tree_images", data={
                    "images": tree_images,
                    "tree_metadata": tree_data
                })
                self.emit.log("info", f"Sent {len(tree_images)} tree(s) to frontend")
            else:
                # Always send result, even if empty, so frontend knows there are no trees
                self.emit.log("warn", "No tree images found - sending empty list to frontend")
                self.emit.result("tree_images", data={
                    "images": [],
                    "tree_metadata": []
                })
            
            return True
            
        except Exception as e:
            self.emit.log("warn", f"Tree visualization failed (non-fatal): {str(e)}")
            return True  # Non-fatal
    
    def load_results(self) -> bool:
        """Load and emit final results."""
        self.emit.progress("results", 95, "Loading results...")
        
        try:
            import pandas as pd
            from Bio import SeqIO
            
            # Load sequence names from combined.fasta (original input sequences)
            # This matches the original GUI behavior which uses sortNames()
            sequence_names = []
            if os.path.exists(self.combined_fasta):
                for record in SeqIO.parse(self.combined_fasta, "fasta"):
                    sequence_names.append(record.id)
            
            # Load IgBLAST results
            outdata_path = os.path.join(self.output_dir, 'outdata.csv')
            if os.path.exists(outdata_path):
                blast_df = pd.read_csv(outdata_path)
                
                # Convert to records for JSON - only for sequences in combined.fasta
                sequences = []
                for query_id in sequence_names:
                    if pd.isna(query_id):
                        continue
                    
                    # IgBLAST may prefix reversed sequences with "reversed|"
                    # Try multiple matching strategies to find the sequence data
                    seq_data = blast_df[blast_df['query id'] == query_id]
                    
                    # If not found, try with "reversed|" prefix
                    if seq_data.empty:
                        seq_data = blast_df[blast_df['query id'] == f"reversed|{query_id}"]
                    
                    # If still not found, try matching without the reversed prefix
                    # (in case query_id accidentally has the prefix)
                    if seq_data.empty and query_id.startswith('reversed|'):
                        clean_id = query_id.replace('reversed|', '', 1)
                        seq_data = blast_df[blast_df['query id'] == clean_id]
                    
                    # Skip if no blast data for this sequence
                    if seq_data.empty:
                        continue
                    
                    seq_record = {
                        'id': str(query_id),
                        'name': str(query_id),
                        'v_gene': None,
                        'd_gene': None,
                        'j_gene': None,
                        'v_locus': None,
                        'd_locus': None,
                        'j_locus': None,
                        'cdr3_dna': None,
                        'cdr3_peptide': None,
                        'somatic_mutations': None,
                        'isotype': None
                    }
                    
                    # Extract V gene info
                    v_data = seq_data[seq_data['chain type'] == 'V']
                    if not v_data.empty:
                        row = v_data.iloc[0]
                        seq_record['v_gene'] = str(row['subject id']) if pd.notna(row['subject id']) else None
                        if seq_record['v_gene']:
                            g = seq_record['v_gene']
                            if '*' in g:
                                idx = g.index('*')
                                if len(g) > 4:
                                    seq_record['v_locus'] = g[3] + g[2] + g[4:idx]
                            if 'L' in g:
                                seq_record['isotype'] = 'Lambda'
                            elif 'K' in g:
                                seq_record['isotype'] = 'Kappa'
                            else:
                                seq_record['isotype'] = 'Heavy'
                    
                    # Extract D gene info
                    d_data = seq_data[seq_data['chain type'] == 'D']
                    if not d_data.empty:
                        row = d_data.iloc[0]
                        seq_record['d_gene'] = str(row['subject id']) if pd.notna(row['subject id']) else None
                        if seq_record['d_gene'] and '*' in seq_record['d_gene']:
                            g = seq_record['d_gene']
                            idx = g.index('*')
                            if len(g) > 4:
                                seq_record['d_locus'] = g[3] + g[2] + g[4:idx]
                    
                    # Extract J gene info
                    j_data = seq_data[seq_data['chain type'] == 'J']
                    if not j_data.empty:
                        row = j_data.iloc[0]
                        seq_record['j_gene'] = str(row['subject id']) if pd.notna(row['subject id']) else None
                        if seq_record['j_gene'] and '*' in seq_record['j_gene']:
                            g = seq_record['j_gene']
                            idx = g.index('*')
                            if len(g) > 4:
                                seq_record['j_locus'] = g[3] + g[2] + g[4:idx]
                    
                    # Extract CDR3 info from blast CSV (for somatic mutations)
                    cdr3_data = seq_data[seq_data['chain type'] == 'CDR3']
                    if not cdr3_data.empty:
                        row = cdr3_data.iloc[0]
                        seq_record['somatic_mutations'] = int(row['alignment length']) if pd.notna(row['alignment length']) else None
                    
                    sequences.append(seq_record)
            
            # Load clonality data and CDR3 from the clonality TSV file
            # This is the authoritative source for CDR3 data (junction and junction_aa columns)
            clone_pass_path = os.path.join(self.output_dir, 'ig_out_data_db-pass_clone-pass_germ-pass.tsv')
            clone_data = {}
            if os.path.exists(clone_pass_path):
                clone_df = pd.read_table(clone_pass_path)
                for _, row in clone_df.iterrows():
                    seq_id = str(row['sequence_id'])
                    clone_id = row['clone_id'] if pd.notna(row['clone_id']) else None
                    
                    # Extract CDR3 data from junction columns
                    junction = str(row['junction']) if pd.notna(row['junction']) else None
                    junction_aa = str(row['junction_aa']) if pd.notna(row['junction_aa']) else None
                    
                    clone_data[seq_id] = {
                        'clone_id': int(clone_id) if clone_id is not None else None,
                        'clone_count': len(clone_df[clone_df['clone_id'] == clone_id]) if clone_id is not None else 0,
                        'productive': True,  # Productive sequences in pass file
                        'cdr3_dna': junction,
                        'cdr3_peptide': junction_aa
                    }
            
            # Load non-productive sequences from fail file (if --failed flag was used)
            clone_fail_path = os.path.join(self.output_dir, 'ig_out_data_db-fail.tsv')
            if os.path.exists(clone_fail_path):
                self.emit.log("info", f"Loading non-productive sequences from fail file")
                fail_df = pd.read_table(clone_fail_path)
                for _, row in fail_df.iterrows():
                    seq_id = str(row['sequence_id'])
                    
                    # Extract CDR3 data from junction columns (if available)
                    junction = str(row['junction']) if pd.notna(row['junction']) else None
                    junction_aa = str(row['junction_aa']) if pd.notna(row['junction_aa']) else None
                    
                    clone_data[seq_id] = {
                        'clone_id': None,  # Non-productive sequences don't get clone IDs
                        'clone_count': 0,
                        'productive': False,  # Non-productive sequences in fail file
                        'cdr3_dna': junction,
                        'cdr3_peptide': junction_aa
                    }
                self.emit.log("info", f"Added {len(fail_df)} non-productive sequences")
            
            # Merge clone data (including CDR3 from clonality file) into sequences
            for seq in sequences:
                if seq['id'] in clone_data:
                    # Update with clonality data
                    seq.update(clone_data[seq['id']])
                    # If somatic_mutations wasn't set from blast CSV, set to None
                    if seq['somatic_mutations'] is None and seq['cdr3_dna']:
                        # Could calculate from junction_length if needed
                        pass
            
            # Group sequences by file
            file_groups = {}
            for seq in sequences:
                # Extract filename from sequence ID (format: seqname|||filename.fasta)
                # The filename is appended with ||| delimiter to avoid conflicts with underscores
                seq_id = seq['id']
                
                # Split by the ||| delimiter
                if '|||' in seq_id:
                    parts = seq_id.split('|||')
                    filename = parts[-1] if len(parts) > 1 else 'unknown.fasta'
                else:
                    # Fallback for old format with _ delimiter
                    parts = seq_id.rsplit('_', 1)
                    if len(parts) > 1 and (parts[1].endswith('.fasta') or parts[1].endswith('.fa')):
                        filename = parts[1]
                    else:
                        filename = 'unknown.fasta'
                
                if filename not in file_groups:
                    file_groups[filename] = []
                file_groups[filename].append(seq)
            
            # Emit results
            self.emit.result("sequences", data={
                "sequences": sequences,
                "file_groups": file_groups,
                "total_count": len(sequences),
                "output_dir": self.output_dir
            })
            
            return True
            
        except Exception as e:
            self.emit.log("error", f"Failed to load results: {str(e)}")
            traceback.print_exc()
            return False
    
    def run_dl_clustering(self) -> bool:
        """Run deep learning-based clustering on CDR3 sequences."""
        if not DL_CLUSTERING_AVAILABLE:
            self.emit.log("info", "Deep learning clustering not available, skipping")
            return False
        
        self.emit.progress("dl_clustering", 98, "Running deep learning clustering...")
        
        try:
            import pandas as pd
            from Bio import SeqIO
            
            # Use HuggingFace pre-trained DNABERT-2 model
            # The local finetuned model is incomplete (only .part file)
            model_name = "zhihan1996/DNABERT-2-117M"
            
            self.emit.log("info", f"Using DNABERT-2 model: {model_name}")
            self.emit.log("info", "Note: First run will download the model (~500MB)")
            
            # Get sequences from combined.fasta
            if not os.path.exists(self.combined_fasta):
                self.emit.log("warn", "Combined FASTA not found, skipping DL clustering")
                return False
            
            # Read sequence IDs and CDR3 sequences from clonality output
            clone_pass_path = os.path.join(self.output_dir, 'ig_out_data_db-pass_clone-pass_germ-pass.tsv')
            if not os.path.exists(clone_pass_path):
                self.emit.log("warn", "Clonality output not found, skipping DL clustering")
                return False
            
            # Load clonality data
            clonality_df = pd.read_table(clone_pass_path)
            
            # Extract sequences with CDR3 data
            sequences_with_ids = []
            for _, row in clonality_df.iterrows():
                if pd.notna(row.get('junction')) and row.get('junction'):
                    seq_id = str(row['sequence_id'])
                    cdr3_seq = str(row['junction'])
                    sequences_with_ids.append((seq_id, cdr3_seq))
            
            if not sequences_with_ids:
                self.emit.log("warn", "No CDR3 sequences found for DL clustering")
                return False
            
            self.emit.log("info", f"Running DL clustering on {len(sequences_with_ids)} sequences...")
            
            # Run DL clustering
            cluster_mapping = dl_clustering.run_dl_clustering(
                sequences_with_ids,
                model_dir=model_name,  # HuggingFace model name
                threshold=0.00015,  # Default threshold from demo
                distance_type='cosine'
            )
            
            if not cluster_mapping:
                self.emit.log("warn", "DL clustering returned no results")
                return False
            
            # Get clone counts
            clone_counts = dl_clustering.get_clone_counts(cluster_mapping)
            
            # Create DL clustering results (same format as traditional results, but with DL clone IDs)
            dl_sequences = []
            for seq_id, dl_clone_id in cluster_mapping.items():
                # Find the original sequence data
                original_seq = None
                for record in SeqIO.parse(self.combined_fasta, "fasta"):
                    if record.id == seq_id:
                        original_seq = record
                        break
                
                if not original_seq:
                    continue
                
                # Get data from clonality file
                seq_clonality_data = clonality_df[clonality_df['sequence_id'] == seq_id]
                
                seq_record = {
                    'id': seq_id,
                    'name': seq_id,
                    'v_gene': None, 'd_gene': None, 'j_gene': None,
                    'v_locus': None, 'd_locus': None, 'j_locus': None,
                    'cdr3_dna': None, 'cdr3_peptide': None, 'somatic_mutations': None,
                    'isotype': None,
                    'clone_id': dl_clone_id,
                    'clone_count': clone_counts.get(seq_id, 0),
                    'productive': True
                }
                
                # Copy CDR3 and other data from clonality output
                if not seq_clonality_data.empty:
                    row = seq_clonality_data.iloc[0]
                    seq_record['cdr3_dna'] = str(row['junction']) if pd.notna(row['junction']) else None
                    seq_record['cdr3_peptide'] = str(row['junction_aa']) if pd.notna(row['junction_aa']) else None
                    seq_record['v_gene'] = str(row['v_call']) if pd.notna(row.get('v_call')) else None
                    seq_record['d_gene'] = str(row['d_call']) if pd.notna(row.get('d_call')) else None
                    seq_record['j_gene'] = str(row['j_call']) if pd.notna(row.get('j_call')) else None
                
                dl_sequences.append(seq_record)
            
            # Group DL sequences by file (same logic as traditional clustering)
            file_groups = {}
            for seq in dl_sequences:
                seq_id = seq['id']
                
                # Split by the ||| delimiter
                if '|||' in seq_id:
                    parts = seq_id.split('|||')
                    filename = parts[-1] if len(parts) > 1 else 'unknown.fasta'
                else:
                    # Fallback for old format
                    parts = seq_id.rsplit('_', 1)
                    if len(parts) > 1 and (parts[1].endswith('.fasta') or parts[1].endswith('.fa')):
                        filename = parts[1]
                    else:
                        filename = 'unknown.fasta'
                
                if filename not in file_groups:
                    file_groups[filename] = []
                file_groups[filename].append(seq)
            
            # Emit DL clustering results
            self.emit.result("dl_sequences", data={
                "sequences": dl_sequences,
                "file_groups": file_groups,
                "total_count": len(dl_sequences)
            })
            
            self.emit.log("info", f"DL clustering complete: {len(dl_sequences)} sequences, {len(file_groups)} file groups")
            return True
            
        except Exception as e:
            self.emit.log("warn", f"DL clustering failed: {str(e)}")
            self.emit.log("debug", traceback.format_exc())
            return False
    
    def run(self) -> bool:
        """Execute the full analysis pipeline."""
        try:
            self.emit.log("info", "🚀 PIPELINE STARTING - Check logs for tree building messages")
            
            # Step 1: Load FASTA files
            if not self.load_fasta_files():
                self.emit.complete(False, "Failed to load FASTA files")
                return False
            
            if self.check_cancelled():
                self.emit.complete(False, "Cancelled by user")
                return False
            
            # Step 2: Clean FASTA files if requested
            if not self.clean_fasta_files():
                self.emit.complete(False, "Failed to clean FASTA files")
                return False
            
            # Step 3: Setup databases
            if not self.setup_databases():
                self.emit.complete(False, "Failed to setup databases")
                return False
            
            # Step 4: Combine FASTA files
            if not self.combine_fasta_files():
                self.emit.complete(False, "Failed to combine FASTA files")
                return False
            
            # Step 5: Build BLAST databases
            if not self.build_blast_databases():
                self.emit.complete(False, "Failed to build BLAST databases")
                return False
            
            if self.check_cancelled():
                self.emit.complete(False, "Cancelled by user")
                return False
            
            # Step 6: Run IgBLAST
            if not self.run_igblast():
                self.emit.complete(False, "IgBLAST analysis failed")
                return False
            
            # Step 7: Calculate threshold
            threshold = self.calculate_threshold()
            if threshold is None or self.check_cancelled():
                self.emit.complete(False, "Cancelled by user")
                return False
            
            # Step 8: Run clonality analysis
            if not self.run_clonality_analysis(threshold):
                self.emit.complete(False, "Clonality analysis failed")
                return False
            
            if self.check_cancelled():
                self.emit.complete(False, "Cancelled by user")
                return False
            
            # Step 9: Build trees
            self.emit.log("info", "About to call build_trees()...")
            if not self.build_trees():
                self.emit.log("warn", "build_trees() returned False - continuing anyway")
            
            # Step 10: Visualize trees
            self.emit.log("info", "About to call visualize_trees()...")
            if not self.visualize_trees():
                self.emit.log("warn", "visualize_trees() returned False - continuing anyway")
            
            # Step 11: Load and emit results
            if not self.load_results():
                self.emit.complete(False, "Failed to load results")
                return False
            
            # Step 12: Run deep learning clustering (DISABLED - uncomment to enable)
            # self.run_dl_clustering()
            
            self.emit.progress("complete", 100, "Analysis complete!")
            self.emit.complete(True)
            return True
            
        except Exception as e:
            self.emit.log("error", f"Pipeline failed: {str(e)}")
            traceback.print_exc()
            self.emit.complete(False, str(e))
            return False


def run_public_clone_analysis(config: Dict[str, Any], emit) -> bool:
    """
    Run public clone analysis on existing results.
    
    Args:
        config: Configuration dictionary with analysis parameters
        emit: NDJSONEmitter for output
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from utils.public_clones import analyze_public_clones
        from Bio import SeqIO
        
        output_dir = config.get('output_dir')
        mode = config.get('mode', 'lenient')
        similarity_threshold = config.get('similarity_threshold', 0.85)
        max_mismatches = config.get('max_mismatches', 2)
        top_n = config.get('top_n', 10)
        
        emit.log("info", f"Starting public clone analysis in {mode} mode")
        emit.progress("public_clones", 10, "Loading clonality data...")
        
        # Paths to existing data
        clone_pass_path = os.path.join(output_dir, 'ig_out_data_db-pass_clone-pass_germ-pass.tsv')
        combined_fasta = os.path.join(output_dir, 'combined.fasta')
        
        # Check if required files exist
        if not os.path.exists(clone_pass_path):
            emit.log("error", f"Clonality file not found: {clone_pass_path}")
            emit.complete(False, "Required clonality data not found. Please run main analysis first.")
            return False
        
        if not os.path.exists(combined_fasta):
            emit.log("error", f"Combined FASTA file not found: {combined_fasta}")
            emit.complete(False, "Required FASTA file not found. Please run main analysis first.")
            return False
        
        emit.progress("public_clones", 30, "Loading sequence metadata...")
        
        # Load sequence metadata (for file grouping)
        sequences_data = []
        for record in SeqIO.parse(combined_fasta, "fasta"):
            sequences_data.append({
                'id': record.id,
                'file': None  # Will be extracted from ID
            })
        
        emit.progress("public_clones", 50, "Analyzing public clones...")
        emit.log("info", f"Analyzing {len(sequences_data)} sequences with top_n={top_n}")
        
        # Run analysis
        results = analyze_public_clones(
            clone_pass_path,
            sequences_data,
            mode=mode,
            similarity_threshold=similarity_threshold,
            max_aa_mismatches=max_mismatches,
            top_n=top_n
        )
        
        emit.progress("public_clones", 90, "Generating visualization data...")
        
        # Emit results
        emit.result('public_clones', data=results)
        
        stats = results.get('stats', {})
        emit.log("info", f"Found {stats.get('total_public_clones', 0)} public clones across {stats.get('total_patients', 0)} patients")
        
        emit.progress("public_clones", 100, "Public clone analysis complete!")
        emit.complete(True)
        return True
        
    except Exception as e:
        emit.log("error", f"Public clone analysis failed: {str(e)}")
        emit.log("debug", traceback.format_exc())
        emit.complete(False, str(e))
        return False


def main():
    """Main entry point."""
    emit = NDJSONEmitter
    
    emit.log("info", "Pipeline runner started")
    
    try:
        # Read configuration from stdin
        config_line = sys.stdin.readline()
        if not config_line:
            emit.complete(False, "No configuration received")
            return 1
        
        config = json.loads(config_line)
        
        action = config.get('action')
        
        if action == 'run':
            runner = PipelineRunner(config.get('config', {}))
            success = runner.run()
            return 0 if success else 1
        elif action == 'public_clones':
            # Run public clone analysis on existing results
            success = run_public_clone_analysis(config.get('config', {}), emit)
            return 0 if success else 1
        else:
            emit.complete(False, f"Unknown action: {action}")
            return 1
            
    except json.JSONDecodeError as e:
        emit.complete(False, f"Invalid JSON configuration: {str(e)}")
        return 1
    except Exception as e:
        emit.log("error", f"Fatal error: {str(e)}")
        traceback.print_exc()
        emit.complete(False, str(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())

