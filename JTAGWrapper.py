# Copyright 2016 Gilad Fride
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys
import subprocess
import time
from SocOnlineHParser import *

_debug = True
mdb_connection_command = "mdb -cl -toggle=include_local_symbols=1 -off=download -connect_only -profile -digilent  -prop=jtag_chain=A8"

class JTAGWrapper:
    def __init__(self):
        self.mdb_proc = ""
        self.is_connected = False
        self.path_to_mdb = self._find_mdb()
        if not os.path.exists(self.path_to_mdb):
            raise SystemError("Can't find MDB, please install Metaware")

    def connect(self):

        if not self.is_connected:
            working_dir = os.path.dirname(self.path_to_mdb)
            self.mdb_proc = subprocess.Popen(mdb_connection_command,
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=working_dir ,
                            )
            # time.sleep(1)
            self.mdb_proc.stdin.write('JJ\n')
            output = ""
            line = ""
            while (line.find('Not a valid command') == -1):
                line = self.mdb_proc.stdout.readline()
                if _debug: print "JTAG Connect: " + line.strip()
                if (line.find("[DIGILENT] Could not open device") != -1):
                    self.detach()
                    raise SystemError("Can't find Digilent cable, please make sure it's connected")
                if (line.find("expired") != -1):
                    self.detach()
                    raise SystemError("Problem loading metaware debugger, please check license")
                if (line.find("JTAG failed") != -1):
                    self.detach()
                    raise SystemError("JTAG failed after 10 attempts;")

                output += line
            self.is_connected = True



    def _exec_command(self,command):
        print "Executing: " + command
        self.mdb_proc.stdin.write(command + '\n')
        self.mdb_proc.stdin.write('JJ\n')
        time.sleep(0.05)
        output = ""
        line = ""
        while (line.find('Not a valid command') == -1):
            if _debug: print "JTAG raw: " + line.strip()
            output += line
            line = self.mdb_proc.stdout.readline()

        # Clean up the output to leave only the relevant data
        cleaned_output = output.replace("mdb> ","").rstrip()
        return cleaned_output


    def write_addr32(self, addr, val):
        output = self._exec_command("/ui emem 0x%x 0x%x" %(addr,val) )


    def read_addr32(self, addr):
        output = self._exec_command("eval *0x%x" %addr )
        # result is in the form of -  "int  (*0x0) = -889271554 (0xcafecafe)"
        reg_value_hex_str = output.split(" ")[-1].lstrip("(").rstrip(")")
        reg_value_hex = int(reg_value_hex_str,16)
        return reg_value_hex


    def write_reg(self,register):
        "Write a register value to the board using JTAG"
        self.write_addr32(register.address_int,register.get_raw_val())

    def read_reg(self,register):
        "Read a register value and update it to the register object using JTAG"
        register.set_raw_val(self.read_addr32(register.address_int))

    def mem2file(self,addr,size_bytes,file_path):
        cmd = "mem2file " + "0x%x" % addr + " " +  str(size_bytes) + " " + file_path
        output = self._exec_command(cmd)
        return output

    def file2mem(self,addr,file_path):
        cmd = "file2mem " + "0x%x "%addr + file_path
        output = self._exec_command(cmd)
        time.sleep(0.1)
        return output


    def _find_mdb(self):
        # Fixed path - fix working with env var
        metaware_root = os.environ.get("METAWARE_ROOT")
        return os.path.join(metaware_root,"arc\\bin\\mdb.exe")

    def test(self):
        print self._exec_command('mem')

    def detach(self):
        self.mdb_proc.stdin.write('continue -detach' + '\n')
        # time.sleep(1)
        self.mdb_proc.stdin.write('exit' + '\n')
        self.mdb_proc.terminate()
        self.is_connected = False

    def download_firmware(self,filename):
        command = "kill\non=download\nload " + filename
        self._exec_command(command)






if __name__ == "__main__":
    print "JTAGWrapper Tester"
    jtag_wrapper = JTAGWrapper()
    jtag_wrapper.connect()
    jtag_wrapper.test()
  
