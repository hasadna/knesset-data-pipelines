#!/usr/bin/env python2
import sys
import os
from pyth.plugins.rtf15.reader import Rtf15Reader
from pyth.plugins.plaintext.writer import PlaintextWriter



def main():
	if len(sys.argv) < 2:
		print "usage %s <data_folder>"
	else:
		for root, dirs, files in os.walk(sys.argv[1]):
			for filename in files:
				if  os.path.splitext(filename)[1] == ".rtf":
					try:
						doc = Rtf15Reader.read(open(os.path.join(root,filename)))
						txt_filename = os.path.splitext(filename)[0] + ".txt"
						with open (os.path.join(root,txt_filename),"w") as of:
							of.write(PlaintextWriter.write(doc).getvalue())
					except:
						continue



if __name__ == '__main__':
	main()