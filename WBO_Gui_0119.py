# TabBar widget for FreeCAD
# Copyright (C) 2015, 2016, 2017, 2018 triplus @ FreeCAD
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
import FreeCADGui as Gui
import FreeCAD as App
from PySide import QtGui
from PySide import QtCore
import os
import json

__strAll__ = "Alle"
__strNew__ = "Neu"
__strLost__= "Verloren gegangen"
__strDrop__= "In Dropdown"

__pathGroupFile__ = os.path.join(App.getUserAppDataDir(),"Mod\\TabBar\\MyWorkbenches.txt")
__pathIcons__     = os.path.dirname(__file__) + "\\Resources\\icons\\"
__pathToolbar__   = "User parameter:BaseApp/Workbench/Global/Toolbar"

__parameters__    = App.ParamGet("User parameter:BaseApp/TabBar")
__groupedWB__     = {}
__newWB__         = []
__justWB__        = []

__actions__       = {}
__mainWindow__    = Gui.getMainWindow()
__tabActions__    = QtGui.QActionGroup(__mainWindow__)
__selectedGroup__ = __strAll__      # the currently selected Group

__floatingWidgetWidth__ = 1000


def openMyWB():
    WB = Gui.listWorkbenches()
    __justWB__ = list(WB)

    # Schreiben der formatierten Daten in eine Datei
    if not os.path.exists(__pathGroupFile__):
        print("File not found: generating new File.")
        __groupedWB__ = {__strNew__: __justWB__, __strAll__: __justWB__, __strLost__: []}
        # Formatieren der Daten mit Einrückung
        formatted_data = json.dumps(__groupedWB__, indent=4)

        with open(__pathGroupFile__, 'w') as f:
            f.write(formatted_data)
	
    else:	# a file already exists. Check for new and lost Workbenches
        with open(__pathGroupFile__, 'r') as f:
            __groupedWB__ = json.load(f)
            loadedAll = __groupedWB__.get(__strAll__)
            __groupedWB__.update({__strNew__: []})
            __groupedWB__.update({__strAll__: __justWB__})
            lostWB    = [wb for wb in loadedAll]
            for wb in WB:
                if wb in loadedAll:
                    lostWB.remove(wb)
                else:
                    __newWB__.append(wb)
	
            if lostWB.__len__() > 0:
                __groupedWB__.update({__strLost__: lostWB})
	
            if __newWB__.__len__() > 0:
                __groupedWB__.update({__strNew__: __newWB__})
	
            formatted_data = json.dumps(__groupedWB__, indent=4)
		
            with open(__pathGroupFile__, 'w') as f:
                f.write(formatted_data)
    return __groupedWB__
__groupedWB__     = openMyWB()


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
        icon = QtGui.QIcon(QtGui.QPixmap(icon))
    else:
        icon = QtGui.QIcon(QtGui.QPixmap(i))
    if icon.isNull():
        icon = QtGui.QIcon(":/icons/freecad")
    return icon


def wbActions():
    """Create workbench actions."""
    wbList = Gui.listWorkbenches()
    for i in wbList:
        if i not in __actions__:
            try:
                action = QtGui.QAction(__tabActions__)
                action.setCheckable(True)
                action.setText(wbList[i].MenuText)
                action.setData(i)
                action.setIcon(wbIcon(wbList[i].Icon))
                __actions__[i] = action
            except:  # there is one 'none'-WB without an icon. We remove this here.
                action.setIcon(QtGui.QIcon(":/icons/freecad"))


def defaults():
    """Sorted string of available workbenches."""
    d = Gui.listWorkbenches()          # ['WB2': <object at ...>, 'WB7': ..]
    d = list(d)                        # ['WB2', 'WB7', ...]
    d.sort()                           # ['WB1', 'WB2', ...]
    d = ",".join(d)                    # 'WB1,WB2,WB3, ...'
    return d


