#!/usr/bin/env python3
'''
Script to convert a .pmd file to .html using pweave.

We cannot use the pweave command line tool since local imports does not work
with it.
'''

import argparse
import os
import pweave
import sys


def main(args):
    # Add current directory to the list of import locations
    sys.path.insert(0, os.getcwd())

    filename = os.path.abspath(args.file)

    # Change directory to output directory so that extra generated files will be
    # there
    os.chdir(os.path.dirname(filename))

    pweave.weave(filename, informat='markdown', doctype='md2html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str)

    args = parser.parse_args()
    main(args)
