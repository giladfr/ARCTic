#!/usr/bin/env python
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

import gtk
import gobject
from threading import Thread
import struct
import time
import math
import ChipConnector
import glob
import os
import random
import filecmp
import pango
import re
import json





class MemoryTest:
    def __init__(self,chip_model):
        self.gladefile = "MemoryTest.glade"
        self.builder = gtk.Builder()
        self.builder.add_from_file(self.gladefile)
        self.chip_model = chip_model
        self.blocks_to_test = []
        self.memories_to_test = []

        self.to_stop_test = False
        try:
            os.mkdir("MemTest")
        except:
            pass



        # Connect callbacks
        handlers = {"on_startTestButton_clicked" : self.start_test_button,
                    "on_scrolledwindow2_size_allocate" : self.size_allocate,
                    "on_cancelButton_clicked" : self.cancel_button,
                    }

        self.builder.connect_signals(handlers)

        #Get the Main Window, and connect the "destroy" event
        self.window = self.builder.get_object("MemoryTest")
        self.spinner = self.builder.get_object("spinner1")
        # if (self.window):
        #     self.window.connect("destroy", gtk.main_quit)

        self.log_textbox = self.builder.get_object("logTextView")
        self.textbuffer = self.log_textbox.get_buffer()
        tag_table = self.textbuffer.get_tag_table()
        err_tag = gtk.TextTag("Error")
        err_tag.set_property("background", "red")
        err_tag.set_property("weight", pango.WEIGHT_BOLD)
        tag_table.add(err_tag)

        # Dynamically build the checkboxes for each block and memory region
        self.build_blocks_checkboxes()

        self.window.set_default_size(600,300)


        self.window.show_all()

    def load_config_from_json(self):
        try :
            fh = open("MemoryTest.json")
            parsed_json = json.loads(fh.read())
            fh.close()
            exclude_memories_re = parsed_json["Exclude memories"]

            exclude_fields_list_re = parsed_json["Exclude read only fields"]
            self.combined_fields_exclude_re = "(" + ")|(".join(exclude_fields_list_re) + ")"

            exclude_memories_re = parsed_json["Exclude memories"]
            if exclude_memories_re != []:
                self.combined_memories_exclude_re = "(" + ")|(".join(exclude_memories_re) + ")"
            else:
                self.combined_memories_exclude_re = "(?!)"

            mask_12bit_re = parsed_json["12 Bit Mask"]
            if mask_12bit_re != []:
                self.mask_12bit_re = "(" + ")|(".join(mask_12bit_re) + ")"
            else:
                self.mask_12bit_re = "(?!)"

            mask_16bit_re = parsed_json["16 Bit Mask"]
            if mask_16bit_re != []:
                self.mask_16bit_re = "(" + ")|(".join(mask_16bit_re) + ")"
            else:
                self.mask_16bit_re = "(?!)"

        except :
            self.combined_fields_exclude_re = "(?!)"
            self.combined_memories_exclude_re = "(?!)"
            self.mask_12bit_re = "(?!)"
            self.mask_16bit_re = "(?!)"






    # This is for getting auto scroll on the log textview
    def size_allocate(self, widget, data = None):
        adj = widget.get_vadjustment()
        adj.set_value( adj.upper - adj.page_size )

    def start_test_button(self, widget, data = None):
        # Add spinner
        self.spinner.start()
        # Run in a thread
        self.start_test_in_thread()

    def cancel_button(self, widget, data = None):
        self.to_stop_test = True

    def start_test_in_thread(self):
        Thread(target=self.start_test).start()

    def start_test(self):
        self.load_config_from_json()
        self.to_stop_test = False
        self.update_log_async("*" * 10 + " Starting Test " + "*"*10)
        num_failed_fields = 0
        num_failed_memories = 0

        # Test registers
        for block in self.blocks_to_test:
            if block == None:
                continue
            self.update_log_async("*" * 5 + " Testing Block : " + block.name)
            num_failed_fields += self.check_block(block)
            if self.to_stop_test:
                self.spinner.stop()
                return

        # Test memories
        for region in self.memories_to_test:
            if region == None:
                continue
            self.update_log_async("*" * 5 + " Testing Memory Region : " + region.name)
            num_failed_memories += self.check_memory_region(region)
            if self.to_stop_test:
                self.spinner.stop()
                return


        self.update_log_async("*" * 10 + " Finished Test " + "*"*10)
        self.update_log_async("%d Failed Fields\n%d Failed Memories" % (num_failed_fields,num_failed_memories))
        if ((num_failed_fields == 0) and (num_failed_memories == 0)):
            self.update_log_async("*" * 10 + "Test Passed" + "*"*10)
        else:
            self.update_log_async("*" * 10 + "Test Failed" + "*"*10,True)

        self.spinner.stop()

    def update_log_async(self,log_line,is_error = False):
        gobject.idle_add(self.update_log, log_line,is_error)

    def update_log(self,log_line,is_error):
        textbuffer = self.log_textbox.get_buffer()
        end_iter = textbuffer.get_end_iter()
        if is_error:
            textbuffer.insert_with_tags_by_name(end_iter, log_line + "\n","Error")
        else:
            textbuffer.insert(end_iter, log_line + "\n")


    def build_blocks_checkboxes(self):
        checkbox_viewport = self.builder.get_object("checkboxViewPort")
        checkbox_vbox = gtk.VBox()
        checkbox_viewport.add(checkbox_vbox)
        for block in self.chip_model.model.blocks:
            self.add_checkbox(checkbox_vbox,"(R) " + block.name)

        for memory in self.chip_model.model.memory_modules:
            self.add_checkbox(checkbox_vbox,"(M) " + memory.name)


    def add_checkbox(self,target_vbox,text):
        checkbox = gtk.CheckButton(label = text)
        checkbox.connect("toggled",self.checkbox_toggled)
        target_vbox.pack_start(checkbox)

    def checkbox_toggled(self,widget,data = None):
        text = widget.get_label()
        type = text.split(" ")[0]
        name = text.split(" ")[-1]
        if type == "(R)":
            if widget.get_active():
                self.blocks_to_test.append(self.chip_model.model.block_by_name(name))
            else:
                self.blocks_to_test.remove(self.chip_model.model.block_by_name(name))
        elif type == "(M)":
            if widget.get_active():
                self.memories_to_test.append(self.chip_model.model.mem_module_by_name(name))
            else:
                self.memories_to_test.remove(self.chip_model.model.mem_module_by_name(name))





