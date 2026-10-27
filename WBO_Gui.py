# WBO Workbench-Organizer widget for FreeCAD
# Copyright (C) 2015, 2016, 2017, 2018 by triplus @ FreeCAD who provided
# the wonderful TabBar widget on which this is based.
# Copyright (C) 2024 Oliver Rafelsberger
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

"""A workbench organizer for FreeCAD."""
"""Group and rename your workbenches as you like!"""

import FreeCADGui as Gui
import FreeCAD as App
# FreeCAD's PySide module wraps PySide2 (Qt5) or PySide6 (Qt6), whichever FreeCAD is built with.
from   PySide import QtGui, QtCore
try:
    from PySide import QtWidgets
except ImportError:     # FreeCAD < 0.20: no QtWidgets in the PySide module, QtGui holds the widgets
    QtWidgets = QtGui
import os
import webbrowser
import wbo_core as core

# QAction and QActionGroup moved from QtWidgets (Qt5) to QtGui (Qt6).
QAction      = getattr(QtWidgets, "QAction", None)      or QtGui.QAction
QActionGroup = getattr(QtWidgets, "QActionGroup", None) or QtGui.QActionGroup

__strAll__        = core.STR_ALL
__strDrop__       = core.STR_DROP
__strNew__        = core.STR_NEW
__strLost__       = core.STR_LOST
__strDisabled__   = core.STR_DISABLED

# The config lives outside the addon folder, so addon updates can't touch it.
__pathAddon__     = os.path.dirname(os.path.abspath(__file__))
__pathConfig__    = os.path.join(App.getUserAppDataDir(), "WB_Organizer")
__pathGroupFile__ = os.path.join(__pathConfig__, core.GROUP_FILE)
__pathAliasFile__ = os.path.join(__pathConfig__, core.ALIAS_FILE)
__pathIcons__     = os.path.join(os.path.dirname(__file__), "Resources", "icons") + os.path.sep
__pathToolbar__   = "User parameter:BaseApp/Workbench/Global/Toolbar"

__parameters__    = App.ParamGet("User parameter:BaseApp/WB_Organizer")
__groupedWB__     = {}
__aliasNames__    = {}

__actions__       = {}
__mainWindow__    = Gui.getMainWindow()
__tabActions__    = QActionGroup(__mainWindow__)

__floatingWidgetWidth__ = 1330

#----------------------------------------------------------
class WBO(QtWidgets.QTabBar):
    def tabSizeHint(self, index):
        s = QtWidgets.QTabBar.tabSizeHint(self, index)
        s.transpose()
        return s

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        opt = QtWidgets.QStyleOptionTab()

        for i in range(self.count()):
            self.initStyleOption(opt, i)
            painter.drawControl(QtWidgets.QStyle.ControlElement.CE_TabBarTabShape, opt)
            painter.save()

            s = opt.rect.size()
            s.transpose()
            r = QtCore.QRect(QtCore.QPoint(), s)
            r.moveCenter(opt.rect.center())
            opt.rect = r

            c = self.tabRect(i).center()
            painter.translate(c)
            painter.rotate(90)
            painter.translate(-c)
            painter.drawControl(QtWidgets.QStyle.ControlElement.CE_TabBarTabLabel, opt)
            painter.restore()

    def Deactivated(self):
        # is called whenever the Workbench is deactivated.
        return

class TabWidget(QtWidgets.QTabWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        self.setTabBar(WBO(self))
        self.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
#--------------------------------------------------------------------

class WidthGrip(QtWidgets.QWidget):
    """Handle at the right end of the free floating toolbar to drag its length."""
    def __init__(self, toolbar):
        QtWidgets.QWidget.__init__(self, toolbar)
        self.toolbar = toolbar
        self.start   = None     # (mouse x, toolbar width) when the drag started
        self.setFixedWidth(10)
        self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
        self.setToolTip("Drag to change the length of the Workbench Organizer")

    @staticmethod
    def mouseX(event):
        return event.globalPosition().x() if hasattr(event, "globalPosition") else event.globalX()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.ColorRole.Mid))
        x = self.width() // 2
        for dx in (-2, 1):
            painter.drawLine(x + dx, 4, x + dx, self.height() - 5)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.start = (self.mouseX(event), self.toolbar.width())

    def mouseMoveEvent(self, event):
        if self.start:
            x, width = self.start
            self.toolbar.resize(max(150, int(width + self.mouseX(event) - x)), self.toolbar.height())

    def mouseReleaseEvent(self, event):
        if self.start:
            self.start = None
            setFloatingWidth(self.toolbar.width())


def setFloatingWidth(width):
    """Store the length of the free floating toolbar."""
    global __floatingWidgetWidth__
    __floatingWidgetWidth__ = width
    __parameters__.SetString("floatingWidth", str(width))

#--------------------------------------------------------------------

def saveMyWB():
    core.save_json(__pathGroupFile__, __groupedWB__)