def onOrientationChanged(w):
    """Set the tabs orientation."""
    btn = w[0]
    tab = w[1]
    orientation = __parameters__.GetString("Orientation", "Auto")


    def layout():
        """Support menu for West and East orientations."""
        wid = QtGui.QWidget()
        lo = QtGui.QVBoxLayout()
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
        tb.resize(__floatingWidgetWidth__, tb.height())
        orientation = "South"

    if orientation == "North":
        tb.addWidget(btn)
        tb.addWidget(tab)
        tab.setTabPosition(QtGui.QTabWidget.North)
        #tab.setCornerWidget(btn)
    elif orientation == "South":
        tb.addWidget(btn)
        tb.addWidget(tab)
        tab.setTabPosition(QtGui.QTabWidget.South)
        #tab.setCornerWidget(btn)
    elif orientation == "West":
        tab.setTabPosition(QtGui.QTabWidget.West)
        layout()
    elif orientation == "East":
        tab.setTabPosition(QtGui.QTabWidget.East)
        layout()
    else:
        pass

    prefbutton = __parameters__.GetString("PrefButton", "On")
    if prefbutton == "On":
        btn.show()
    else:
        btn.hide()


def onGroupSelected(group):
    """Group selected"""
    global __selectedGroup__
    __selectedGroup__ = group
    print("onGroup selected:",__selectedGroup__)

    btn.setText(group)

    for i in tb.findChildren(QtGui.QTabWidget, "TabBar"):
        i.deleteLater()
    for i in tb.findChildren(QtGui.QWidgetAction):
        i.deleteLater()

    ToolBarWidget = tabs(group)
    onOrientationChanged(ToolBarWidget)


def tabs(groupName = __strAll__):
    """Tabs widget."""
    # The user can decide in the Preferences if a WB shall be shown ...
    # ... in the TabBar as Tab (checked)
    # ... as Dropdown-Entry at the left Side of the TabBar (double not checked)
    # ... not (once not checked)
    print("tabs:",groupName)

    def onGroupSelectedAction(group):
        return lambda checked=False, group=group: onGroupSelected(group)

    tb.clear()
    wbActions()
    default = defaults()
    
    w = QtGui.QTabWidget(tb)
    active = Gui.activeWorkbench().__class__.__name__   # this is the currently active workbench

    # DropdownMenu ===========================================================
    global btn
    btn = QtGui.QPushButton(w)
    btn.setFlat(True)
    btn.setIcon(QtGui.QIcon(__pathIcons__ + "TabBar_Start.svg"))
    if groupName == __strAll__:
        btn.setText("Select Group:")
    else:
        btn.setText(groupName)
    menu = QtGui.QMenu(btn)
    btn.setMenu(menu)

    # Add some WB from the __strDrop__ group directly to the Groups-DropDown
    inGroupsDD = __groupedWB__.get(__strDrop__)
    """ remove the active WB from the ones in the Dropdownlist. I think, we don't need this.
        It might confuse users as the dropdown list always changes somehow magically.

    if inGroupsDD and (active in inGroupsDD):     # remove existing inGroupsDD WB
        inGroupsDD.remove(active)
    else:
        inGroupsDD = []
    """
    for i in inGroupsDD:                         # Add the inGroupsDD WB
        if i in __actions__:
            menu.addAction(__actions__[i])

    menu.addSeparator()

    # Add the groups to the dropdown-menu
    for group in __groupedWB__.keys():
        if group not in [__strDrop__, __strLost__, __strNew__]:
            gr = QtGui.QAction(menu)
            gr.setText(group)
            gr.setData(group)
            gr.triggered.connect(onGroupSelectedAction(group))
            #gr.triggered.connect(functools.partial(onGroupSelectedAction, group))
            menu.addAction(gr)

    menu.addSeparator()

    pref = QtGui.QAction(menu)
    pref.setText("Preferences")
    pref.triggered.connect(onPreferences)
    menu.addAction(pref)

    # Tabs ==========================================================================
    # enabled = __parameters__.GetString("Enabled", default)   # enabled = 'WB1,WB2,...'
    # enabled = enabled.split(",")                # enabled = ['WB1', 'WB2', ...]
    group = groupName
    enabled = __groupedWB__.get(group)

    #unchecked = __parameters__.GetString("Unchecked")        # not checked in the Preferences
    #unchecked = unchecked.split(",")            # just the unchecked. ['WB5']

    w.setObjectName("TabBar")
    w.setDocumentMode(True)
    w.setUsesScrollButtons(True)
    w.tabBar().setDrawBase(True)

    #default = default.split(",")
    #for i in default:
    #    if (i not in inGroupsDD and
    #            i not in enabled and
    #            i not in unchecked):
    #        enabled.append(i)

    # Add temporarily the active WB to the Tabs if it's not already there and remove it later again.
    tempAddedWB = ""                
    if active not in enabled:       
        enabled.append(active)      
        tempAddedWB = active

    for i in enabled:
        if i in __actions__:
            if __parameters__.GetString("Style") == "IconText":
                r = w.tabBar().addTab(__actions__[i].icon(), __actions__[i].text())
            elif __parameters__.GetString("Style") == "Text":
                r = w.tabBar().addTab(__actions__[i].text())
            else:
                r = w.tabBar().addTab(__actions__[i].icon(), None)
            w.tabBar().setTabData(r, i)
            w.tabBar().setTabToolTip(r, __actions__[i].text())

    for i in range(w.count()):
        if w.tabBar().tabData(i) == active:
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

    # Remove the temporarily added Tab again
    if tempAddedWB:
        enabled.remove(tempAddedWB)

    return [btn, w]


