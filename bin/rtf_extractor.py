#!/usr/bin/env python2
import sys
import os
from pyth.plugins.rtf15.reader import Rtf15Reader
from pyth.plugins.plaintext.writer import PlaintextWriter

# used by pipelines to parse rtf files
# requires python2

def main():
    if len(sys.argv) < 2:
        print("usage %s <rtf_file_name> <txt_file_name>")
    else:
        doc = Rtf15Reader.read(open(os.path.join(sys.argv[1])))
        txt_filename = sys.argv[2]
        with open(os.path.join(txt_filename), "w") as of:
            of.write(PlaintextWriter.write(doc).getvalue())


if __name__ == '__main__':
    main()
