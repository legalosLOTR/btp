#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
from GdbPexpect import GdbPexpect
import sqlite3


class MyFrame(wx.Frame):
    def __init__(self, database, gdb_pexpect, *args, **kwds):
        self.gdb_pexpect = gdb_pexpect
        self.__init_db(database)
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.search_box = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        self.button_backward = wx.Button(self, -1, label="<<", name='backward')
        self.button_forward = wx.Button(self, -1, label=">>", name='forward')
        self.entries_list_box = wx.ListBox(self, -1, choices=[], style=wx.LB_SINGLE)
        self.detail_pane = wx.StaticText(self, -1, "Entry Details")
        self.list_header = wx.StaticText(self, -1, "Timestamp\t\t\t\t\t\t\tMemory address\t\t\t\tEIP")

        self.__set_properties()
        self.__do_layout()
        self.__setup_events()
        # end wxGlade

        init_res = self.db_search(0)
        self.add_to_entries_list_box(init_res)


    def __init_db(self, database):
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()

    def __setup_events(self):
        self.button_forward.Bind(wx.EVT_BUTTON, self.search_button_clicked)
        self.button_backward.Bind(wx.EVT_BUTTON, self.search_button_clicked)
        self.entries_list_box.Bind(wx.EVT_LISTBOX, self.entry_clicked)
        self.entries_list_box.Bind(wx.EVT_LISTBOX_DCLICK, self.entry_d_clicked)

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Query Engine - RRDebug")
        self.search_box.SetMinSize((150, 27))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.search_box, 0, wx.ALL, 0)
        sizer_2.Add(self.button_backward, 0, 0, 0)
        sizer_2.Add(self.button_forward, 0, 0, 0)
        sizer_1.Add(sizer_2, 0, wx.ALIGN_RIGHT, 0)
        sizer_1.Add((-1,20))
        sizer_1.Add(sizer_4, 0, 0, 0)
        sizer_4.Add(self.list_header, 0, 0, 0)
        sizer_3.Add(self.entries_list_box, 1, wx.ALL|wx.EXPAND, 0)
        sizer_3.Add(self.detail_pane, 1, wx.ALL|wx.EXPAND, 3)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()
        # end wxGlade

    def search_button_clicked(self, e):
        button_name = e.GetEventObject().GetName()
        query = self.search_box.GetValue()

        if query.startswith('0x'):
            query_addr = query[2:]
        else:
            out = gdb_pexpect.execute('p &{0}'.format(query))[1]
            if (out.startswith('No symbol')):
                wx.MessageDialog(None, "Symbol not found.", 'Error',
                        wx.OK | wx.ICON_ERROR).ShowModal()
                return
            else:
                query_addr = out.split('0x')[1].strip()

        cur_index = self.entries_list_box.GetSelection()
        if cur_index == wx.NOT_FOUND:
            cur_ts = 0
        else:
            cur_ts = self.entries_list_box.GetClientData(cur_index)[1]

        if (button_name == 'forward'):
            res = self.db_search(cur_ts, query_addr)
        else:
            res = self.db_search(cur_ts, query_addr, False)

        if (len(res) == 0):
            wx.MessageDialog(None, "Address not found in database.", 'Error',
                    wx.OK | wx.ICON_ERROR).ShowModal()
        else:
            self.entries_list_box.Set([])
            self.add_to_entries_list_box(res)

    def add_to_entries_list_box(self, entries):
        for item in entries:
            self.entries_list_box.Append("{0}\t\t\t\t{1}\t\t\t\t{2}".format(item[1],
                item[2], item[0]), clientData=item)

    def entry_clicked(self, e):
        selected_index = self.entries_list_box.GetSelection()
        if (selected_index != wx.NOT_FOUND):
            selected = self.entries_list_box.GetClientData(selected_index)
            self.display_on_detail_pane(selected)

    def display_on_detail_pane(self, entry):
        out = "Memory Address:\t{0}\n\
Eip:\t\t\t\t\t{1}\n\
Old Data:\t\t\t\t{2}\n\
New Data:\t\t\t{3}\n\
Backtrace:\n\n{4}\n".format(entry[2], entry[0], entry[3], entry[4], entry[5])
        self.detail_pane.SetLabel("Details:\n\n" + out)

    def entry_d_clicked(self, e):
        selected = self.entries_list_box.GetClientData(self.entries_list_box.\
                GetSelection())
        disp = self.db_search(selected[1], forward=False)
        past = len(disp)
        disp.append(selected)
        disp.extend(self.db_search(selected[1]))

        self.entries_list_box.Set([])
        self.add_to_entries_list_box(disp)
        self.entries_list_box.SetSelection(past)

    def db_search(self, ts, mem_addr=None, forward=True, limit=50):
        if forward:
            comp = '>'
        else:
            comp = '<'

        if (mem_addr is None):
            results = self.cursor.execute('SELECT * FROM logs WHERE timestamp\
                    {0} ? limit {1}'.format(comp, limit), (ts,)).fetchall()
        else:
            results = self.cursor.execute('SELECT * FROM logs WHERE timestamp\
                    {0} ? AND mem_addr = "{1}" limit {2}'.format(comp,
                        mem_addr, limit), (ts,)).fetchall()

        return results


# end of class MyFrame


if __name__ == "__main__":
    database = '../rrdebug.sqlite.old'
    gdb_exec = '/usr/local/bin/gdb'
    vmlinux = '/home/ankur/btp/vmlinux.gent'

    gdb_pexpect = GdbPexpect(gdb_exec)
    gdb_pexpect.execute('file ' + vmlinux)

    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    frame_1 = MyFrame(database, gdb_pexpect, None, -1, "")
    app.SetTopWindow(frame_1)
    frame_1.SetSizeHints(800, 600)
    frame_1.Show()
    frame_1.Maximize()
    app.MainLoop()
