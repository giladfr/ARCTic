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
import math

class Field():
    def __init__(self, name, offset, width, value = 0):
        self.name = name
        self.offset = offset
        self.width = width
        self.value = value & int(math.pow(2,width) - 1)

    def __repr__(self):
        return "Name = %s ; Offset = %d ; width = %d ; value = %d" %(self.name,self.offset,self.width,self.value)


class Register():
    def __init__(self, name, address):
        self.name = name
        self.address = address
        self.address_int = int(address, 16)
        self.fields = []

    def add_field(self, field):
        self.fields.append(field)

    def set_raw_val(self,val_int):
        for field in self.fields:
            mask = int((math.pow(2,field.width) - 1)) << field.offset
            field.value = (val_int & mask) >> field.offset

    def get_raw_val(self):
        raw_val = 0
        for field in self.fields:
            raw_val |= (field.value << field.offset)
        return raw_val

    def __repr__(self):
        return "Reg Name = %s ; Address = 0x%X; Value = 0x%X" %(self.name,self.address_int,self.get_raw_val())



class RegisterBlock():
    def __init__(self, name):
        self.name = name
        self.registers = []
        self.offset = 0

    def add_register(self, reg):
        self.registers.append(reg)

    def register_by_name(self,name):
        registers = filter(lambda x: x.name == name, self.registers)
        if registers == []:
            return None
        else:
            return registers[0]

    def __repr__(self):
        return "Name = %s" % self.name


class Memory():
    def __init__(self,memblock_name,name,addr,size):
        self.name = name
        self.address = addr
        self.size = size

class MemoryModule():
    def __init__(self,name):
        self.name = name
        self.memories = []

    def add_memory(self,memory):
        self.memories.append(memory)

    def memory_by_name(self,name):
        memories = filter(lambda x: x.name == name, self.memories)
        if memories == []:
            return None
        else:
            return memories[0]

class ChipModel():
    def __init__(self):
        self.blocks = []
        self.memory_modules = []

    def add_block(self, name):
        ext_blocks = self.block_by_name(name)
        if ext_blocks:
            return ext_blocks
        else:
            new_block = RegisterBlock(name)
            self.blocks.append(new_block)
            return new_block

    def add_mem_module(self,name):
        ext_mem_module = self.mem_module_by_name(name)
        if ext_mem_module:
            return ext_mem_module
        else:
            new_mem_module = MemoryModule(name)
            self.memory_modules.append(new_mem_module)
            return new_mem_module

    def block_by_name(self, name):
        blocks = filter(lambda x: x.name == name, self.blocks)
        if blocks == []:
            return None
        else:
            return blocks[0]

    def mem_module_by_name(self,name):
        modules = filter(lambda x: x.name == name, self.memory_modules)
        if modules == []:
            return None
        else:
            return modules[0]

