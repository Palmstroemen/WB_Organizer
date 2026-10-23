"""Tests for the FreeCAD-independent logic of the Workbench Organizer."""

import json

import pytest

import wbo_core as core
from wbo_core import STR_ALL, STR_DROP, STR_NEW, STR_LOST, STR_DISABLED


# --- terminated lists ("" at the end so every real line ends with a comma) ---

@pytest.mark.parametrize("given, expected", [
    ([], [""]),
    (["a", "b"], ["a", "b", ""]),
    (["a", "b", ""], ["a", "b", ""]),
    (["a", "", "b"], ["a", "b", ""]),
    (["a", "", "b", ""], ["a", "b", ""]),
])
def test_terminated(given, expected):
    assert core.terminated(given) == expected


# --- default groups / templates ----------------------------------------------

def test_default_groups_contains_all_special_groups():
    groups = core.default_groups(["PartWorkbench", "SketcherWorkbench"])
    assert list(groups) == [STR_DROP, STR_ALL, STR_NEW, STR_LOST, STR_DISABLED]
    assert groups[STR_ALL] == ["PartWorkbench", "SketcherWorkbench", ""]
    assert groups[STR_NEW] == ["PartWorkbench", "SketcherWorkbench", ""]
    assert groups[STR_DROP] == [""]
    assert groups[STR_LOST] == [""]
    assert groups[STR_DISABLED] == [""]


def test_default_groups_lists_are_independent():
    groups = core.default_groups(["PartWorkbench"])
    groups[STR_NEW].append("X")
    assert "X" not in groups[STR_ALL]


def test_alias_template():
    aliases = core.alias_template(["ArchWorkbench", "PartWorkbench"])
    assert aliases == {"ArchWorkbench": "Architecture", "PartWorkbench": "", "": ""}


# --- syncing the groups with the installed workbenches -----------------------

def test_sync_detects_new_workbenches_and_appends_them_to_all():
    groups = {STR_ALL: ["A", "B", ""], STR_NEW: ["old"], STR_LOST: [""]}
    synced = core.sync_groups(groups, ["A", "B", "C"])
    assert synced[STR_ALL] == ["A", "B", "C", ""]
    assert synced[STR_NEW] == ["C", ""]


def test_sync_detects_lost_workbenches_but_keeps_them_in_all():
    groups = {STR_ALL: ["A", "B", "C", ""], STR_NEW: [], STR_LOST: [""]}
    synced = core.sync_groups(groups, ["A", "C"])
    assert synced[STR_ALL] == ["A", "B", "C", ""]
    assert synced[STR_LOST] == ["B", ""]


def test_sync_clears_new_and_lost_when_nothing_changed():
    groups = {STR_ALL: ["A", "B", ""], STR_NEW: ["X", ""], STR_LOST: ["Y", ""]}
    synced = core.sync_groups(groups, ["A", "B"])
    assert synced[STR_NEW] == []
    assert synced[STR_LOST] == [""]


def test_sync_keeps_user_groups_untouched():
    groups = {"Mine": ["B", "---", "A", ""], STR_ALL: ["A", "B", ""]}
    synced = core.sync_groups(groups, ["A", "B"])
    assert synced["Mine"] == ["B", "---", "A", ""]
    assert list(synced)[0] == "Mine"


def test_sync_creates_missing_all_group():
    synced = core.sync_groups({"Mine": ["A"]}, ["A", "B"])
    assert synced[STR_ALL] == ["A", "B", ""]


def test_sync_does_not_mutate_input():
    groups = {STR_ALL: ["A", ""]}
    core.sync_groups(groups, ["A", "B"])
    assert groups == {STR_ALL: ["A", ""]}


# --- reading the config files --------------------------------------------------

def test_load_json_ok(tmp_path):
    path = tmp_path / "groups.txt"
    path.write_text(json.dumps({STR_ALL: ["A"]}))
    data, error = core.load_json(str(path))
    assert data == {STR_ALL: ["A"]}
    assert error is None


def test_load_json_reports_syntax_error(tmp_path):
    path = tmp_path / "groups.txt"
    path.write_text('{"Mine": ["A",]}')      # the typical trailing-comma mistake
    data, error = core.load_json(str(path))
    assert data is None
    assert error.startswith("Error decoding JSON:")


def test_load_json_reports_missing_file(tmp_path):
    data, error = core.load_json(str(tmp_path / "missing.txt"))
    assert data is None
    assert "not found" in error