def onWorkbenchActivated():
    """Populate the tabs toolbar."""
    for i in tb.findChildren(QtGui.QTabWidget, "TabBar"):
        i.deleteLater()
    for i in tb.findChildren(QtGui.QWidgetAction):
        i.deleteLater()
    global __selectedGroup__
    ToolBarWidget = tabs(__selectedGroup__)
    onOrientationChanged(ToolBarWidget)


def onWorkbenchSelected(a):     # When a WB-Tab has been pressed.
    """Activate workbench on action."""
    print("------------------")
    data = a.data()
    if data:
        try:
            #Gui.doCommand('Gui.activateWorkbench("' + data + '")')
            Gui.activateWorkbench(data)
        except KeyError:
            pass


import subprocess
import sys

def open_file_in_editor():
    """A first, simple solution to edit the config-file that defines the groups"""
    try:
        if sys.platform.startswith('linux'):
            subprocess.run(['nano', __pathGroupFile__])
        elif sys.platform.startswith('win'):
            subprocess.run(['notepad', __pathGroupFile__])
        elif sys.platform.startswith('darwin'):  # MacOSX
            subprocess.run(['open', '-t', __pathGroupFile__])
        else:
            print("Betriebssystem wird nicht unterstützt.")
    except Exception as e:
        print(f"Fehler beim Öffnen der Datei: {e}")