def openMyWB():
    installed = list(Gui.listWorkbenches())
    try:
        for name in core.migrate_config(__pathAddon__, __pathConfig__):
            print("WB_Organizer: copied {} to {}".format(name, __pathConfig__))
    except OSError as e:
        print("WB_Organizer: can't copy the config to {}: {}".format(__pathConfig__, e))
    global __groupedWB__, __aliasNames__

    if not __parameters__.GetString("PrefButton"):
        __parameters__.SetString("floatingWidth", "1000")
        __parameters__.SetString("PrefButton", "Dropdown")
        __parameters__.SetString("Style", "IconText")
        __parameters__.SetString("selectedWB", __strAll__)

    if not os.path.exists(__pathGroupFile__):
        print("Config-file not found: generating new template.")
        __groupedWB__ = core.default_groups(installed)
        saveMyWB()
    else:   # a file already exists. Check for new and lost Workbenches
        loaded, error = core.load_json(__pathGroupFile__)
        if error:
            # Don't save here, so the user can still repair the broken file.
            print(error)
            print("ERROR on opening config-file.")
            __groupedWB__ = core.default_groups(installed)
        else:
            __groupedWB__ = core.sync_groups(loaded, installed)

    if not os.path.exists(__pathAliasFile__):
        print("Renaming-file not found: generating new Template.")
        __aliasNames__ = core.alias_template(installed)
        core.save_json(__pathAliasFile__, __aliasNames__)
    else:
        aliases, error = core.load_json(__pathAliasFile__)
        if error:
            print(error)
        else:
            __aliasNames__ = aliases

    global __selectedGroup__
    __selectedGroup__ = core.resolve_group(__groupedWB__, __parameters__.GetString("selectedWB", __strAll__))
    print("SelectedGroup:",__selectedGroup__)
    return __groupedWB__

__groupedWB__  = openMyWB()


def wbIcon(i):
    """Create workbench icon."""
    if str(i.find("XPM")) != "-1":
        icon = []
        for a in ((((i
                     .split('{', 1)[1])
                    .rsplit('}', 1)[0])
                   .strip())
                  .split("\n")):
            icon.append((a
                         .split('"', 1)[1])
                        .rsplit('"', 1)[0])
    else:
        icon = i
    try:
        icon = QtGui.QIcon(QtGui.QPixmap(icon))
    except Exception:   # e.g. an XPM icon the Qt binding can't read
        icon = QtGui.QIcon()
    if icon.isNull():
        icon = QtGui.QIcon(":/icons/freecad")
    return icon


def wbActions():
    """Create workbench actions."""
    wbList = Gui.listWorkbenches()
    for i in wbList:
        if i not in __actions__:
            try:
                action = QAction(__tabActions__)
                action.setCheckable(True)
                action.setText(core.display_name(i, wbList[i].MenuText, __aliasNames__))
                action.setData(i)
                action.setIcon(wbIcon(wbList[i].Icon))
                __actions__[i] = action
            except:  # there is one 'none'-WB without an icon. We remove this here.
                action.setIcon(QtGui.QIcon(":/icons/freecad"))


def onOrientationChanged(w):
    """Set the tabs orientation."""
    btn = w[0]
    tab = w[1]
    orientation = __parameters__.GetString("Orientation", "Auto")
    prefbutton  = __parameters__.GetString("PrefButton", "Dropdown")
    #if prefbutton == "Tabs":

    def layout():
        """Support menu for West and East orientations."""
        wid = QtWidgets.QWidget()
        lo  = QtWidgets.QVBoxLayout()
        #spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        #lo.addItem(spacer)
        lo.addWidget(btn)
        lo.addWidget(tab)
        wid.setLayout(lo)
        tb.addWidget(wid)
        lo.setContentsMargins(0, 0, 0, 0)
        btn.setMaximumWidth(tab.height())

    if orientation == "Auto":
        if __mainWindow__.toolBarArea(tb) == QtCore.Qt.ToolBarArea.TopToolBarArea:
            orientation = "North"
        elif __mainWindow__.toolBarArea(tb) == QtCore.Qt.ToolBarArea.BottomToolBarArea:
            orientation = "South"
        elif __mainWindow__.toolBarArea(tb) == QtCore.Qt.ToolBarArea.LeftToolBarArea:
            orientation = "West"
        elif __mainWindow__.toolBarArea(tb) == QtCore.Qt.ToolBarArea.RightToolBarArea:
            orientation = "East"
        elif tb.orientation() == QtCore.Qt.Orientation.Horizontal:
            orientation = "North"
        elif tb.orientation() == QtCore.Qt.Orientation.Vertical:
            orientation = "West"
        else:
            pass

    if tb.isFloating():
        global __floatingWidgetWidth__
        __floatingWidgetWidth__ = int(__parameters__.GetString("floatingWidth", "1000"))
        tb.resize(__floatingWidgetWidth__, tb.height())
        orientation = "South"


    if orientation == "North":
        tb.addWidget(btn)
        tb.addWidget(tab)
        if prefbutton == "Tabs":
            tab.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
    elif orientation == "South":
        if prefbutton == "Tabs":
            tab.setTabPosition(QtWidgets.QTabWidget.TabPosition.South)
        tb.addWidget(btn)
        tb.addWidget(tab)
    elif orientation == "West":
        if prefbutton == "Tabs":
            tab.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
            tab.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
        layout()
    elif orientation == "East":
        if prefbutton == "Tabs":
            tab.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
            tab.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        layout()
    else:
        pass

    if tb.isFloating():
        if prefbutton != "Tabs":    # the tabs fill the toolbar, the dropdown button doesn't
            spacer = QtWidgets.QWidget(tb)
            spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
            tb.addWidget(spacer)
        tb.addWidget(WidthGrip(tb))

    btn.show()


def onGroupSelected(group):
    """Group selected"""
    global __selectedGroup__
    __selectedGroup__ = group

    for i in tb.findChildren(QtWidgets.QTabWidget, "TabBar"):
        i.deleteLater()
    for i in tb.findChildren(QtWidgets.QWidgetAction):
        i.deleteLater()

    ToolBarWidget = WB_organizer(group)
    onOrientationChanged(ToolBarWidget)
    __parameters__.SetString("selectedWB", __selectedGroup__)
    print("SelectedGroup:", __selectedGroup__)