def test_load_json_rejects_non_object(tmp_path):
    path = tmp_path / "groups.txt"
    path.write_text('["A", "B"]')
    data, error = core.load_json(str(path))
    assert data is None
    assert error


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "groups.txt")
    groups = core.default_groups(["A"])
    core.save_json(path, groups)
    data, error = core.load_json(path)
    assert error is None
    assert data == groups


# --- names --------------------------------------------------------------------

def test_display_name_uses_alias():
    assert core.display_name("ArchWorkbench", "Arch", {"ArchWorkbench": "Architektur"}) == "Architektur"


def test_display_name_falls_back_on_empty_or_missing_alias():
    assert core.display_name("ArchWorkbench", "Arch", {"ArchWorkbench": ""}) == "Arch"
    assert core.display_name("ArchWorkbench", "Arch", {}) == "Arch"
    assert core.display_name("ArchWorkbench", "Arch", None) == "Arch"


def test_group_label_uses_alias_for_all_group():
    assert core.group_label(STR_ALL, {STR_ALL: "Alle"}) == "Alle"


def test_group_label_without_alias_for_all_group():
    assert core.group_label(STR_ALL, {}) == STR_ALL
    assert core.group_label(STR_ALL, {STR_ALL: ""}) == STR_ALL


def test_group_label_for_user_group():
    assert core.group_label("Mine", {"Mine": "ignored"}) == "Mine"


# --- groups shown in the dropdown --------------------------------------------

def test_selectable_groups_hides_internal_groups_and_keeps_order():
    groups = {STR_DROP: [], "B": [], STR_NEW: [], "A": [], STR_ALL: [],
              STR_LOST: [], STR_DISABLED: []}
    assert core.selectable_groups(groups) == ["B", "A", STR_ALL]


def test_resolve_group_keeps_existing_group():
    assert core.resolve_group({"Mine": [], STR_ALL: []}, "Mine") == "Mine"


def test_resolve_group_falls_back_to_all_for_unknown_group():
    assert core.resolve_group({STR_ALL: []}, "Renamed") == STR_ALL
    assert core.resolve_group({STR_ALL: []}, "") == STR_ALL


def test_resolve_group_never_selects_internal_group():
    assert core.resolve_group({STR_LOST: [], STR_ALL: []}, STR_LOST) == STR_ALL


# --- separators ---------------------------------------------------------------

@pytest.mark.parametrize("entry, label", [
    ("---", ""),
    ("---Separator", "Separator"),
    ("----", "-"),
    ("--", None),
    ("PartWorkbench", None),
    ("", None),
])
def test_separator_label(entry, label):
    assert core.separator_label(entry) == label


# --- workbenches of a group --------------------------------------------------

def test_dropdown_entries():
    groups = {"Mine": ["A", "---Assembly", "B", "unknown", ""]}
    assert core.dropdown_entries(groups, "Mine", {"A", "B"}) == [
        ("workbench", "A"), ("separator", "Assembly"), ("workbench", "B")]


def test_dropdown_entries_hides_disabled_workbenches():
    groups = {"Mine": ["A", "---", "B", "C", ""], STR_DISABLED: ["B"]}
    assert core.dropdown_entries(groups, "Mine", {"A", "B", "C"}) == [
        ("workbench", "A"), ("separator", ""), ("workbench", "C")]


def test_dropdown_entries_of_unknown_group_is_empty():
    assert core.dropdown_entries({}, "Gone", {"A"}) == []


def test_tab_workbenches_filters_unknown_and_disabled():
    groups = {"Mine": ["A", "---", "B", "C", ""], STR_DISABLED: ["B"]}
    assert core.tab_workbenches(groups, "Mine", "A", {"A", "B", "C"}) == ["A", "C"]


def test_tab_workbenches_appends_active_workbench_if_missing():
    groups = {"Mine": ["A", ""]}
    assert core.tab_workbenches(groups, "Mine", "C", {"A", "C"}) == ["A", "C"]


def test_tab_workbenches_does_not_mutate_groups():
    groups = {"Mine": ["A", ""]}
    core.tab_workbenches(groups, "Mine", "C", {"A", "C"})
    assert groups["Mine"] == ["A", ""]


def test_tab_workbenches_of_unknown_group_shows_active_only():
    assert core.tab_workbenches({}, "Gone", "A", {"A"}) == ["A"]


# --- editing groups (setup dialog) --------------------------------------------

def _groups():
    return {
        STR_DROP: [""],
        "Parts": ["PartWorkbench", ""],
        STR_ALL: ["PartWorkbench", "SketcherWorkbench", ""],
        "Draw": ["TechDrawWorkbench", ""],
        STR_NEW: [],
        STR_LOST: [""],
        STR_DISABLED: [""],
    }