# Real block / memory testing code starts here

    def check_block(self,block):
        num_failed_fields = 0
        for register in block.registers:
            if self.to_stop_test:
                self.spinner.stop()
                return
            num_failed_fields += self.check_register(register)
        return num_failed_fields

    def check_memory_region(self,mem_region):
        num_failed_memories = 0
        for memory in mem_region.memories:
            if self.to_stop_test:
                self.spinner.stop()
                return
            num_failed_memories += self.check_memory(memory)
        return num_failed_memories


    def check_register(self,register):
        num_failed_field = 0
        # TODO: differentiate between read only to r/w fields
        self.update_log_async("*" * 3 + " Testing register : " + register.name)
        is_read_only = False
        register.set_raw_val(0)
        self.chip_model.write_reg(register)
        register.set_raw_val(0xFFFFFFFF)
        self.chip_model.write_reg(register)
        # Go over fields and test each one
        self.chip_model.read_reg(register)
        for field in register.fields:
            if not re.search(self.combined_fields_exclude_re, field.name):
                if field.value != (math.pow(2,field.width) - 1):
                    self.update_log_async("*" * 3 + " ERR: Bad value (0x%X) in field : %s" %(field.value, field.name),True)
                    num_failed_field += 1
            else:
                self.update_log_async("*" * 3 + " Skipping Field : %s" % field.name)
        return num_failed_field




    def check_memory(self,memory):
        num_failed_memories = 0
        if not re.search(self.combined_memories_exclude_re, memory.name):
            self.update_log_async("*" * 3 + " Testing memory : " + memory.name)

            # Create a binary file, upload and download
            for pattern in [0x0, 0xAAAAAAAA, 0x55555555,0xFFFFFFFF]:
                upload_filename = os.path.abspath(os.path.join("MemTest",memory.name + "_0x%X"%pattern + "_upload.bin"))
                download_filename = os.path.abspath(os.path.join("MemTest",memory.name + "_0x%X"%pattern + "_download.bin"))
                if re.search(self.mask_16bit_re, memory.name):
                    self.create_bin_file(upload_filename,memory.size,pattern,0x0000FFFF)
                elif re.search(self.mask_12bit_re, memory.name):
                    self.create_bin_file(upload_filename,memory.size,pattern,0x00000FFF)
                else:
                    self.create_bin_file(upload_filename,memory.size,pattern)

                self.chip_model.load_bin_file_to_address(memory.address,upload_filename)
                self.chip_model.dump_bin_file_from_address(memory.address,memory.size,download_filename)
                # Check if files are bit exact
                if not filecmp.cmp(upload_filename,download_filename):
                    num_failed_memories += 1
                    self.update_log_async("*" * 3 + " ERR: Files are not bit exact in memory : %s, pattern %s "%(memory.name,pattern),True)

        return num_failed_memories



    def create_bin_file(self,filename,size,pattern = None,mask = None):
        fh = open(filename,'wb')
        dword_size = size / 4
        for i in range(dword_size):
            if pattern == None:
                num = random.randint(0,0xFFFFFFFF)
            else:
                num = pattern

            if mask != None:
                num = num & mask

            dword =struct.pack("L",num)
            fh.write(dword)
        fh.close()












    def __del__(self):
        self.window.destroy()


if __name__ == "__main__":
    print "Parsing h file"
    h_file = glob.glob("*.h")[0]
    model = ChipConnector.ChipConnector(h_file)

    model.connect_board()
    memTest = MemoryTest(model)
    gtk.main()