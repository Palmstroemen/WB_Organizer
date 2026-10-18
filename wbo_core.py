# WBO Workbench-Organizer widget for FreeCAD
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

"""Logic of the Workbench Organizer that does not depend on FreeCAD or Qt.

Keep this module free of FreeCAD and Qt imports so it can be tested with pytest.
"""

import json
import os

STR_ALL      = "WBO All"
STR_DROP     = "WBO In Groups Dropdown"
STR_NEW      = "WBO New"
STR_LOST     = "WBO Lost"
STR_DISABLED = "WBO Disabled"

INTERNAL_GROUPS = (STR_DROP, STR_NEW, STR_LOST, STR_DISABLED)
SEPARATOR       = "---"


def terminated(entries):
    """Return entries without empty strings, plus one "" at the end.

    The trailing "" lets users end every real line of the config file with a comma.
    """
    return [e for e in entries if e != ""] + [""]


def default_groups(installed):
    """Groups for a freshly generated config file."""
    return {
        STR_DROP:     [""],
        STR_ALL:      terminated(installed),
        STR_NEW:      terminated(installed),
        STR_LOST:     [""],
        STR_DISABLED: [""],
    }


def alias_template(installed):
    """Content for a freshly generated renaming file."""
    aliases = {key: "" for key in installed}
    aliases["ArchWorkbench"] = "Architecture"
    aliases[""] = ""
    return aliases


def sync_groups(groups, installed):
    """Compare the groups with the installed workbenches.

    Returns a new dict where new workbenches are appended to the 'All' group and
    listed in 'New', and workbenches that are no longer installed are listed in
    'Lost' (they stay in 'All' to keep their position).
    """
    synced = {name: list(entries) for name, entries in groups.items()}
    known  = [wb for wb in synced.get(STR_ALL, []) if wb != ""]
    new    = [wb for wb in installed if wb not in known]
    lost   = [wb for wb in known if wb not in installed]

    synced[STR_ALL]  = terminated(known + new)
    synced[STR_NEW]  = terminated(new) if new else []
    synced[STR_LOST] = terminated(lost)
    return synced


def load_json(path):
    """Read a config file. Returns (data, None) or (None, error message)."""
    if not os.path.exists(path):
        return None, "Error: file not found: {}".format(path)
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, "Error decoding JSON: {}".format(e)
    except Exception as e:
        return None, "Error: {}".format(e)
    if not isinstance(data, dict):
        return None, "Error: the file must contain a {...} object."
    return data, None


def save_json(path, data):
    """Write a config file with indentation, so users can edit it by hand."""
    with open(path, "w") as f:
        f.write(json.dumps(data, indent=4))


def display_name(wb, default, aliases):
    """Name of a workbench: its alias if one is set, otherwise the default."""
    return (aliases or {}).get(wb) or default


def group_label(group, aliases):
    """Name of a group in the groups dropdown. Only 'All' can be renamed."""
    if group == STR_ALL:
        return (aliases or {}).get(STR_ALL) or STR_ALL
    return group


def selectable_groups(groups):
    """Groups to show in the groups dropdown, in file order."""
    return [g for g in groups if g not in INTERNAL_GROUPS]


def resolve_group(groups, name):
    """Return name if it is a selectable group, otherwise the 'All' group."""
    if name in groups and name not in INTERNAL_GROUPS:
        return name
    return STR_ALL


def separator_label(entry):
    """Label of a separator entry ("---Label"), or None if entry is no separator."""
    if entry.startswith(SEPARATOR):
        return entry[len(SEPARATOR):]
    return None


def dropdown_entries(groups, group, available):
    """Entries of the workbench dropdown as ("workbench", name) / ("separator", label).

    Disabled workbenches are hidden.
    """
    disabled = groups.get(STR_DISABLED) or []
    entries = []
    for entry in groups.get(group) or []:
        label = separator_label(entry)
        if label is not None:
            entries.append(("separator", label))
        elif entry in available and entry not in disabled:
            entries.append(("workbench", entry))
    return entries


def tab_workbenches(groups, group, active, available):
    """Workbenches to show as tabs.

    The active workbench is appended if it is not part of the group, so the
    user always sees which workbench is active. Disabled workbenches are hidden.
    """
    wbs = list(groups.get(group) or [])
    if active not in wbs:
        wbs.append(active)
    disabled = groups.get(STR_DISABLED) or []
    return [wb for wb in wbs if wb in available and wb not in disabled]