@pytest.mark.parametrize("name", ["", "  ", STR_ALL, STR_DISABLED, "Parts"])
def test_check_group_name_rejects(name):
    assert core.check_group_name(_groups(), name)


def test_check_group_name_accepts_new_name():
    assert core.check_group_name(_groups(), "Print") is None


def test_add_group_after_last_selectable_group():
    groups = core.add_group(_groups(), "Print")
    assert list(groups) == [STR_DROP, "Parts", STR_ALL, "Draw", "Print", STR_NEW, STR_LOST, STR_DISABLED]
    assert groups["Print"] == [""]


def test_add_group_rejects_existing_name():
    with pytest.raises(ValueError):
        core.add_group(_groups(), "Parts")


def test_add_group_does_not_change_the_input():
    groups = _groups()
    core.add_group(groups, "Print")
    assert "Print" not in groups


def test_rename_group_keeps_position_and_members():
    groups = core.rename_group(_groups(), "Parts", "Construct")
    assert list(groups)[1] == "Construct"
    assert groups["Construct"] == ["PartWorkbench", ""]
    assert "Parts" not in groups


def test_rename_group_to_same_name_is_allowed():
    assert core.rename_group(_groups(), "Parts", "Parts") == _groups()


@pytest.mark.parametrize("old, new", [(STR_ALL, "Everything"), (STR_DISABLED, "X"), ("Parts", "Draw")])
def test_rename_group_rejects(old, new):
    with pytest.raises(ValueError):
        core.rename_group(_groups(), old, new)


def test_delete_group():
    groups = core.delete_group(_groups(), "Draw")
    assert "Draw" not in groups
    assert core.selectable_groups(groups) == ["Parts", STR_ALL]


@pytest.mark.parametrize("name", [STR_ALL, STR_NEW])
def test_delete_group_rejects_protected_groups(name):
    with pytest.raises(ValueError):
        core.delete_group(_groups(), name)


def test_reorder_groups_keeps_internal_groups_in_place():
    groups = core.reorder_groups(_groups(), ["Draw", "Parts", STR_ALL])
    assert list(groups) == [STR_DROP, "Draw", "Parts", STR_ALL, STR_NEW, STR_LOST, STR_DISABLED]
    assert groups["Draw"] == ["TechDrawWorkbench", ""]


def test_reorder_groups_rejects_incomplete_order():
    with pytest.raises(ValueError):
        core.reorder_groups(_groups(), ["Draw", "Parts"])


def test_set_members_drops_duplicates_but_keeps_separators():
    groups = core.set_members(_groups(), "Parts",
                              ["PartWorkbench", "---", "SketcherWorkbench", "---", "PartWorkbench", ""])
    assert groups["Parts"] == ["PartWorkbench", "---", "SketcherWorkbench", "---", ""]


def test_set_members_empty_group():
    assert core.set_members(_groups(), "Parts", [])["Parts"] == [""]


# --- aliases ----------------------------------------------------------------

def test_set_alias_and_has_alias():
    aliases = core.set_alias({"": ""}, "ArchWorkbench", " Architecture ")
    assert aliases["ArchWorkbench"] == "Architecture"
    assert core.has_alias("ArchWorkbench", aliases)
    assert not core.has_alias("PartWorkbench", aliases)


def test_set_alias_empty_name_removes_alias():
    aliases = core.set_alias({"ArchWorkbench": "Architecture"}, "ArchWorkbench", "")
    assert "ArchWorkbench" not in aliases
    assert not core.has_alias("ArchWorkbench", aliases)


def test_empty_alias_entry_from_template_is_no_alias():
    assert not core.has_alias("DraftWorkbench", {"DraftWorkbench": ""})


# --- drag & drop in the lists of the setup dialog ------------------------------

@pytest.mark.parametrize("rows, row, expected, first", [
    ([0], 2, ["b", "a", "c", "d"], 1),          # down: drop between b and c
    ([3], 0, ["d", "a", "b", "c"], 0),          # up to the top
    ([0, 2], 4, ["b", "d", "a", "c"], 2),       # two entries to the end
    ([1], 1, ["a", "b", "c", "d"], 1),          # dropped onto its own place
])
def test_move_entries(rows, row, expected, first):
    entries, start, count = core.move_entries(["a", "b", "c", "d"], rows, row)
    assert entries == expected
    assert (start, count) == (first, len(rows))


def test_insert_entries_skips_present_workbenches_but_not_separators():
    entries, first, count = core.insert_entries(["A", "---", "B"], ["B", "C", "---", "C"], 1)
    assert entries == ["A", "C", "---", "---", "B"]
    assert (first, count) == (1, 2)
