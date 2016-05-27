import struct
import os
import sys


if __name__ == "__main__":
    values = []
    fh = open(sys.argv[1],"rb")
    try:
        ushort = fh.read(2)
        while ushort:
            val = struct.unpack("<H",ushort)[0]
            values.append(val)

            ushort = fh.read(2)

    finally:
        fh.close()
        i=0
        print "Got %d values in the binary"%len(values)
        csv_fh = open(os.path.basename(sys.argv[1]).split(".")[0] + ".txt",'w')
        for val in values:
            csv_fh.write("%d\t%d\n"%(i,val))
            i += 1
        csv_fh.close()



