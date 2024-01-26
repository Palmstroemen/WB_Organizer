# WorkbenchOrganizer
A workbench organizer widget for FreeCAD.

The aim of the workbench organizer (WBO) is to organize the long list of workbenches into meaningful groups.

<video width="486" height="308" controls>
  <source src="./Resources/videos/WBO_dropdown.mp4" type="video/mp4">
  Here you could see a video if only your browser would support this.
</video>
The WBO provides __workbench groups__ with an __additional selector__ to first select a group of workbenches which then allows you to select a workbench from a (reduced) group of workbenches to make it easier to find your workbenches.

It also allows to present the workbenches in tabs or in a dropdown list.

<video width="1034" height="296" controls>
  <source src="./Resources/videos/WBO_tabs.mp4" type="video/mp4">
  Here you could see a video if only your browser would support this.
</video>

It allows to put __one workbench in multiple groups__. So i.e. the Spreadsheet-Workbench might appear in multiple groups.

It even allows to put workbenches __into the group-selector dropdown__. This might be useful for workbenches like Spreadsheet that you might want to put in many groups.

It further allows to __rename workbenches__ whether to translate or to give it a more meaningful name. In the videos above you can see, that we have renamed several workbenches in the German language. Like 'Spreadsheet' --> 'Tabellen'

Of course, you also find an 'All'-workbenches group to access workbenches the traditional way.


A __WorkbenchOrganizer preferences__ dialog can be accessed from within the groups dropdown or under __menu -> Accessories -> WorkbenchOrganizer__.
![Image],(./resources/images/WBP_preferences.png)

To be honest, the preferences dialog at the moment is quite rudimentary.
For an introduction to how to create and modify your workbenches, see [instructions.txt](./Resources/Instructions.txt)

_In case our WorkbenchOrganizer finds some fans, we'll continue to improve it. For the moment, this is our MVP (minimal valuable product)._
