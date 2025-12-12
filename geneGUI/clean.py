import pandas
import re
import sys
import os


def clean_imgt(in_path, out_path):

    in_file = open(in_path, 'r')
    out_file = open(out_path, "x")

    for line in in_file:
        if(line[0] == '>'):

            boundaries = list(find_all(line))
            germline_name = line[boundaries[0]+1: boundaries[1]]

            new_line = '>'+germline_name+'\n'
            out_file.write(new_line)
        else:
            out_file.write(line.replace(".",""))

    in_file.close()
    out_file.close()

def find_all(a_str, sub = '|', numToFind = 2):
    """
    Function that finds all occurences of a given character in a string
    :param a_str: string to search through
    :param sub:  char searching for
    :param numToFind: how many occurences of sub are we looking for
    """
    start = 0
    numFound = 0
    while (numFound < numToFind):
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        numFound += 1
        start += len(sub) # use start += 1 to find overlapping matches




