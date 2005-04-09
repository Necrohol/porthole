#!/usr/bin/env python

'''
    Porthole Depends TreeModel
    Calculates and stores package dependency information

    Copyright (C) 2003 - 2004 Fredrik Arnerup and Daniel G. Taylor

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''

import gtk, gobject, portagelib, string
from utils import dprint
from gettext import gettext as _

class DependsTree(gtk.TreeStore):
    """Calculate and display dependencies in a treeview"""
    def __init__(self):
        """Initialize the TreeStore object"""
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING,
                                gtk.gdk.Pixbuf,
                                gobject.TYPE_PYOBJECT,
                                gobject.TYPE_BOOLEAN)
        self.use_flags = portagelib.get_portage_environ("USE").split()
        
    def parse_depends_list(self, depends_list, parent = None):
        """Read through the depends list and order it nicely
           Returns a list of (parent, dep, satisfied) for each dep"""
        new_list = []
        use_list = []
        ops = ""
        using_list=False
        for depend in depends_list:
            #dprint(depend)
            if depend[-1] == "?":
                if depend[0] != "!":
                    parent = _("Using ") + depend[:-1]
                    using_list=True
                else:
                    parent = _("Not Using ") + depend[1:-1]
            else:
                if depend not in ["(", ")", ":", "||"]:
                    try: depend, ops = self.get_ops(depend)
                    except: dprint("DEPENDS: Depend didn't split: " + depend)
                    depend2 = None
                    if ops: # should only be specific if there are operators
                        depend2 = portagelib.extract_package(depend)
                    if not depend2:
                        depend2 = depend
                    latest_installed = portagelib.Package(depend2).get_installed()
                    if latest_installed:
                        if ops:
                            satisfied = self.is_dep_satisfied(latest_installed[0], depend, ops)
                        else:
                            satisfied = True
                    else:
                        satisfied = False
                    if using_list:
                        use_list.append((parent, depend, satisfied))
                    else:
                        new_list.append((parent,depend,satisfied))
                if depend == ")":
                    using_list = False
                    parent = None
        return new_list + use_list
                    

    def add_depends_to_tree(self, depends_list, depends_view, parent = None):
        """Add all dependencies to the tree"""
        depends_list = self.parse_depends_list(depends_list)
        parent_iter = parent
        last_flag = None
        for use_flag, depend, satisfied in depends_list:
            if last_flag != use_flag and use_flag != None:
                parent_iter = self.insert_before(parent, None)
                self.set_value(parent_iter, 0, use_flag)
                if use_flag[0] == "U":
                    flag = use_flag[6:]
                    icon = flag in self.use_flags and gtk.STOCK_YES or ''
                else:
                    flag = use_flag[9:] 
                    icon = flag in self.use_flags and '' or gtk.STOCK_YES
                self.set_value(parent_iter, 1, depends_view.render_icon(icon,
                                    size = gtk.ICON_SIZE_MENU, detail = None))
                last_flag = use_flag
                depend_iter = self.insert_before(parent_iter, None)
            elif use_flag == None:
                depend_iter = self.insert_before(parent,None)
            else:
                depend_iter = self.insert_before(parent_iter,None)
            self.set_value(depend_iter, 0, depend)
            if satisfied:
                icon = gtk.STOCK_YES
            else:
                icon = '' # used to be gtk.STOCK_NO
            self.set_value(depend_iter, 3, satisfied)
            self.set_value(depend_iter, 1, 
                                    depends_view.render_icon(icon,
                                                             size = gtk.ICON_SIZE_MENU,
                                                             detail = None))
            pack = portagelib.Package(depend)
            self.set_value(depend_iter, 2, pack)
            if icon != gtk.STOCK_YES:
                if depend not in self.depends_list:
                    self.depends_list.append(depend)
                    #pack = portagelib.Package(depend)
                    ebuild = pack.get_latest_ebuild()
                    depends = portagelib.get_property(ebuild, "DEPEND").split()
                    if depends:
                        self.add_depends_to_tree(depends, depends_view, depend_iter)

    def get_ops(self, depend):
        """No, this isn't IRC...
           Returns depend with the operators cut out, and the operators"""
        op = depend[0]
        if op in [">", "<", "=", "!"]:
            op2 = depend[1]
            if op2 == "=":
                return depend, op + op2
            else:
                return depend, op
        else:
            return depend, None

    def is_dep_satisfied(self, installed_ebuild, dep_ebuild, operator = "="):
        """ Returns installed_ebuild <operator> dep_ebuild """
        retval = False
        ins_ver = portagelib.get_version(installed_ebuild)
        dep_ver = portagelib.get_version(dep_ebuild)
        # extend to normal comparison operators in case they aren't
        if operator == "=": operator = "=="
        if operator == "!": operator = "!="
        # determine the retval
        if operator == "==": retval = ins_ver == dep_ver
        elif operator == "<=":  retval = ins_ver <= dep_ver
        elif operator == ">=": retval = ins_ver >= dep_ver
        elif operator == "!=": retval = ins_ver != dep_ver
        elif operator == "<": retval = ins_ver < dep_ver
        elif operator == ">": retval = ins_ver > dep_ver
        # return the result of the operation
        return retval

    def fill_depends_tree(self, treeview, package):
        """Fill the dependencies tree for a given ebuild"""
        dprint("DEPENDS: Updating deps tree for " + package.get_name())
        ebuild = package.get_latest_ebuild(False)
        depends = portagelib.get_property(ebuild, "DEPEND").split()
        self.clear()
        if depends:
            #dprint(depends)
            self.depends_list = []
            self.add_depends_to_tree(depends, treeview)
        else:
            parent_iter = self.insert_before(None, None)
            self.set_value(parent_iter, 0, _("None"))
        treeview.set_model(self)
