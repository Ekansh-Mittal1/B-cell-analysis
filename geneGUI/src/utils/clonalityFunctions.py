import subprocess
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import sys
import os

# Get outs directory path - go up to geneGUI directory
geneHome = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
outs_dir = os.path.join(geneHome, "outs")


def make_db(i, rj, rv, rd, s):
    # MakeDb.py creates output in current directory, so change to outs_dir
    original_cwd = os.getcwd()
    try:
        os.chdir(outs_dir)
        # Use relative paths from outs_dir
        i_rel = os.path.relpath(i, outs_dir) if os.path.isabs(i) else i
        cmd = ['MakeDb.py', 'igblast', '-i', i_rel, '-r', rj, rv, rd, '-s', s]
        print(cmd)
        command = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output = command.communicate()[0]
    finally:
        os.chdir(original_cwd)
    
def define_clonality(db, dist, act='set', model='ham', norm='len'):
    # DefineClones.py creates output in current directory, so change to outs_dir
    original_cwd = os.getcwd()
    try:
        os.chdir(outs_dir)
        # Use relative path from outs_dir
        db_rel = os.path.relpath(db, outs_dir) if os.path.isabs(db) else db
        #nproc
        cmd = ['DefineClones.py', '-d', db_rel, '--act', act, '--model', model, '--norm', norm, '--dist', dist]
        command = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
        output = command.communicate()[0]
        print(output)
    finally:
        os.chdir(original_cwd)

def showImage(pathToPlot=None):
    if pathToPlot is None:
        pathToPlot = os.path.join(outs_dir, "distributionPlot.png")
    img = mpimg.imread(pathToPlot)
    plt.imshow(img)
    plt.show()

def create_germline(db, v, d, j):
    # CreateGermlines.py creates output in current directory, so change to outs_dir
    original_cwd = os.getcwd()
    try:
        os.chdir(outs_dir)
        # Use relative path from outs_dir
        db_rel = os.path.relpath(db, outs_dir) if os.path.isabs(db) else db
        cmd = ['CreateGermlines.py', '-d', db_rel, '-r', v, d, j, '-g', 'dmask', '--cloned' ]
        command = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
        output = command.communicate()[0]
        print(output)
    finally:
        os.chdir(original_cwd)



def findDist(dbPath, pathToScript=None, pathToPlot=None):
    if pathToScript is None:
        pathToScript = os.path.join(geneHome, "src", "scripts", "calculateDistribution.R")
    if pathToPlot is None:
        pathToPlot = os.path.join(outs_dir, "distributionPlot.png")
    command = 'Rscript'
    args = [dbPath, pathToPlot]
    cmd = [command, pathToScript] + args
    try:
        output = subprocess.check_output(cmd, shell=False)

        distribution = float(str(output)[6:-3])

        return distribution
    except subprocess.CalledProcessError as e:
        print(e.returncode)
        print(e.output)