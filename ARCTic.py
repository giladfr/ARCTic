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
import os
import sys
from ChipConnector import *
import datetime
import glob
import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
import pango
import locale
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
import importlib
import gobject

__Version__ = "0.12"
gobject.threads_init()


class BufferDraw:
    def __init__(self,buffer):
        pass

    def show_dialog(self):
        pass




class ARCTic:
        def __init__(self,input_h_file = ""):
            print "ARCTic Init"
            #Set the Glade file
            self.gladefile = "ARCTic.glade"
            self.builder = gtk.Builder()
            print "Building Static GUI from Glade File"
            self.builder.add_from_file(self.gladefile)
            self.board_ops_buttons = []
            self.open_dialog = self.builder.get_object("FileOpenDialog")
            self.memdump_dialog = self.builder.get_object("MemDumpDialog")

            #Get the Main Window, and connect the "destroy" event
            self.window = self.builder.get_object("MainWindow")
            if (self.window):
                self.window.connect("destroy", self.exit)

            self.window.set_icon_from_file("ARCTic.ico")

            self.status_bar =  self.builder.get_object("StatusBar")
            self.statusbar_context_id = self.status_bar.get_context_id("Log")


            # Connect callbacks
            handlers = {"on_mainWindow_destroy" : self.exit,
                        "on_Connect_clicked" : self.connect,
                        "on_RefreshAll_clicked" : self.refresh_all,
                        "on_CommitAll_clicked" : self.commit_all,
                        "on_SaveAll_clicked" : self.save_all,
                        "on_OpenFile_clicked" : self.open_file,
                        "on_aboutMenuItem_activate" : self.show_about,
                        "on_ResumeFW_clicked": self.detach_run,
                        "on_download_activate": self.download_firmware,
                        "on_MainWindow_key_press_event" : self.main_keypress,
                        "on_memdump_activate": self.memory_dump

                        }

            self.builder.connect_signals(handlers)




            # Creating the model
            print "Parsing h file"
            if input_h_file == "":
                # h file wasn't defined, try to find and load it
                input_h_file = glob.glob("*.h")[0]
            self.chip_connector = ChipConnector(input_h_file)

            # add dynamic elements
            print "Building Dynamic GUI - register map"
            self.build_dynamic_reg_map()
            print "Building Dynamic GUI - memory map"
            self.build_dynamic_mem_map()
            settings = gtk.settings_get_default()
            settings.props.gtk_button_images = True
            regview_width = self.builder.get_object("RegViewPort").get_allocation()[2]
            self.window.set_geometry_hints(None,min_width = regview_width)
            self.window.set_title("ARCTic - Version: " + str(__Version__))


            # disable sensitivity of all the register ops buttons
            self.board_ops_buttons.append(self.builder.get_object("CommitAll"))
            self.board_ops_buttons.append(self.builder.get_object("RefreshAll"))
            self.board_ops_buttons.append(self.builder.get_object("ResumeFW"))
            self.set_sensitivity_board_ops(False)

            # Build the plugins menu
            sys.path.append("./plugins")
            plugins_list = [os.path.basename(i).split(".")[0] for i in glob.glob("./plugins/*.py")]
            plugins_menu = self.builder.get_object("PluginsMenu")

            for plugin_name in plugins_list:
                new_plugin_item = gtk.MenuItem()
                new_plugin_item.set_name(plugin_name)
                new_plugin_item.set_label(plugin_name)
                new_plugin_item.connect("activate",self.activate_plugin)
                plugins_menu.add(new_plugin_item)


            self.window.show_all()
            print "ARCTIC - Init End"



        def exit(self, widget, data=None):
            self.window.destroy()
            gtk.main_quit()


        def set_sensitivity_board_ops(self,isEnabled):
            [but.set_sensitive(isEnabled) for but in self.board_ops_buttons]
            self.builder.get_object("Connect").set_sensitive(not(isEnabled))




        def connect(self, widget, data=None):
            "Connect to the JTAG debugger"
            res = self.chip_connector.connect_board()
            if self.chip_connector.is_connected:
                self.log_status("Succesfully connected to digilent cable")
                self.set_sensitivity_board_ops(True)
            else:
                self.log_status("Error: " + res)


        def refresh_all(self, widget, data=None):
            self.chip_connector.read_model_from_board()
            self.update_ui_from_model()


        def commit_all(self, widget, data=None):
            self.update_model_from_ui()
            self.chip_connector.write_model_to_board()

        def save_all(self,widget, data = None):
            filename = self.save_file_dialog()
            if filename != "":
                for block in self.chip_connector.model.blocks:
                        self.chip_connector.save_block_on_disk(block, filename)



        def build_dynamic_mem_map(self):
            reg_viewport = self.builder.get_object("RegViewPort")
            scroll_window = gtk.ScrolledWindow()
            self.items_notebook.append_page(scroll_window,gtk.Label("Memories"))
            module_viewport = gtk.Viewport()
            scroll_window.add(module_viewport)
            module_vbox = gtk.VBox(homogeneous = False, spacing = 1)
            module_viewport.add(module_vbox)

            for mem_module in self.chip_connector.model.memory_modules:
               # Build a frame for each register
                module_frame = gtk.Frame(label = mem_module.name )
                module_frame.set_border_width(5)
                module_frame.set_label_align(0.5,0.5)
                module_frame.set_name(mem_module.name)
                module_vbox.add(module_frame)

                # fields adding
                memory_vbox = gtk.VBox()
                module_frame.add(memory_vbox)
                for memory in mem_module.memories:
                    # memory hbox
                    memory_hbox = gtk.HBox(homogeneous = False)
                    memory_vbox.add(memory_hbox)

                    # Label for each memory in module
                    field_label = gtk.Label("[0x%06X] "%memory.address  + memory.name  + " [" + str(memory.size) + "] ")
                    field_label.modify_font(pango.FontDescription("sans 12"))
                    memory_hbox.pack_start(field_label,False,True,10)


                   # Buttons for each memory
                    button_box = gtk.HButtonBox()
                    button_box.set_layout(gtk.BUTTONBOX_END)
                    memory_hbox.add(button_box)

                    save_but = gtk.Button()
                    image_save = gtk.Image()
                    image_save.set_from_stock(gtk.STOCK_SAVE, gtk.ICON_SIZE_BUTTON)
                    save_but.add(image_save)
                    save_but.connect("clicked",self.memory_save,memory)
                    button_box.add(save_but)

                    upload_but = gtk.Button()
                    image_upload = gtk.Image()
                    image_upload.set_from_stock(gtk.STOCK_GO_UP, gtk.ICON_SIZE_BUTTON)
                    upload_but.add(image_upload)
                    upload_but.connect("clicked",self.memory_upload,memory)
                    button_box.add(upload_but)

                    lutdraw_but = gtk.Button()
                    image_lutdraw = gtk.Image()
                    image_lutdraw.set_from_stock(gtk.STOCK_PRINT, gtk.ICON_SIZE_BUTTON)
                    lutdraw_but.add(image_lutdraw)
                    lutdraw_but.connect("clicked",self.draw_lut,memory)
                    button_box.add(lutdraw_but)


                    self.board_ops_buttons.append(button_box)







        def build_dynamic_reg_map(self):
            reg_viewport = self.builder.get_object("RegViewPort")
            self.items_notebook = gtk.Notebook()
            reg_viewport.add(self.items_notebook)
            for block in self.chip_connector.model.blocks:
                # build a scroll view and view port for each block
                scroll_window = gtk.ScrolledWindow()
                block_viewport = gtk.Viewport()
                scroll_window.add(block_viewport)
                scroll_window.set_policy(gtk.POLICY_AUTOMATIC   , gtk.POLICY_AUTOMATIC)
                self.items_notebook.append_page(scroll_window,gtk.Label(block.name))
                # Build a registers vbox for each block
                reg_vbox = gtk.VBox(homogeneous = False, spacing = 1)
                block_viewport.add(reg_vbox)

                # Add buttons for each block inside a frame for block operations
                block_ops_frame = gtk.Frame(label = "Block Operations")
                block_ops_frame.set_border_width(5)
                block_ops_frame.set_label_align(0.5,0.5)
                reg_vbox.add(block_ops_frame)
                button_box = gtk.HButtonBox()
                button_box.set_border_width(5)
                button_box.set_layout(gtk.BUTTONBOX_SPREAD)
                block_ops_frame.add(button_box)
                refresh_but = gtk.Button()
                image_refresh = gtk.Image()
                image_refresh.set_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_BUTTON)
                refresh_but.add(image_refresh)
                refresh_but.connect("clicked",self.block_refresh,block)
                button_box.add(refresh_but)
                commit_but = gtk.Button()
                image_commit = gtk.Image()
                image_commit.set_from_stock(gtk.STOCK_GO_UP, gtk.ICON_SIZE_BUTTON)
                commit_but.add(image_commit)
                commit_but.connect("clicked",self.block_commit,block)
                button_box.add(commit_but)
                save_but = gtk.Button()
                image_save = gtk.Image()
                image_save.set_from_stock(gtk.STOCK_SAVE, gtk.ICON_SIZE_BUTTON)
                save_but.add(image_save)
                save_but.connect("clicked",self.block_save,block)
                button_box.add(save_but)
                self.board_ops_buttons.append(block_ops_frame)


                for register in block.registers:
                    # Build a frame for each register
                    reg_frame = gtk.Frame(label = register.name + " [0x%X]" % register.address_int)
                    reg_frame.set_border_width(5)
                    reg_frame.set_label_align(0.5,0.5)
                    reg_frame.set_name(register.name)
                    reg_vbox.add(reg_frame)
                    # fields adding
                    fields_vbox = gtk.VBox()
                    reg_frame.add(fields_vbox)
                    for field in register.fields:
                        # Field control H box
                        fcontrol_hbox = gtk.HBox(homogeneous = False)
                        fields_vbox.add(fcontrol_hbox)


                        # Label - for each field
                        field_label = gtk.Label("[" + "%02d"%field.offset + "] " +  field.name)
                        field_label.modify_font(pango.FontDescription("sans 14"))
                        fcontrol_hbox.pack_start(field_label,False,True,10)

                        # Spin Button
                        adjustment = gtk.Adjustment(value=0, lower=0, upper=int(math.pow(2,field.width)-1), step_incr=1, page_incr=0, page_size=0)
                        val_spin = gtk.SpinButton(adjustment)
                        val_spin.set_name(field.name)
                        val_spin.modify_font(pango.FontDescription("monospace 14"))
                        val_spin.connect("output",self.field_spin_value_changed)
                        val_spin.connect("value_changed",self.field_spin_value_changed)
                        val_spin.set_width_chars(3)
                        field.ui = val_spin
                        fcontrol_hbox.pack_end(val_spin,False,False,10)

                    # Buttons for each register
                    button_box = gtk.HButtonBox()
                    button_box.set_layout(gtk.BUTTONBOX_SPREAD)
                    fields_vbox.add(button_box)

                    refresh_but = gtk.Button()
                    image_refresh = gtk.Image()
                    image_refresh.set_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_BUTTON)
                    refresh_but.add(image_refresh)
                    refresh_but.connect("clicked",self.register_refresh,register)
                    button_box.add(refresh_but)

                    commit_but = gtk.Button()
                    image_commit = gtk.Image()
                    image_commit.set_from_stock(gtk.STOCK_GO_UP, gtk.ICON_SIZE_BUTTON)
                    commit_but.add(image_commit)
                    commit_but.connect("clicked",self.register_commit,register)
                    button_box.add(commit_but)

                    self.board_ops_buttons.append(button_box)


        def field_spin_value_changed(self,widget,data = None):
            adjustment = widget.get_adjustment()
            value = adjustment.get_value()
            text = "0x%X" % value
            widget.set_width_chars(len(text));
            widget.set_text(text)



        def block_refresh(self,widget,data = None):
            block = data
            for register in block.registers:
                self.register_refresh(None,register)

        def block_commit(self,widget,data=None):
            block = data
            for register in block.registers:
                self.register_commit(None,register)

        def block_save(self,widget,data=None):
            block = data
            timestamp = datetime.datetime.now().strftime("%dd%mm%yy")
            filename = self.save_file_dialog(block.name + "_" + timestamp)
            if filename != "":
                self.chip_connector.save_block_on_disk(block, filename)




        def register_refresh(self, widget, data=None):
            register = data
            # refresh the chip model of the register
            self.chip_connector.read_reg(register)
            # Update the UI of the register
            self.update_reg_ui_from_model(data)
            self.log_status("Successfully read value 0x%X from register %s"% (register.get_raw_val(),register.name))


        def register_commit(self,widget, data = None):
            register = data
            # Update the fields from the UI
            self.update_reg_model_from_ui(register)
            # Write register to board
            self.chip_connector.write_reg(register)
            self.log_status("Successfully committed value 0x%X to register %s"%(register.get_raw_val(),register.name))

        def memory_save(self,widget,data = None):
            filename = self.save_file_dialog()
            if filename != "":
                res = self.chip_connector.dump_bin_file_from_address(data.address, data.size, filename)
                self.log_status(res)

        def memory_upload(self,widget,data = None):
            filename = self.open_file_dialog()
            if filename != "":
                res = self.chip_connector.load_bin_file_to_address(data.address, filename)
                self.log_status(res)


        def update_ui_from_model(self):
            for block in self.chip_connector.model.blocks:
                for register in block.registers:
                    self.update_reg_ui_from_model(register)


        def update_model_from_ui(self):
            for block in self.chip_connector.model.blocks:
                for register in block.registers:
                    self.update_reg_model_from_ui(register)


        def update_reg_ui_from_model(self,register):
            for field in register.fields:
                field.ui.set_value(float(field.value))
                self.field_spin_value_changed(field.ui)

        def update_reg_model_from_ui(self,register):
            for field in register.fields:
                field.value = int(field.ui.get_value())
                self.field_spin_value_changed(field.ui)





        def save_file_dialog(self,suggested_filename = None):
            dialog = gtk.FileChooserDialog(title="Save as...",action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
            dialog.set_default_response(gtk.RESPONSE_OK)
            if suggested_filename:
                dialog.set_filename(suggested_filename)
            response = dialog.run()
            filename = ""
            if response == gtk.RESPONSE_OK:
                filename = dialog.get_filename()
            elif response == gtk.RESPONSE_CANCEL:
                filename = ""
            dialog.destroy()
            return filename


        def open_file_dialog(self):
            dialog = gtk.FileChooserDialog(title="Open Memory File...",action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            dialog.set_default_response(gtk.RESPONSE_OK)
            response = dialog.run()
            filename = ""
            if response == gtk.RESPONSE_OK:
                filename = dialog.get_filename()
            elif response == gtk.RESPONSE_CANCEL:
                filename = ""
            dialog.destroy()
            return filename




        def open_file(self,widget,data = None):
            response = self.open_dialog.run()
            self.open_dialog.hide()
            if response:
                run_after_open = self.builder.get_object("commitAfterload").get_active()
                filename =  self.open_dialog.get_filename()
                if filename:
                    self.parse_csv(filename,run_after_open)



        def log_status(self,text):
            self.status_bar.push(self.statusbar_context_id,text)


        def detach_run(self,widget,data = None):
            self.chip_connector.detach()
            self.log_status("ARC Resumed")
            self.set_sensitivity_board_ops(False)


        def activate_plugin(self,widget,data = None):
            plugin_name =  widget.get_name()
            print "Activating plugin", plugin_name
            plugin_lib = importlib.import_module(plugin_name)
            os.chdir("./plugins")
            plugin = getattr(plugin_lib,plugin_name)(self.chip_connector)
            os.chdir("..")



        def show_about(self,widget,data = None):
            about_win = self.builder.get_object("aboutDialog")
            about_win.version = __Version__
            about_win.run()
            about_win.hide()


        def parse_csv(self,filename,is_commit):
            fh = open(filename,"r")
            for line in fh.readlines():
                splitted = line.strip().split(",")
                if line.startswith("MEM"):
                    aa , mem_module_name, mem_name , file_path = splitted
                    file_path = os.path.abspath(file_path)
                    mem_module = self.chip_connector.model.mem_module_by_name(mem_module_name)
                    if mem_module != None:
                        memory = mem_module.memory_by_name(mem_name)
                        if memory != None:
                            res = self.chip_connector.load_bin_file_to_address(memory.address, file_path)
                        else:
                            self.show_error_box("Can't find memory named: " + mem_name)
                    else:
                        self.show_error_box("Can't find memory module named: " + mem_module_name)

                else:
                    block_name , register_name , value = splitted
                    # Updaate the register in the model
                    block = self.chip_connector.model.block_by_name(block_name)
                    if block != None:
                        register = block.register_by_name(register_name)
                        if register != None:
                            register.set_raw_val(int(value,16))
                            if is_commit:
                                self.chip_connector.write_reg(register)
                        else:
                            self.show_error_box("Can't find register named: " + register_name)
                    else:
                            self.show_error_box("Can't find block named: " + block_name)
            self.update_ui_from_model()

        def draw_lut(self,widget,data = None):
            # Dump to bin file
            memory = data

            res = self.chip_connector.dump_bin_file_from_address(memory.address, memory.size, os.path.join(os.getcwd(), "lutdraw.bin"))
            self.log_status(res)

            # Draw the lut
            fh = open("lutdraw.bin","rb")
            window = gtk.Window()
            window.set_geometry_hints(None,min_width = 600,min_height = 600)
            window.set_title(str(memory.name))

            figure = Figure(figsize=(20,20), dpi=100)
            axis = figure.add_subplot(111)
            canvas = FigureCanvas(figure)
            window.add(canvas)
            signal = []
            dword = fh.read(4)
            while (dword):

                val, = struct.unpack('L', dword)
                signal.append(val)
                dword = fh.read(4)

            axis.cla()
            axis.plot(signal)
            figure.canvas.draw()

            window.show_all()



        def download_firmware(self,widget,data=None):
            filename = self.open_file_dialog()
            if filename != "":
                self.chip_connector.download_firmware(filename)

        def memory_dump(self,widget,data=None):
            response = self.memdump_dialog.run()
            self.memdump_dialog.hide()
            if response:
                filename = self.builder.get_object("memDump_Filename").get_text()
                size_bytes_str = self.builder.get_object("memDump_Size").get_text()
                addr_str = self.builder.get_object("memDump_Addr").get_text()
                # Convert to int 16 if neede
                if (size_bytes_str.startswith("0x")):
                    size_bytes = int(size_bytes_str,16)
                else:
                    size_bytes = int(size_bytes_str)

                if (addr_str.startswith('0x')):
                    addr = int(addr_str,16)
                else:
                    addr = int(addr_str)
                if filename:
                    filename = os.path.abspath(filename)
                    self.chip_connector.dump_bin_file_from_address(addr, size_bytes, filename)



        def show_error_box(self,description):
            arent = None
            md = gtk.MessageDialog(self.window,
                gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_CLOSE, description)
            md.run()
            md.destroy()


        def main_keypress(self,widget,data = None):
            print widget
            print data



if __name__ == "__main__":
    if len(sys.argv) > 1:
        hwg = ARCTic(sys.argv[1])
    else:
        hwg = ARCTic()

    gtk.main()