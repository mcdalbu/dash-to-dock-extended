"""Standalone stable dock behavior and preferences without GNOME Extended."""
import os
from pathlib import Path
import subprocess
import time


def test_standalone_dock(evaluate, check, screenshot, results):
    check('removed-effect-schemas', 'manager.settings.settings_schema.list_keys().every(k => !/^(dock-blur|icon-shadow|dock-outline)/.test(k))')
    evaluate('manager.settings.set_boolean("shell-menu-style", true); manager.settings.set_boolean("shell-menu-colors", true);')
    time.sleep(0.3)
    check('shell-menu-profile', 'background.get_style().includes("border-top:") && background.get_style().includes("box-shadow: none")')
    check('outer-shadow-on', '!!background.get_theme_node().get_box_shadow()')
    evaluate('manager.settings.set_boolean("shell-menu-shadow", false);')
    check('outer-shadow-off', '!background.get_theme_node().get_box_shadow()')
    evaluate('manager.settings.set_boolean("shell-menu-shadow", true); manager.settings.set_int("dock-shadow-size", 150);')
    check('outer-shadow-restored', '!!background.get_theme_node().get_box_shadow()')
    check('shell-menu-hover', '!!dock._themeManager._hoverCss?.includes(":hover")')
    check('no-native-blur', '!dock._themeManager._blurEffect && typeof dock._themeManager._updateBlur === "undefined"')
    evaluate('manager.settings.set_boolean("shell-menu-style", false); manager.settings.set_boolean("shell-menu-colors", false);')
    time.sleep(0.3)
    check('disable-profile', '!dock.has_style_class_name("shell-menu-style") && !dock._themeManager._hoverCss')
    evaluate('manager.settings.set_boolean("shell-menu-style", true); manager.settings.set_boolean("shell-menu-colors", true);')
    time.sleep(0.3)
    check('reenable-profile', 'dock.has_style_class_name("shell-menu-style") && !!dock._themeManager._hoverCss')
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, WAYLAND_DISPLAY='wayland-0', GDK_BACKEND='wayland', GSETTINGS_BACKEND='memory',
               GI_TYPELIB_PATH='/usr/lib64/gnome-shell/girepository-1.0:/usr/lib64/gnome-shell')
    prefs = subprocess.run(['gjs', '-m', str(root / 'tests/central-prefs.mjs'), str(root)],
                           env=env, capture_output=True, text=True, timeout=15)
    results['standalone-preferences'] = dict(passed=prefs.returncode == 0, output=prefs.stdout.strip())
    if prefs.returncode:
        raise RuntimeError(prefs.stderr)