def WB_organizer(groupName = __strAll__):
    """This is the WBO widget.
    Users can decide in the Preferences if a WB shall be shown ...
    ... in the TabBar as Tab (checked)
    ... as Dropdown-Entry at the left Side of the TabBar (double not checked)
    .. not (once not checked)
    """
    def onGroupSelectedAction(group):
        return lambda checked=False, group=group: onGroupSelected(group)

    groupName = core.resolve_group(__groupedWB__, groupName)
    tb.clear()
    wbActions()
    
    w = QtWidgets.QTabWidget(tb)
    activeWB = Gui.activeWorkbench().__class__.__name__   # this is the currently active workbench

    # DropdownMenu for Groups ===========================================================
    global btn
    btn = QtWidgets.QPushButton(w)
    btn.setFlat(True)
    btn.setIcon(QtGui.QIcon(__pathIcons__ + "WBO_icon.svg"))
    btn.setStyleSheet("text-align: left;")
    showName = __parameters__.GetString("GroupStyle", "showName")
    if showName == "showName":
        if groupName == __strAll__:
            btn.setText("Select Group:")
        else:
            btn.setText(groupName)
    else:
        btn.setText("")
    menu = QtWidgets.QMenu(btn)
    btn.setMenu(menu)

    # Add some WB from the __strDrop__ group directly to the Groups-DropDown
    inGroupsDD = __groupedWB__.get(__strDrop__)
    if not inGroupsDD: inGroupsDD = {}  # prevents error in case __strDrop__ has been changed
    """ remove the active WB from the ones in the Dropdownlist. I think, we don't need this.
        It might confuse users as the dropdown list always changes somehow magically.

    if inGroupsDD and (activeWB in inGroupsDD):     # remove existing inGroupsDD WB
        inGroupsDD.remove(activeWB)
    else:
        inGroupsDD = []
    """
    for i in inGroupsDD:                         # Add the inGroupsDD WB
        if i in __actions__:
            menu.addAction(__actions__[i])

    menu.addSeparator()

    # Add the groups to the dropdown-menu
    for group in core.selectable_groups(__groupedWB__):
        gr = QAction(menu)
        gr.setText(core.group_label(group, __aliasNames__))
        gr.setData(group)
        gr.triggered.connect(onGroupSelectedAction(group))
        menu.addAction(gr)

    menu.addSeparator()

    pref = QAction(menu)
    pref.setText("Preferences ...")
    pref.setIcon(QtGui.QIcon(__pathIcons__ + "WBO_Prefs.svg"))
    pref.triggered.connect(onPreferences)
    menu.addAction(pref)

    help = QAction(menu)
    help.setText("Help ...")
    help.setIcon(QtGui.QIcon(__pathIcons__ + "WBO_help.svg"))
    help.triggered.connect(onHelp)
    menu.addAction(help)


    menu_width = menu.sizeHint().width()
    menu.setFixedWidth(menu_width + 20)

    # Now for the workbench-selector (dropdown or tabs)
    prefbutton  = __parameters__.GetString("PrefButton", "Dropdown")
    if prefbutton == 'Dropdown':
        # Dropdown ======================================================================
        global btnWB
        btnWB = QtWidgets.QPushButton(w)
        btnWB.setFlat(True)
        activeAction = __actions__.get(activeWB)
        if activeAction:
            btnWB.setIcon(activeAction.icon())
            btnWB.setText(activeAction.text())
        menu = QtWidgets.QMenu(btnWB)
        btnWB.setMenu(menu)

        for kind, value in core.dropdown_entries(__groupedWB__, groupName, __actions__):
            if kind == "separator":
                menu.addSeparator().setText(value)
            else:
                menu.addAction(__actions__[value])

        menu2_width = menu.sizeHint().width()
        menu.setFixedWidth(menu2_width + 10)
        btnWB.setFixedWidth(menu2_width + 10)
        btnWB.setStyleSheet("text-align: left;")
        w = btnWB

    else:
        # Tabs ==========================================================================
        w.setObjectName("TabBar")
        w.setDocumentMode(True)
        w.setUsesScrollButtons(True)
        w.tabBar().setDrawBase(True)

        for i in core.tab_workbenches(__groupedWB__, groupName, activeWB, __actions__):
            if __parameters__.GetString("Style") == "Icon":
                r = w.tabBar().addTab(__actions__[i].icon(), "")
            elif __parameters__.GetString("Style") == "Text":
                r = w.tabBar().addTab(__actions__[i].text())
            else:
                r = w.tabBar().addTab(__actions__[i].icon(), __actions__[i].text())
            w.tabBar().setTabData(r, i)
            w.tabBar().setTabToolTip(r, __actions__[i].text())

        for i in range(w.count()):
            if w.tabBar().tabData(i) == activeWB:
                w.tabBar().setCurrentIndex(i)

        def onTab(d):
            """Activate workbench on tab."""
            data = w.tabBar().tabData(d)
            if data:
                for i in __actions__:
                    if __actions__[i].data() == data:
                        __actions__[i].trigger()
            w.currentChanged.disconnect(onTab)

        w.currentChanged.connect(onTab)

    return [btn, w]

#==================================================================================================================================

def onWorkbenchActivated():
    """Populate the tabs toolbar."""
    for i in tb.findChildren(QtWidgets.QTabWidget, "TabBar"):
        i.deleteLater()
    for i in tb.findChildren(QtWidgets.QWidgetAction):
        i.deleteLater()
    global __selectedGroup__
    ToolBarWidget = WB_organizer(__selectedGroup__)
    onOrientationChanged(ToolBarWidget)


def onWorkbenchSelected(a):     # When a WB-Tab has been pressed.
    """Activate workbench on action."""
    data = a.data()
    if data:
        try:
            #Gui.doCommand('Gui.activateWorkbench("' + data + '")')
            Gui.activateWorkbench(data)
        except KeyError:
            pass


