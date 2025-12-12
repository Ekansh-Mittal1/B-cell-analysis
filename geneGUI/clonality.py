from code import clonalityFunctions
import subprocess


DIST = 0


def generate_db_dist(j, v, d, fasta):
    global DIST

    clonalityFunctions.make_db("ig_out_data.fmt7", j, v, d, fasta)
    DIST = clonalityFunctions.findDist("ig_out_data_db-pass.tsv")
    #will return a new clone and display
#this is when the window pops up
def finish_clonality(j, v, d, fasta, dist):
    clonalityFunctions.define_clonality("ig_out_data_db-pass.tsv" , dist)
    clonalityFunctions.create_germline("ig_out_data_db-pass_clone-pass.tsv", v, d, j)

def get_dist():
    global DIST
    return DIST

#displays the distrobution plot image
def display_Image():
    clonalityFunctions.showImage()

