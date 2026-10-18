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