class WBList(QtWidgets.QListWidget):
    """List of the preferences dialog that hands drops and the [Del] key to callbacks.

    The drops are handled here instead of by Qt, because Qt5 and Qt6 differ in how
    a QListWidget moves its items. Qt itself never adds or removes items here.
    """
    def __init__(self, parent=None):
        QtWidgets.QListWidget.__init__(self, parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.dropSources = [self]   # lists whose items may be dropped here
        self.onDrop      = None     # called as onDrop(source, row) after a drop
        self.onDelete    = None     # called when [Del] is pressed

    def dropRow(self, event):
        """Position in the list where the drop indicator is."""
        pos  = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item = self.itemAt(pos)
        if item is None:
            return self.count()
        row = self.row(item)
        if pos.y() > self.visualItemRect(item).center().y():
            row += 1
        return row

    def dragEnterEvent(self, event):
        if event.source() in self.dropSources:
            QtWidgets.QListWidget.dragEnterEvent(self, event)
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() in self.dropSources:
            QtWidgets.QListWidget.dragMoveEvent(self, event)   # draws the drop indicator
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        source = event.source()
        if source in self.dropSources and self.onDrop:
            # A CopyAction keeps Qt from removing the dragged items from the source list.
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
            row = self.dropRow(event)
            self.setState(QtWidgets.QAbstractItemView.State.NoState)   # hides the drop indicator
            self.viewport().update()
            self.onDrop(source, row)
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Delete and self.onDelete:
            self.onDelete()
        else:
            QtWidgets.QListWidget.keyPressEvent(self, event)


class NameDelegate(QtWidgets.QStyledItemDelegate):
    """Editor for names in the lists of the preferences dialog.

    It shows the current name grey and selected, so the first key replaces it.
    The placeholder of an empty editor is the name that an empty entry restores.
    """
    untouched = ("QLineEdit { background-color: palette(base); color: grey; border: 1px solid palette(highlight);"
                 " selection-background-color: palette(base); selection-color: grey; }")
    edited    = "QLineEdit { background-color: palette(base); color: palette(text); border: 1px solid palette(highlight); }"

    def __init__(self, parent, placeholder):
        QtWidgets.QStyledItemDelegate.__init__(self, parent)
        self.placeholder = placeholder   # function(index) -> name shown in an empty editor

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setStyleSheet(self.untouched)   # an own background: FreeCAD's style sheets may make editors transparent
        editor.textEdited.connect(lambda text: editor.setStyleSheet(self.edited))
        return editor

    def setEditorData(self, editor, index):
        editor.setText(index.data())
        editor.setPlaceholderText(self.placeholder(index))
        editor.selectAll()


def setGroups(groups):
    """Store edited groups."""
    global __groupedWB__
    __groupedWB__ = groups
    saveMyWB()


def setAliases(aliases):
    """Store edited aliases and show them on the workbench actions."""
    global __aliasNames__
    __aliasNames__ = aliases
    core.save_json(__pathAliasFile__, __aliasNames__)
    wbList = Gui.listWorkbenches()
    for wb, action in __actions__.items():
        if wb in wbList:
            action.setText(core.display_name(wb, wbList[wb].MenuText, __aliasNames__))


def defaultName(wb):
    """Name of a workbench without alias."""
    wbList = Gui.listWorkbenches()
    return wbList[wb].MenuText if wb in wbList else wb


def setSelectedGroup(group):
    """Set the group shown in the toolbar."""
    global __selectedGroup__
    __selectedGroup__ = group
    __parameters__.SetString("selectedWB", group)


def prefDialog():
    """Preferences dialog."""
    wbActions()
    dialog = QtWidgets.QDialog(__mainWindow__)
    dialog.setModal(True)
    dialog.resize(1000, 650)
    dialog.setWindowTitle("WorkbenchOrganizer preferences")
    layout = QtWidgets.QVBoxLayout()
    dialog.setLayout(layout)
    grey = QtGui.QBrush(QtGui.QColor("grey"))
    blue = QtGui.QBrush(QtGui.QColor("#2f7fe0"))   # aliases; readable on light and dark themes
    #------------------------
    selector = WBList(dialog)
    selector.setItemDelegate(NameDelegate(selector, lambda index: defaultName(index.data(32))))
    selector.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    selector.setToolTip("Drag workbenches to sort them, or into a group to add them.\nUncheck workbenches to hide them.")
    selector.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

    groupList = WBList(dialog)
    groupList.setItemDelegate(NameDelegate(groupList, lambda index: index.data(32)))
    groupList.setToolTip("Drag a group to sort the groups dropdown.\nDouble-click a group to rename it.")

    memberList = WBList(dialog)
    memberList.dropSources = [memberList, selector]
    memberList.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    memberList.setToolTip("Drag workbenches here from the list of all workbenches.\nDrag them inside this list to sort them.\n[Del] removes them from the group.")

    btnClose = QtWidgets.QPushButton("Close", dialog)
    btnClose.setToolTip("Close the preferences dialog")
    btnClose.setDefault(True)

    btnHelp = QtWidgets.QPushButton(dialog)
    btnHelp.setToolTip("Get online help to the Workbench-Organizer")
    btnHelp.setIcon(QtGui.QIcon(__pathIcons__ + "WBO_help.svg"))
    btnHelp.setIconSize(QtCore.QSize(28, 28))
    btnHelp.setFlat(True)
    btnHelp.setStyleSheet("QPushButton { border: none; background: transparent; }")
    btnHelp.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    btnNewGroup = QtWidgets.QPushButton("New", dialog)
    btnNewGroup.setToolTip("Create a new group")

    btnDelGroup = QtWidgets.QPushButton("Delete", dialog)
    btnDelGroup.setToolTip("Delete the selected group")

    btnSeparator = QtWidgets.QPushButton("Add Separator", dialog)
    btnSeparator.setToolTip("Insert a separator below the selected workbench")

    btnRemove = QtWidgets.QPushButton("Remove", dialog)
    btnRemove.setToolTip("Remove the selected workbenches from the group")

    explication = QtWidgets.QLabel("<i>Confirm your data entry with [Shift] + [Return]<br>to keep the dialog window open.</i>")
    explication.setWordWrap(True)

    lineEdit = QtWidgets.QLineEdit(dialog)
    lineEdit.setGeometry(QtCore.QRect(30, 40, 211, 22))
    lineEdit.setObjectName("Length of tab")
    lineEdit.setFixedWidth(100)
    lineEdit.setToolTip("Use this to set the length of the tabbar\nif you want to place the Workbench Organizer\ni.e. on top of the header line of FreeCAD.")
    #lineEdit.setIconText("Length of freefloating tab")
    lineEdit.setText(str(__floatingWidgetWidth__))
    #----------------------- Left Area: groups and their workbenches
    groupsPanel = QtWidgets.QGroupBox("Groups:")
    groupsLayout = QtWidgets.QVBoxLayout()
    groupsLayout.addWidget(groupList)
    groupsButtons = QtWidgets.QHBoxLayout()
    groupsButtons.addWidget(btnNewGroup)
    groupsButtons.addWidget(btnDelGroup)
    groupsButtons.addStretch()
    groupsLayout.addLayout(groupsButtons)
    groupsPanel.setLayout(groupsLayout)

    memberPanel = QtWidgets.QGroupBox("Workbenches in the group:")
    memberLayout = QtWidgets.QVBoxLayout()
    memberLayout.addWidget(memberList)
    memberButtons = QtWidgets.QHBoxLayout()
    memberButtons.addWidget(btnSeparator)
    memberButtons.addWidget(btnRemove)
    memberButtons.addStretch()
    dragHint = QtWidgets.QLabel("<i>Drag to add →</i>")
    dragHint.setToolTip("Drag workbenches from the list of all workbenches into this group.")
    memberButtons.addWidget(dragHint)
    memberLayout.addLayout(memberButtons)
    memberPanel.setLayout(memberLayout)

    l1 = QtWidgets.QVBoxLayout()
    l1.addWidget(groupsPanel, 2)
    l1.addWidget(memberPanel, 3)

    #----------------------- Center Area: all workbenches
    allPanel = QtWidgets.QGroupBox("All workbenches (double-click to rename):")
    allLayout = QtWidgets.QVBoxLayout()
    allLayout.addWidget(selector)
    allPanel.setLayout(allLayout)

    #----------------------- Right Area ----------------------------
    showGRPpanelLayout = QtWidgets.QVBoxLayout()
    showGRPpanel = QtWidgets.QGroupBox("Show group name:")
    showGRPpanel.setLayout(showGRPpanelLayout)
    r6 = QtWidgets.QRadioButton("show name", showGRPpanel)
    r6.setObjectName("showName")
    r6.setToolTip("Show the selected group name in the title")
    r7 = QtWidgets.QRadioButton("hide name", showGRPpanel)
    r7.setObjectName("hideName")
    r7.setToolTip("Show just the icon to reduce button size")
    showGRPpanelLayout.addWidget(r6)
    showGRPpanelLayout.addWidget(r7)
    #--------------------------------------------------------------
    showWBpanelLayout = QtWidgets.QVBoxLayout()
    showWBpanel = QtWidgets.QGroupBox("Show Workbenches as:")
    showWBpanel.setLayout(showWBpanelLayout)
    r8 = QtWidgets.QRadioButton("Tabs", showWBpanel)
    r8.setObjectName("Tabs")
    r8.setToolTip("Show the workbenches in a tabbar")
    r9 = QtWidgets.QRadioButton("Dropdown", showWBpanel)
    r9.setObjectName("Dropdown")
    r9.setToolTip("Show the workbenches in a dropdownlist")
    showWBpanelLayout.addWidget(r9)
    showWBpanelLayout.addWidget(r8)
    #--------------------------------------------------------------
    stylePanelLayout = QtWidgets.QVBoxLayout()
    stylePanel = QtWidgets.QGroupBox("Tabs-Style:")
    stylePanel.setLayout(stylePanelLayout)
    r0 = QtWidgets.QRadioButton("Icon", stylePanel)
    r0.setObjectName("Icon")
    r0.setToolTip("Show just icon in tabbar.")
    r1 = QtWidgets.QRadioButton("Text", stylePanel)
    r1.setObjectName("Text")
    r1.setToolTip("Show just text in tabbar.")
    r2 = QtWidgets.QRadioButton("Icon and text", stylePanel)
    r2.setObjectName("IconText")
    r2.setToolTip("Show icon and text in tabbar")
    stylePanelLayout.addWidget(r0)
    stylePanelLayout.addWidget(r1)
    stylePanelLayout.addWidget(r2)

    styleLengthLayout = QtWidgets.QVBoxLayout()
    styleLengthPanel = QtWidgets.QGroupBox("Length when free floating:")
    styleLengthPanel.setLayout(styleLengthLayout)
    styleLengthLayout.addWidget(lineEdit)
    styleLengthLayout.addWidget(explication)
    #-----------------------
    buttonsPanel = QtWidgets.QHBoxLayout()    # Close-Button unten im rechten Bereich
    buttonsPanel.addStretch(1)
    buttonsPanel.addWidget(btnClose)
    #-----------------------
    l4 = QtWidgets.QVBoxLayout()
    topRow = QtWidgets.QHBoxLayout()          # Help-Button rechts oben
    topRow.addWidget(showGRPpanel, 1)
    topRow.addWidget(btnHelp, 0, QtCore.Qt.AlignmentFlag.AlignTop)
    l4.addLayout(topRow)
    l4.addWidget(showWBpanel)
    l4.addWidget(stylePanel)
    l4.addWidget(styleLengthPanel)
    l4.addStretch()
    l4.addLayout(buttonsPanel)
    optionsArea = QtWidgets.QWidget(dialog)
    optionsArea.setLayout(l4)
    optionsArea.setMaximumWidth(230)
    l4.setContentsMargins(0, 0, 0, 0)
    #--------------------------------------
    l5 = QtWidgets.QHBoxLayout()
    l5.addLayout(l1, 3)             # Groups and their workbenches
    l5.addWidget(allPanel, 3)       # All List
    l5.addWidget(optionsArea, 2)    # Radio-Buttons

    layout.addLayout(l5)

    def onAccepted():
        """Close dialog on button close."""
        dialog.done(1)

    def onFinished():
        """Delete dialog on close."""
        dialog.deleteLater()

    #----------------------- groups and their workbenches
    def currentGroup():
        """Group selected in the groups list."""
        item = groupList.currentItem()
        return item.data(32) if item else None

    def entriesOf(listWidget):
        return [listWidget.item(r).data(32) for r in range(listWidget.count())]

    def selectRows(listWidget, first, count):
        listWidget.clearSelection()
        for r in range(first, first + count):
            listWidget.item(r).setSelected(True)
        if count:
            listWidget.setCurrentRow(first, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate)

    def memberItem(entry):
        """List item for a workbench or a separator of a group."""
        item = QtWidgets.QListWidgetItem()
        item.setData(32, entry)
        label = core.separator_label(entry)
        if label is not None:
            item.setText("──── " + label + " ────" if label else "────────────")
            item.setForeground(grey)
            item.setToolTip("Separator")
        elif entry in __actions__:
            item.setText(__actions__[entry].text())
            item.setIcon(__actions__[entry].icon())
            if core.has_alias(entry, __aliasNames__):
                item.setForeground(blue)
                item.setToolTip("Alias of '{}'".format(defaultName(entry)))
        else:
            item.setText(entry)
            item.setForeground(grey)
            item.setToolTip("This workbench is not installed.")
        return item

    def fillGroups(select=None):
        """Show the groups and select the group select (default: the toolbar's group)."""
        if select is None:
            select = __selectedGroup__
        groupList.blockSignals(True)
        groupList.clear()
        # First the workbenches shown directly in the groups dropdown, as in the dropdown itself.
        item = QtWidgets.QListWidgetItem("In groups dropdown", groupList)
        item.setData(32, __strDrop__)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled)
        font = item.font()
        font.setItalic(True)
        item.setFont(font)
        item.setIcon(QtGui.QIcon(__pathIcons__ + "WBO_icon.svg"))
        item.setToolTip("Workbenches shown directly in the groups dropdown, above the groups.")
        if select == __strDrop__:
            groupList.setCurrentItem(item)
        for group in core.selectable_groups(__groupedWB__):
            item = QtWidgets.QListWidgetItem(core.group_label(group, __aliasNames__), groupList)
            item.setData(32, group)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            if group == __strAll__:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
                item.setToolTip("All workbenches, sorted in the list in the middle.")
                if core.has_alias(group, __aliasNames__):
                    item.setForeground(blue)
            if group == select:
                groupList.setCurrentItem(item)
        groupList.blockSignals(False)
        fillMembers()

    def fillMembers(first=0, count=0):
        """Show the workbenches of the selected group."""
        group = currentGroup()
        editable = group is not None and group != __strAll__
        memberList.clear()
        if editable:
            for entry in __groupedWB__.get(group) or []:
                if entry != "":
                    memberList.addItem(memberItem(entry))
            if group == __strDrop__:
                memberPanel.setTitle("Workbenches in the groups dropdown:")
            else:
                memberPanel.setTitle("Workbenches in '{}':".format(group))
            selectRows(memberList, first, count)
        elif group == __strAll__:
            memberPanel.setTitle("'{}' holds all workbenches.".format(core.group_label(group, __aliasNames__)))
        else:
            memberPanel.setTitle("Workbenches in the group:")
        memberList.setEnabled(editable)
        btnSeparator.setEnabled(editable and group != __strDrop__)   # the groups dropdown shows no separators
        btnDelGroup.setEnabled(editable and group != __strDrop__)
        onMemberSelectionChanged()

    def onMemberSelectionChanged():
        btnRemove.setEnabled(memberList.isEnabled() and bool(memberList.selectedItems()))

    def storeMembers(entries, first=0, count=0):
        """Save the workbenches of the selected group and show them again."""
        setGroups(core.set_members(__groupedWB__, currentGroup(), entries))
        fillMembers(first, count)
        onWorkbenchActivated()

    def showError(title, error):
        QtWidgets.QMessageBox.warning(dialog, title, str(error))

    def onNewGroup():
        name, ok = QtWidgets.QInputDialog.getText(dialog, "New group", "Name of the new group:")
        if not ok:
            return
        name = name.strip()
        try:
            groups = core.add_group(__groupedWB__, name)
        except ValueError as e:
            showError("New group", e)
            return
        setGroups(groups)
        fillGroups(name)
        onWorkbenchActivated()

    def onDeleteGroup():
        group = currentGroup()
        if group is None or group in (__strAll__, __strDrop__):
            return
        answer = QtWidgets.QMessageBox.question(dialog, "Delete group", "Delete the group '{}'?".format(group))
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        setGroups(core.delete_group(__groupedWB__, group))
        if __selectedGroup__ == group:
            setSelectedGroup(__strAll__)
        fillGroups(__strAll__)
        onWorkbenchActivated()

    def onGroupRenamed(item):
        old = item.data(32)
        new = item.text().strip()
        if not new and old != __strAll__:
            new = old   # an empty name keeps the group's name
        if old == __strAll__:
            # 'All' keeps its key in the config file and gets an alias instead.
            setAliases(core.set_alias(__aliasNames__, old, new, default=old))
            onWorkbenchActivated()
            QtCore.QTimer.singleShot(0, lambda: fillGroups(old))
            return
        try:
            groups = core.rename_group(__groupedWB__, old, new)
        except ValueError as e:
            showError("Rename group", e)
            new = old
        else:
            setGroups(groups)
            if __selectedGroup__ == old:
                setSelectedGroup(new)
            onWorkbenchActivated()
        # Rebuild the list after Qt has finished editing the item.
        QtCore.QTimer.singleShot(0, lambda: fillGroups(new))

    def onGroupDropped(source, row):
        group = currentGroup()
        if group is None or group == __strDrop__:
            return
        # The groups dropdown entry stays on top; sort only the groups below it.
        order, first, count = core.move_entries(entriesOf(groupList)[1:], [groupList.currentRow() - 1], max(row - 1, 0))
        setGroups(core.reorder_groups(__groupedWB__, order))
        fillGroups(group)
        onWorkbenchActivated()

    def onMembersDropped(source, row):
        entries = entriesOf(memberList)
        if source is memberList:
            rows = [memberList.row(i) for i in memberList.selectedItems()]
            entries, first, count = core.move_entries(entries, rows, row)
        else:
            new = [i.data(32) for i in sorted(source.selectedItems(), key=source.row)]
            entries, first, count = core.insert_entries(entries, new, row)
        storeMembers(entries, first, count)

    def onRemoveMembers():
        rows = set(memberList.row(i) for i in memberList.selectedItems())
        if rows:
            storeMembers([e for r, e in enumerate(entriesOf(memberList)) if r not in rows])

    def onSeparator():
        row = memberList.currentRow() + 1 if memberList.currentItem() else memberList.count()
        entries, first, count = core.insert_entries(entriesOf(memberList), [core.SEPARATOR], row)
        storeMembers(entries, first, count)

    #----------------------- all workbenches
    def styleWorkbenchItem(item):
        """Show the name of a workbench in the list of all workbenches; aliases in blue."""
        wb = item.data(32)
        item.setText(__actions__[wb].text())
        item.setData(51, item.text())   # to tell a rename from a click on the check box
        if core.has_alias(wb, __aliasNames__):
            item.setForeground(blue)
            item.setToolTip("Alias of '{}'. Double-click to rename it,\nleave the name empty to remove the alias.".format(defaultName(wb)))
        else:
            item.setData(QtCore.Qt.ItemDataRole.ForegroundRole, None)
            item.setToolTip("Double-click to rename the workbench.")

    def onWorkbenchRenamed(item):
        wb = item.data(32)
        setAliases(core.set_alias(__aliasNames__, wb, item.text(), default=defaultName(wb)))
        selector.blockSignals(True)
        styleWorkbenchItem(item)
        selector.blockSignals(False)
        fillMembers()
        onWorkbenchActivated()

    def onItemChanged(item=None):
        """Save workbench list state."""
        if item and item.text() != item.data(51):
            onWorkbenchRenamed(item)
            return
        if item:
            selector.blockSignals(True)
            if item.data(50) == "Unchecked":
                item.setCheckState(QtCore.Qt.CheckState.Checked)
                item.setData(50, "Checked")
            else:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
                item.setData(50, "Unchecked")
            selector.blockSignals(False)
        disabled = []
        for index in range(selector.count()):
            if selector.item(index).checkState() != QtCore.Qt.CheckState.Checked:
                disabled.append(selector.item(index).data(32))
        __groupedWB__.update({__strDisabled__: disabled})
        saveMyWB()

        onWorkbenchActivated()

    def onAllDropped(source, row):
        """Sort the list of all workbenches."""
        rows = [selector.row(i) for i in selector.selectedItems()]
        if not rows:
            return
        entries, first, count = core.move_entries(entriesOf(selector), rows, row)
        selector.blockSignals(True)
        items = {selector.item(r).data(32): selector.takeItem(r) for r in reversed(range(selector.count()))}
        for wb in entries:
            selector.addItem(items[wb])
        selector.blockSignals(False)
        selectRows(selector, first, count)
        # Workbenches that are not installed aren't listed, but keep them in 'All'.
        hidden = [wb for wb in __groupedWB__.get(__strAll__) or [] if wb not in items]
        __groupedWB__.update({__strAll__: core.terminated(entries + hidden)})
        saveMyWB()
        onItemChanged()

    #----------------------- options
    def on_lineEdit_clicked():
        global __floatingWidgetWidth__
        # if self.lineEdit.textChanged():
        __floatingWidgetWidth__ = int(lineEdit.displayText())
        __parameters__.SetString("floatingWidth", str(__floatingWidgetWidth__))
        onWorkbenchActivated()


    def ongroupPanel(r):
        """Set Groups button style."""
        if r:
            for i in showGRPpanel.findChildren(QtWidgets.QRadioButton):
                if i.isChecked():
                    __parameters__.SetString("GroupStyle", i.objectName())
            onWorkbenchActivated()

    def onshowWBpanel(r):
        """Set pref button."""
        if r:
            for i in showWBpanel.findChildren(QtWidgets.QRadioButton):
                if i.isChecked():
                    __parameters__.SetString("PrefButton", i.objectName())
            onWorkbenchActivated()

    def onstylePanel(r):
        """Set TabBar style."""
        if r:
            for i in stylePanel.findChildren(QtWidgets.QRadioButton):
                if i.isChecked():
                    __parameters__.SetString("Style", i.objectName())
            onWorkbenchActivated()


    unchecked = __groupedWB__.get(__strDisabled__)
    if not unchecked: unchecked = {}  # prevents error in case __strDisabled__ has been changed
    position  = __groupedWB__.get(__strAll__)
    if not position: position = {}    # prevents error in case __strAll__ has been changed


    # build up the list of WB and set the CheckState
    for i in position:
        if i in __actions__:
            item = QtWidgets.QListWidgetItem(selector)
            item.setIcon(__actions__[i].icon())
            item.setData(32, __actions__[i].data())
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            styleWorkbenchItem(item)
            if __actions__[i].data() in position:
                item.setCheckState(QtCore.Qt.CheckState.Checked)
                item.setData(50, "Checked")
            if __actions__[i].data() in unchecked:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
                item.setData(50, "Unchecked")

    fillGroups()

    # set the radio buttons to the stored values
    groupStyle = __parameters__.GetString("GroupStyle", "showName")
    if groupStyle == "showName":
        r6.setChecked(True)
    else:
        r7.setChecked(True)

    style = __parameters__.GetString("Style")
    if style == "Text":
        r1.setChecked(True)
    elif style == "IconText":
        r2.setChecked(True)
    else:
        r0.setChecked(True)


    prefbutton = __parameters__.GetString("PrefButton", "Tabs")
    if prefbutton == "Tabs":
        r8.setChecked(True)
    else:
        r9.setChecked(True)

    r6.toggled.connect(ongroupPanel)
    r7.toggled.connect(ongroupPanel)

    r8.toggled.connect(onshowWBpanel)
    r9.toggled.connect(onshowWBpanel)

    r0.toggled.connect(onstylePanel)
    r1.toggled.connect(onstylePanel)
    r2.toggled.connect(onstylePanel)

    groupList.onDrop   = onGroupDropped
    groupList.onDelete = onDeleteGroup
    memberList.onDrop   = onMembersDropped
    memberList.onDelete = onRemoveMembers
    groupList.currentItemChanged.connect(lambda current, previous: fillMembers())
    groupList.itemChanged.connect(onGroupRenamed)
    btnNewGroup.clicked.connect(onNewGroup)
    btnDelGroup.clicked.connect(onDeleteGroup)
    btnSeparator.clicked.connect(onSeparator)
    btnRemove.clicked.connect(onRemoveMembers)
    memberList.itemSelectionChanged.connect(onMemberSelectionChanged)

    btnHelp.clicked.connect(onHelp)
    selector.onDrop = onAllDropped
    selector.itemChanged.connect(onItemChanged)
    dialog.finished.connect(onFinished)
    btnClose.clicked.connect(onAccepted)
    lineEdit.returnPressed.connect(on_lineEdit_clicked) #connection lineEdit

    return dialog


