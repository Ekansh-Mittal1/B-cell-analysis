import sys
import subprocess
import pandas as pd
from io import StringIO
import warnings
import numpy as np
from Bio import SeqIO
import os


def blast_get_top_hits_v(input_fp, db_V_fp, db_J_fp, db_D_fp, organism='human', bin_dir=None, data_dir=None, output_dir=None):
    """
    Function that parses the hits table from blastp (bin/igblast(p/n)) into pandas dataframe. The hits table shows the top 3 hits (default) of the germline seuqences that are with highest identity % to the query seuqence.
    :param input_fp: string, file path of the input fasta file
    :param db_V_fp: string, file path of the V gene database
    :param db_J_fp: string, file path of the J gene database
    :param db_D_fp: string, file path of the D gene database
    :param organism: string, optional, default = human
    :param bin_dir: string, optional, path to bin directory (if None, will calculate)
    :param data_dir: string, optional, path to data directory (if None, will calculate)
    :param output_dir: string, optional, path to output directory (if None, will calculate)
    :return: a tuple of (df, output data)
    """
    # Calculate paths if not provided
    if bin_dir is None or data_dir is None or output_dir is None:
        # Get the geneGUI directory path - go up from backend/utils to geneGUI
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        geneHome = os.path.join(backend_dir, '..', 'geneGUI')
        geneHome = os.path.abspath(geneHome)
        
        if bin_dir is None:
            bin_dir = os.path.join(geneHome, 'bin')
        if data_dir is None:
            data_dir = os.path.join(geneHome, 'data')
        if output_dir is None:
            output_dir = os.path.join(geneHome, 'outs')
    else:
        geneHome = os.path.dirname(bin_dir) if bin_dir else os.path.dirname(data_dir)
    
    #runs the igblastn command
    igblastn_path = os.path.join(bin_dir, 'igblastn')
    aux_data_path = os.path.join(data_dir, 'optional_data', 'human_gl.aux')
    # IGDATA should point to the parent directory containing 'internal_data' folder
    igdata_path = data_dir
    # Set IGDATA environment variable so igblastn can find internal_data
    env = os.environ.copy()
    env['IGDATA'] = igdata_path
    cmd = [igblastn_path, '-germline_db_V', db_V_fp, '-germline_db_D', db_D_fp, '-germline_db_J', db_J_fp,'-query', input_fp, '-outfmt', '7 std qseq sseq btop', '-auxiliary_data', aux_data_path]#, '-out', 'ig_out_data.fmt7', "-organism", organism]
    a = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=geneHome, env=env)
    out = a.communicate()[0].decode('utf-8')
    b = StringIO(out)
    # parse output into string
    all_data = [x.strip() for x in str(b.getvalue()).split('#')]

    fmt7_path = os.path.join(output_dir, "ig_out_data.fmt7")
    with open(fmt7_path, "w") as txt_file:
        txt_file.write(out)

    # the hit table is the 2nd from the last in the list above.

    hits=[]
    for line in all_data:
        if 'hits found' in line:
            hits+=line.split('\n')[1:]
        if("Query: " in line):
            cur_query = line[7:]
        if("Sub-region sequence details" in line):
            dna, prot = line.split('\n')[1].split('\t')[1:3]
        if("CDR3-IMGT" in line):
            somatic_mutations = 0
            d = line.split("\n")
            for s in d:
                if("Total" in s):
                    somatic_mutations = int(s.split()[5])
            x = ("CDR3\t" + cur_query + '\t' + dna+ "\t" + prot + "\t" + str(somatic_mutations) + "\n")
            hits.append(x)

    #default fields
    fields = 'chain type\tquery id\tsubject id\t% identity\talignment length\tmismatches\tgap opens\tgaps\tq.start\tq.ends\t s.start\ts.end\tevalue\tbit score\tquery seq\tsubject seq\tBTOP'

    # add col header
    hits.insert(0, fields)
    # parse into df
    #print('\n'.join(hits))
    data = StringIO('\n'.join(hits))
    df = pd.read_csv(data, sep='\t')
    csv_path = os.path.join(output_dir, 'out.csv')
    df.to_csv(csv_path)
    # get df, the best matching germline allele & identity
    return df, out
    #except:
      #  print('None of the seuqenced you provided in the fasta file ')
       # return None, None, None


# Test call removed - uncomment below to test locally
# blast_get_top_hits_v("fasta_files/1018.fasta", "Database-Files/IGHV_clean.fasta", "Database-Files/IG_HKL_J_clean.fasta", "Database-Files/IGHD_clean.fasta")