def prefDialog():
    """Preferences dialog."""
    wbActions()
    dialog = QtGui.QDialog(__mainWindow__)
    dialog.setModal(True)
    dialog.resize(800, 450)
    dialog.setWindowTitle("Workbench Organizer preferences")
    layout = QtGui.QVBoxLayout()
    dialog.setLayout(layout)
    #------------------------
    selector = QtGui.QListWidget(dialog)
    selector.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    btnClose = QtGui.QPushButton("Close", dialog)
    btnClose.setToolTip("Close the preferences dialog")
    btnClose.setDefault(True)
    btnUp = QtGui.QPushButton(dialog)
    btnUp.setToolTip("Move selected item up")
    btnUp.setIcon(QtGui.QIcon(__pathIcons__ + "TabBar_MoveUp"))
    btnDown = QtGui.QPushButton(dialog)
    btnDown.setToolTip("Move selected item down")
    btnDown.setIcon(QtGui.QIcon(__pathIcons__ + "TabBar_MoveDown"))
    btnFile = QtGui.QPushButton(dialog)
    btnFile.setToolTip("Open and Edit the config-file")
    btnFile.setText("Open config-file")
    #--------------------------------------------------------------
    l0 = QtGui.QVBoxLayout()
    g0 = QtGui.QGroupBox("Style:")
    g0.setLayout(l0)
    r0 = QtGui.QRadioButton("Icon", g0)
    r0.setObjectName("Icon")
    r0.setToolTip("TabBar icon style")
    r1 = QtGui.QRadioButton("Text", g0)
    r1.setObjectName("Text")
    r1.setToolTip("TabBar text style")
    r2 = QtGui.QRadioButton("Icon and text", g0)
    r2.setObjectName("IconText")
    r2.setToolTip("TabBar icon and text style")
    l0.addWidget(r0)
    l0.addWidget(r1)
    l0.addWidget(r2)
    #-----------------------
    l1 = QtGui.QVBoxLayout()
    g1 = QtGui.QGroupBox("Tab orientation:")
    g1.setLayout(l1)
    r3 = QtGui.QRadioButton("Auto", g1)
    r3.setObjectName("Auto")
    r3.setToolTip("Set based on the orientation")
    r4 = QtGui.QRadioButton("Top", g1)
    r4.setObjectName("North")
    r4.setToolTip("Tabs at top")
    r5 = QtGui.QRadioButton("Bottom", g1)
    r5.setObjectName("South")
    r5.setToolTip("Tabs at bottom")
    r6 = QtGui.QRadioButton("Left", g1)
    r6.setObjectName("West")
    r6.setToolTip("Tabs at left")
    r7 = QtGui.QRadioButton("Right", g1)
    r7.setObjectName("East")
    r7.setToolTip("Tabs at right")
    l1.addWidget(r3)
    l1.addWidget(r4)
    l1.addWidget(r5)
    l1.addWidget(r6)
    l1.addWidget(r7)
    #-----------------------
    l2 = QtGui.QHBoxLayout()    # die untere Leiste mit den Up/down und Close-Buttons
    l2.addWidget(btnUp)
    l2.addWidget(btnDown)
    l2.addWidget(btnFile)
    l2.addStretch(1)
    l2.addWidget(btnClose)
    #-----------------------
    l3 = QtGui.QHBoxLayout()
    l3.addStretch()
    l4 = QtGui.QVBoxLayout()
    l4.addWidget(g0)
    l4.addWidget(g1)
    #-----------------------
    l6 = QtGui.QVBoxLayout()
    g6 = QtGui.QGroupBox("Preferences button on tabbar:")
    g6.setLayout(l6)
    r8 = QtGui.QRadioButton("On", g6)
    r8.setObjectName("On")
    r8.setToolTip("A preference button appears on the right/bottom of the tabbar")
    r9 = QtGui.QRadioButton("Off", g6)
    r9.setObjectName("Off")
    r8.setToolTip("No button on the tabbar (only via menu Tools -> Acessories")
    l6.addWidget(r8)
    l6.addWidget(r9)
    l4.addWidget(g6)
    l4.addStretch()
    l4.insertLayout(0, l3)
    #----------------------- Center Area
    m1 = QtGui.QVBoxLayout()
    mg1= QtGui.QGroupBox("Define your groups here:")
    mg1.setLayout(m1)
    #--------------------------------------
    l5 = QtGui.QHBoxLayout()
    l5.addWidget(selector)      # All List
    l5.insertLayout(1, m1)            # Groups funktioniert noch nicht
    l5.insertLayout(1, l4)      # Radio-Buttons

    layout.insertLayout(0, l5)  # die beiden Bereiche Links Liste, Rechts Radio-Buttons
    layout.insertLayout(1, l2)  # die untere Lesite mit den Buttons

    def onAccepted():
        """Close dialog on button close."""
        dialog.done(1)

    def onFinished():
        """Delete dialog on close."""
        dialog.deleteLater()

    def onItemChanged(item=None):
        """Save workbench list state."""
        if item:
            selector.blockSignals(True)
            if item.data(50) == "Unchecked":
                item.setCheckState(QtCore.Qt.CheckState(2))
                item.setData(50, "Checked")
            else:
                item.setCheckState(QtCore.Qt.CheckState(0))
                item.setData(50, "Unchecked")
            selector.blockSignals(False)
        enabled = []
        unchecked = []
        for index in range(selector.count()):
            if selector.item(index).checkState() == QtCore.Qt.Checked:
                enabled.append(selector.item(index).data(32))
            else:
                unchecked.append(selector.item(index).data(32))
        __parameters__.SetString("Enabled", ",".join(enabled))
        __parameters__.SetString("Unchecked", ",".join(unchecked))
        onWorkbenchActivated()

    def onUp():
        """Save workbench position list."""
        currentIndex = selector.currentRow()
        if currentIndex != 0:
            selector.blockSignals(True)
            currentItem = selector.takeItem(currentIndex)
            selector.insertItem(currentIndex - 1, currentItem)
            selector.setCurrentRow(currentIndex - 1)
            selector.blockSignals(False)
            #position = []
            #for index in range(selector.count()):
            #    position.append(selector.item(index).data(32))
            #__parameters__.SetString("Position", ",".join(position))
            onItemChanged()

    def onDown():
        """Save workbench position list."""
        currentIndex = selector.currentRow()
        if currentIndex != selector.count() - 1 and currentIndex != -1:
            selector.blockSignals(True)
            currentItem = selector.takeItem(currentIndex)
            selector.insertItem(currentIndex + 1, currentItem)
            selector.setCurrentRow(currentIndex + 1)
            selector.blockSignals(False)
            #position = []
            #for index in range(selector.count()):
            #    position.append(selector.item(index).data(32))
            #__parameters__.SetString("Position", ",".join(position))
            onItemChanged()

    def onOpenFile():
        """Open the configuration file"""
        open_file_in_editor()


    def onG0(r):
        """Set TabBar style."""
        if r:
            for i in g0.findChildren(QtGui.QRadioButton):
                if i.isChecked():
                    __parameters__.SetString("Style", i.objectName())
            onWorkbenchActivated()

    def onG1(r):
        """Set TabBar orientation."""
        if r:
            for i in g1.findChildren(QtGui.QRadioButton):
                if i.isChecked():
                    __parameters__.SetString("Orientation", i.objectName())
            onWorkbenchActivated()

    def onG6(r):
        """Set pref button."""
        if r:
            for i in g6.findChildren(QtGui.QRadioButton):
                if i.isChecked():
                    __parameters__.SetString("PrefButton", i.objectName())
            onWorkbenchActivated()

    default = defaults()
    enabled = __parameters__.GetString("Enabled", default)
    enabled = enabled.split(",")
    unchecked = __parameters__.GetString("Unchecked")
    unchecked = unchecked.split(",")
    position = __parameters__.GetString("Position")
    position = position.split(",")
    default = default.split(",")
    for i in default:                       # find new WB and append them to 'position'
        if i not in position:
            position.append(i)

    # build up the list of WB and set the CheckState        
    for i in position:
        if i in __actions__:
            item = QtGui.QListWidgetItem(selector)
            item.setText(__actions__[i].text())
            item.setIcon(__actions__[i].icon())
            item.setData(32, __actions__[i].data())
            if __actions__[i].data() in enabled:
                item.setCheckState(QtCore.Qt.CheckState(2))
                item.setData(50, "Checked")
            elif __actions__[i].data() in unchecked:
                item.setCheckState(QtCore.Qt.CheckState(0))
                item.setData(50, "Unchecked")
            else:
                item.setCheckState(QtCore.Qt.CheckState(2))
                item.setData(50, "Checked")

    # set the radio buttons to the stored values
    style = __parameters__.GetString("Style")
    if style == "Text":
        r1.setChecked(True)
    elif style == "IconText":
        r2.setChecked(True)
    else:
        r0.setChecked(True)
    orientation = __parameters__.GetString("Orientation")
    if orientation == "North":
        r4.setChecked(True)
    elif orientation == "South":
        r5.setChecked(True)
    elif orientation == "West":
        r6.setChecked(True)
    elif orientation == "East":
        r7.setChecked(True)
    else:
        r3.setChecked(True)
    prefbutton = __parameters__.GetString("PrefButton", "On")
    if prefbutton == "On":
        r8.setChecked(True)
    else:
        r9.setChecked(True)
    r0.toggled.connect(onG0)
    r1.toggled.connect(onG0)
    r2.toggled.connect(onG0)
    r3.toggled.connect(onG1)
    r4.toggled.connect(onG1)
    r5.toggled.connect(onG1)
    r6.toggled.connect(onG1)
    r7.toggled.connect(onG1)
    r8.toggled.connect(onG6)
    r9.toggled.connect(onG6)
    btnUp.clicked.connect(onUp)
    btnDown.clicked.connect(onDown)
    selector.itemChanged.connect(onItemChanged)
    dialog.finished.connect(onFinished)
    btnClose.clicked.connect(onAccepted)
    btnFile.clicked.connect(onOpenFile)

    return dialog


def onPreferences():
    """Open the preferences dialog."""
    dialog = prefDialog()
    dialog.show()


def accessoriesMenu():
    """Add TabBar preferences to accessories menu."""
    pref = QtGui.QAction(__mainWindow__)
    pref.setText("TabBar")
    pref.setObjectName("TabBar")
    pref.triggered.connect(onPreferences)
    try:
        import AccessoriesMenu
        AccessoriesMenu.addItem("TabBar")
    except ImportError:
        a = __mainWindow__.findChild(QtGui.QAction, "AccessoriesMenu")
        if a:
            a.menu().addAction(pref)
        else:
            mb = __mainWindow__.menuBar()
            actionAccessories = QtGui.QAction(__mainWindow__)
            actionAccessories.setObjectName("AccessoriesMenu")
            actionAccessories.setIconText("Accessories")
            menu = QtGui.QMenu()
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
        tb = __mainWindow__.findChild(QtGui.QToolBar, "Tabs")
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