def onPreferences():
    """Open the preferences dialog."""
    dialog = prefDialog()
    dialog.show()


def onHelp():
    """Open a help page."""
    webbrowser.open("https://github.com/Palmstroemen/WB_Organizer/wiki")

#==================================================================================================================================

def accessoriesMenu():
    """Add WorkbenchOrganizer preferences to accessories menu."""
    pref = QAction(__mainWindow__)
    pref.setText("WorkbenchOrganizer")
    pref.setObjectName("WorkbenchOrganizer")
    pref.triggered.connect(onPreferences)
    try:
        import AccessoriesMenu
        AccessoriesMenu.addItem("WorkbenchOrganizer")
    except ImportError:
        a = __mainWindow__.findChild(QAction, "AccessoriesMenu")
        if a:
            a.menu().addAction(pref)
        else:
            mb = __mainWindow__.menuBar()
            actionAccessories = QAction(__mainWindow__)
            actionAccessories.setObjectName("AccessoriesMenu")
            actionAccessories.setIconText("Accessories")
            menu = QtWidgets.QMenu()
            actionAccessories.setMenu(menu)
            menu.addAction(pref)

            def addMenu():
                """Add accessories menu to the menu bar."""
                mb.addAction(actionAccessories)
                actionAccessories.setVisible(True)

            addMenu()
            __mainWindow__.workbenchActivated.connect(addMenu)


