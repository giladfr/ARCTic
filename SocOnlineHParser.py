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
import math
from ChipModel import *

BLOCK_OPEN = '<Expander Margin="5" DockPanel.Dock="Top">\n<Expander.Header>%s</Expander.Header>\n<StackPanel>'
BLOCK_CLOSE = '</StackPanel>\n</Expander>'
REGISTER_OPEN = '<GroupBox Header="%s [0x%06X]" Margin="10,10,0,0"><StackPanel>'
REGISTER_CLOSE = '</StackPanel></GroupBox>'
XAML_LINE = '<my:RegisterFieldControl FieldName="%s" RegAddress="%s" FieldOffset="%d" FieldWidth="%d" Margin="3"/>'
CSV_LINE = '%s,%s,%s,%s,%s'



def parse(in_file_name):
    in_fh = open(in_file_name)
    chip_model = ChipModel()
    cur_reg = None
    cur_block = None

    for line_num,line in enumerate(in_fh.readlines()):
        # print line
        if line.startswith("}"):
            cur_reg = None

        if cur_reg:
            if line.startswith("	unsigned"):
                field_name = line.split(" ")[1].upper()
                field_width = int(line.split(" ")[2].lstrip(":").rstrip(";\n"))
                if not field_name.startswith("RSV"):
                    cur_reg.add_field(Field(field_name,cur_offset,field_width))
                cur_offset += field_width


        if line.startswith("#define"):
            if "MEMORY" in line:
                module_name = cur_reg_str.replace("_MODULE","")
                name_full  = line.split(" ")[1]
                num = line.split(" ")[2]
                mem_name = name_full.partition("_")[2].rpartition("_")[0]
                memory_module = chip_model.add_mem_module(module_name)
                if name_full.endswith("ADDR"):
                    # Create a memory for the chip
                    new_memory = Memory(module_name,mem_name,int(num,16),0)
                    memory_module.add_memory(new_memory)
                elif name_full.endswith("SIZE"):
                    # this is the next line, add to the last new memory
                    new_memory.size = int(num)
                    new_memory = ""

                print "Memory: %s ; %s" % (module_name,mem_name)

                continue

            if "MODULE_ADDR" in line:
                # block offset line, usually is in the end of the file so we need to fix the register addresses afterwards
                block_name = line.split(" ")[1].partition("_")[0]
                block_offset = line.split("  ")[-1].lstrip("(").rstrip(")\n")
                block_to_fix = chip_model.block_by_name(block_name)
                if block_to_fix:
                    block_to_fix.offset = int(block_offset,16)

                else : # if it's not a block, find and fix the relevant memories
                    mem_module_name = line.split(" ")[1].partition("_")[2].rpartition("_MODULE")[0]
                    for memory_module in chip_model.memory_modules:
                        if memory_module.name == mem_module_name:
                            for memory in memory_module.memories:
                                memory.address += int(block_offset,16)
            else:
                # Add a new register to a register block
                block_name = line.split(" ")[1].split("_")[0]
                block = chip_model.add_block(block_name)
                register_name = line.split(" ")[1].partition("_")[2].rpartition("_")[0]
                register_address = line.split("  ")[1].lstrip("(").strip(")\n")
                new_reg = Register(register_name, register_address)
                block.add_register(new_reg)
                print "Block: %s ; %s" % (block_name,new_reg)
                cur_block = block

        if line.startswith("typedef"):  # and not line.find("MODULE"):
            cur_reg_str = line.split(" ")[2].lstrip("_")
            cur_reg_str = cur_reg_str.replace(cur_block.name,"",1)
            cur_reg_str = cur_reg_str.partition("_")[2]
            cur_reg_str = cur_reg_str.rpartition("_")[0]

            if cur_reg_str != "MODULE":
                cur_reg = cur_block.register_by_name(cur_reg_str)
                cur_offset = 0
                # find the register

    # Fix all the offset of all the registers by the block offset
    for block in chip_model.blocks:
        for register in block.registers:
            register.address_int += block.offset
            register.address = "0x%X" % register.address_int

    in_fh.close()
    return chip_model


def write_xaml(chip):
    out_fh = open(os.path.basename(in_file_name) + "_XAML.txt", "w")

    for block in chip.blocks:
        out_fh.write(BLOCK_OPEN % block.name + "\n")
        for register in block.registers:
            out_fh.write(REGISTER_OPEN % (register.name,register.address_int) + "\n")
            for field in register.fields:
                out_fh.write(XAML_LINE % (field.name,register.address,field.offset,field.width) + "\n")
            out_fh.write(REGISTER_CLOSE + "\n")
        out_fh.write(BLOCK_CLOSE + "\n")


    out_fh.close()

def write_fields_CSV(chip):
    out_fh = open(os.path.basename(in_file_name) + ".csv", "w")
    out_fh.write("Reg Name,Reg Address,Field Name,Offset,Width,Value\n")
    for block in chip.blocks:
        for register in block.registers:
            for field in register.fields:
                out_fh.write(CSV_LINE % (register.name,register.address,field.name,field.offset,field.width) + "\n")








if __name__ == '__main__':
    in_file_name = sys.argv[1]
    chip = parse(in_file_name)
    write_xaml(chip)
    write_fields_CSV(chip)
