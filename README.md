# B-Cell Repertoire Analysis Tool

A comprehensive pipeline for analyzing B-cell receptor (BCR) repertoires from single-cell sequencing data (10x Genomics VDJ). Features include IgBLAST alignment, clone definition, phylogenetic tree building, and public clone identification across multiple samples.

## Features

- **IgBLAST Alignment**: Align sequences against IMGT germline databases
- **Clone Definition**: Identify clonal families using configurable parameters
- **Distance Threshold Calculation**: Automatic threshold detection with manual override
- **Phylogenetic Trees**: Build maximum likelihood trees for top clones using IQ-TREE2
- **Public Clone Analysis**: Identify antibody clones shared across multiple patients
- **Modern UI**: Electron-based desktop application with real-time progress tracking

## Prerequisites

### Required Software

- **Node.js** 18+ and npm
- **Python** 3.9+
- **R** 4.0+
- **IgBLAST** (included in `geneGUI/bin/`)

### System Requirements

- macOS 10.15+ (Catalina or later)
- 8+ GB RAM recommended
- ~2 GB disk space for installation

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd B-cell-analysis
```

### 2. Install Node.js Dependencies

```bash
cd electron-app
npm install
```

This will install all JavaScript dependencies including Electron (~200 MB download).

### 3. Install Python Dependencies

```bash
pip3 install biopython pandas matplotlib
```

Install the Change-O toolkit (for DefineClones.py, MakeDb.py, etc.):

```bash
pip3 install changeo
```

Or follow the official installation guide: https://changeo.readthedocs.io/en/stable/install.html

### 4. Install R Packages

Open R and run:

```R
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

BiocManager::install("shazam")
```

### 5. Grant Permissions to IgBLAST Executables (macOS only)

On first run, macOS may block the IgBLAST executables. If prompted, go to **System Settings > Privacy & Security** and click "Allow Anyway" for each binary.

Alternatively, run once manually:
```bash
cd geneGUI/bin
./igblastn -version  # This will trigger the permission prompt
```

## Running the Application

### Development Mode

```bash
cd electron-app
npm run dev
```

This starts the app with hot-reload for development.

### Production Mode

```bash
cd electron-app
npm run build
npm start
```

### Building Distributable App

```bash
cd electron-app
npm run package:mac  # Creates .dmg and .zip in electron-app/release/
```

## Usage

### Basic Workflow

1. **Select Files**: Choose a directory containing 10x Genomics VDJ FASTA files
2. **Choose Database**: Use IMGT Human Database (default) or provide custom germline references
3. **Configure Clone Settings**: 
   - **V/J Mode**: `allele` (strict, recommended) or `gene` (permissive)
   - **Linkage Method**: `average` (recommended), `complete` (strictest), or `single` (most permissive)
4. **Review & Start**: Confirm settings and run the analysis
5. **Review Results**: Browse sequences, view phylogenetic trees, and analyze clones

### Clone Definition Parameters

The pipeline uses Change-O's DefineClones.py with these configurable parameters:

- **V/J Mode** (`--mode`):
  - `allele`: Requires exact allele matches (e.g., IGKV3-20*01)
  - `gene`: Groups all alleles of a gene (e.g., IGKV3-20*01, *02, *03)

- **Linkage Method** (`--link`):
  - `complete`: All sequences must be within threshold (strictest)
  - `average`: Average distance must be within threshold (recommended)
  - `single`: Any two sequences within threshold creates chain (most permissive)

- **Distance Threshold**: Automatically calculated or manually set (0.01-0.05 typical range)

### Understanding Clone Sizes

For 10x Genomics single-cell data:
- **Clone size** = number of individual B cells with related BCR sequences
- Large clones (100+ cells) indicate biological clonal expansion
- Each cell has a unique barcode, so technical duplicates are automatically excluded

## Project Structure

```
B-cell-analysis/
├── electron-app/          # Modern Electron UI
│   ├── src/
│   │   ├── main/          # Electron main process
│   │   ├── preload/       # Preload scripts
│   │   └── renderer/      # Svelte UI components
│   └── package.json
├── backend/               # Python pipeline
│   ├── pipeline_runner.py # Main pipeline orchestrator
│   ├── scripts/           # R scripts for trees and calculations
│   └── utils/             # Python utility modules
├── geneGUI/               # Legacy PyQt GUI (deprecated)
│   ├── bin/               # IgBLAST executables
│   └── data/              # IMGT reference databases
└── BCR_Deep_Clustering-main/  # Optional DL clustering (experimental)
```

## Troubleshooting

### "Cannot find DefineClones.py"

Make sure Change-O is installed and in your PATH:
```bash
which DefineClones.py
# Should show: /Users/<username>/Library/Python/3.x/bin/DefineClones.py
```

### "IgBLAST permission denied"

Grant execution permissions to binaries in `geneGUI/bin/`:
```bash
chmod +x geneGUI/bin/*
```

### Large Clone Sizes

Large clones (100-500 cells) are biologically normal for:
- Active immune responses
- Long COVID or chronic infections
- Memory B-cell expansions

See the pipeline logs for threshold calculations and clone definition parameters.

## Citation

This pipeline uses:
- **Change-O**: Gupta NT, et al. Change-O: a toolkit for analyzing large-scale B cell immunoglobulin repertoire sequencing data. Bioinformatics. 2015.
- **IgBLAST**: Ye J, et al. IgBLAST: an immunoglobulin variable domain sequence analysis tool. Nucleic Acids Res. 2013.
- **IQ-TREE**: Nguyen LT, et al. IQ-TREE: a fast and effective stochastic algorithm for estimating maximum-likelihood phylogenies. Mol Biol Evol. 2015.

## License

[Add your license here]

## Contact

[Add contact information]