def onClose():
    """Remove tabs toolbar on FreeCAD close."""
    g = App.ParamGet("User parameter:BaseApp/Workbench/Global/Toolbar")
    g.RemGroup("Tabs")


def onStart():
    """Start TabBar."""
    start = False
    try:
        __mainWindow__.workbenchActivated
        __mainWindow__.mainWindowClosed
        global tb
        tb = __mainWindow__.findChild(QtWidgets.QToolBar, "Tabs")
        tb.orientation
        start = True
    except AttributeError:
        pass
    if start:
        t.stop()
        t.deleteLater()
        accessoriesMenu()
        onWorkbenchActivated()
        __tabActions__.triggered.connect(onWorkbenchSelected)
        __mainWindow__.mainWindowClosed.connect(onClose)
        __mainWindow__.workbenchActivated.connect(onWorkbenchActivated)
        tb.orientationChanged.connect(onWorkbenchActivated)
        tb.topLevelChanged.connect(onWorkbenchActivated)


def onPreStart():
    """Improve start reliability and maintain FreeCAD 0.16 support."""
    if App.Version()[1] < "17":
        onStart()
    else:
        if __mainWindow__.property("eventLoop"):
            onStart()


t = QtCore.QTimer()
t.timeout.connect(onPreStart)
t.start(500)