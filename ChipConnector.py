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
# limitations under the License.from SocOnlineHParser import *
from JTAGWrapper import *
import pickle
import struct

class ChipConnector :
    def __init__(self,path_to_soc_file):
        # load chip model from the Soconline C file
        self.model = parse(path_to_soc_file)
        self.is_connected = False

    def connect_board(self):
        # connect to the board
        try:
            self.jtag_wrapper = JTAGWrapper()
            self.jtag_wrapper.connect()
            self.is_connected = True
        except SystemError, err:
            self.is_connected = False
            return err.message



    def read_model_from_board(self):
        self.iterate_all_registers(self.read_reg)

    def write_model_to_board(self):
        self.iterate_all_registers(self.write_reg)

    def read_reg(self,register):
        self.jtag_wrapper.read_reg(register)

    def write_reg(self,register):
        self.jtag_wrapper.write_reg(register)

    # def write_reg_by_name(self,name,value):
    #      for block in self.model.blocks:
    #         for register in block.registers:
    #             if (register.name == name):
    #                 register.set_raw_val(value)
    #                 self.jtag_wrapper.write_reg(register)

    def update_reg_by_name(self,block_name,reg_name,reg_val):
        updated = -1
        block = self.model.block_by_name(block_name)
        if not(block):
            return -1
        register = block.register_by_name(reg_name)
        if not(register):
            return -1
        register.set_raw_val(reg_val)
        return 0


    def iterate_all_registers(self,func):
        for block in self.model.blocks:
            for register in block.registers:
                func(register)


    def get_save_line(self,register):
        return "%s,0x%X"%(register.name,register.get_raw_val())

    def save_block_on_disk(self,block,filename):
        fh = open(filename,"a")
        for register in block.registers:
            fh.write(block.name + "," + self.get_save_line(register) + "\n")
        fh.close()


    def save_model_on_disk(self,filename):
        fh = open(filename,"w")
        for block in self.model.blocks:
            for register in block.registers:
                fh.write(block.name + "," + self.get_save_line(register) + "\n")
        fh.close()

    def load_model_from_disk(self,filename):
        fh = open(filename,"r")
        for line in fh.readlines():
            block_name, reg_name, reg_value = line.split(",")
            res = self.update_reg_by_name(block_name,reg_name,int(reg_value,16))
            if res != 0:
                return res

    def load_bin_file_to_address(self,memory_addr,filename):
        res = self.jtag_wrapper.file2mem(memory_addr,filename)
        return res

    def dump_bin_file_from_address(self,memory_addr,size_bytes,filename):
        res = self.jtag_wrapper.mem2file(memory_addr,size_bytes,filename)
        return res

    def detach(self):
        self.jtag_wrapper.detach()

    def download_firmware(self,filename):
        self.jtag_wrapper.download_firmware(filename)


if __name__ == "__main__":
    model = ChipConnector("omic_ARC.h")
    # model.read_model_from_board()
    model.save_model_on_disk("reg_dump.csv")
    model.load_model_from_disk("reg_dump.csv")
    # print model.model.blocks[0].registers
