import subprocess
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import sys


def make_db(i, rj, rv, rd, s):
    cmd = ['MakeDb.py', 'igblast', '-i', i, '-r', rj, rv, rd, '-s', s]
    print(cmd)
    command = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output = command.communicate()[0]
    
def define_clonality(db, dist, act='set', model='ham', norm='len'):
    #nproc
    cmd = ['DefineClones.py', '-d', db, '--act', act, '--model', model, '--norm', norm, '--dist', dist]
    command = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
    output = command.communicate()[0]
    print(output)

def showImage(pathToPlot="code/distributionPlot.png"):
    img = mpimg.imread(pathToPlot)
    plt.imshow(img)
    plt.show()

def create_germline(db, v, d, j):
    cmd = ['CreateGermlines.py', '-d', db, '-r', v, d, j, '-g', 'dmask', '--cloned' ]
    command = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
    output = command.communicate()[0]
    print(output)



def findDist(dbPath, pathToScript="code/calculateDistribution.R", pathToPlot="code/distributionPlot.png"):
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