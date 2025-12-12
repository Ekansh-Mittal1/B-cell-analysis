import glob
from setuptools import setup
import os

home = os.path.dirname(os.path.abspath(__file__))
APP = ['main.py']
DATA_FILES = ["menu.ui", "main.ui", "clean.py", "cells.icns",
                ('clean_db_files', glob.glob('clean_db_files/')),
                ('bin', glob.glob('bin/')), "clonality.py", 
                "blast.py", ('code', glob.glob('code/')), 
                ('optional_data', glob.glob('optional_data/')), 
                "ig_out_data.fmt7", ('internal_data', glob.glob('internal_data/')),
                ('Database-Files', glob.glob('Database-Files/')), "clean_fasta", 
                "progress.ui"]


OPTIONS = {'iconfile':'cells.icns'}
setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'], 
    install_requires=['PyQt6', 'qdarkstyle', 'tabulate', 'pandas', 'biopython', 'changeo']
)