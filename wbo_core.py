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


# --- editing groups and aliases (used by the setup dialog) -------------------

def check_group_name(groups, name):
    """Return an error message if name can't be used for a new group, otherwise None."""
    if not name.strip():
        return "The group name must not be empty."
    if name in INTERNAL_GROUPS or name == STR_ALL:
        return "'{}' is reserved for the Workbench Organizer.".format(name)
    if name in groups:
        return "A group '{}' already exists.".format(name)
    return None


def add_group(groups, name):
    """Return groups with a new, empty group after the last selectable group."""
    error = check_group_name(groups, name)
    if error:
        raise ValueError(error)
    selectable = selectable_groups(groups)
    result = {}
    for key, entries in groups.items():
        result[key] = list(entries)
        if selectable and key == selectable[-1]:
            result[name] = [""]
    if name not in result:
        result[name] = [""]
    return result


def rename_group(groups, old, new):
    """Return groups with group old renamed to new, keeping its position.

    'All' and the internal groups can't be renamed here; 'All' gets an alias instead.
    """
    if old in INTERNAL_GROUPS or old == STR_ALL:
        raise ValueError("'{}' can't be renamed.".format(old))
    if new == old:
        return {key: list(entries) for key, entries in groups.items()}
    error = check_group_name(groups, new)
    if error:
        raise ValueError(error)
    return {(new if key == old else key): list(entries) for key, entries in groups.items()}


def delete_group(groups, name):
    """Return groups without group name. 'All' and the internal groups can't be deleted."""
    if name in INTERNAL_GROUPS or name == STR_ALL:
        raise ValueError("'{}' can't be deleted.".format(name))
    return {key: list(entries) for key, entries in groups.items() if key != name}


def reorder_groups(groups, order):
    """Return groups with the selectable groups in the given order.

    The internal groups keep their places in the file; the selectable groups
    fill the remaining places in the new order.
    """
    selectable = selectable_groups(groups)
    if sorted(order) != sorted(selectable):
        raise ValueError("The new order must contain every selectable group once.")
    remaining = iter(order)
    result = {}
    for key in groups:
        name = next(remaining) if key in selectable else key
        result[name] = list(groups[name])
    return result


def set_members(groups, group, members):
    """Return groups with the workbenches of group replaced by members.

    Duplicate workbenches are dropped (the first one stays); separators may repeat.
    """
    seen = set()
    cleaned = []
    for entry in members:
        if entry == "":
            continue
        if separator_label(entry) is None:
            if entry in seen:
                continue
            seen.add(entry)
        cleaned.append(entry)
    result = {key: list(entries) for key, entries in groups.items()}
    result[group] = terminated(cleaned)
    return result


def move_entries(entries, rows, row):
    """Move the entries at rows to position row, as a drop indicator shows it.

    row counts positions in the original list. Returns (entries, first, count):
    the moved entries are now at entries[first:first + count].
    """
    rows   = sorted(set(rows))
    picked = [entries[r] for r in rows]
    rest   = [e for r, e in enumerate(entries) if r not in rows]
    first  = row - len([r for r in rows if r < row])
    return rest[:first] + picked + rest[first:], first, len(picked)


def insert_entries(entries, new, row):
    """Insert new at position row, skipping workbenches that are already there.

    Separators may repeat. Returns (entries, first, count) like move_entries.
    """
    added = []
    for entry in new:
        if separator_label(entry) is None and (entry in entries or entry in added):
            continue
        added.append(entry)
    return entries[:row] + added + entries[row:], row, len(added)

def has_alias(wb, aliases):
    """True if the workbench (or the 'All' group) has an alias."""
    return bool((aliases or {}).get(wb))


def set_alias(aliases, wb, name):
    """Return aliases with the alias of wb set to name. An empty name removes the alias."""
    result = dict(aliases or {})
    name = name.strip()
    if name:
        result[wb] = name
    else:
        result.pop(wb, None)
    return result
