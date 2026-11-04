"""Standalone stable dock behavior and preferences without GNOME Extended."""
import os
from pathlib import Path
import subprocess
import time


def test_highlight_colors(evaluate, check):
    evaluate('''(() => {
        const St = imports.gi.St;
        globalThis.highlightProbe = new St.BoxLayout({style_class: 'dash-item-container'});
        globalThis.highlightButtons = ['app-well-app', 'overview-tile', 'show-apps'].map(style_class => {
            const button = new St.Button({style_class});
            button.set_child(new St.Bin({style_class: 'overview-icon'}));
            highlightProbe.add_child(button);
            return button;
        });
        dock.dash._box.add_child(highlightProbe);
        globalThis.interfaceSettings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        globalThis.highlightMatches = (button, color, opacity) => {
            const actual = button.child.get_theme_node().get_background_color();
            return ['red', 'green', 'blue'].every(k => actual[k] === color[k]) &&
                Math.abs(actual.alpha - color.alpha * opacity) <= 1;
        };
    })()''')
    try:
        for theme in ['prefer-dark', 'prefer-light']:
            evaluate(f'interfaceSettings.set_string("color-scheme", "{theme}");')
            time.sleep(0.4)
            for opacity in [0, 0.35, 1]:
                evaluate(f'manager.settings.set_double("background-opacity", {opacity}); '
                         'highlightButtons.forEach(b => b.add_style_class_name("focused"));')
                time.sleep(0.1)
                check(f'{theme}-focus-opacity-{opacity}', f'''(() => {{
                    const color = dock._themeManager._colorHover.actor.get_theme_node().get_background_color();
                    return color.alpha > 0 && highlightButtons.slice(0, 2).every(b => highlightMatches(b, color, {opacity}));
                }})()''')
                evaluate('highlightButtons.forEach(b => b.add_style_pseudo_class("hover"));')
                check(f'{theme}-hover-focused-{opacity}', '''(() => {
                    const color = dock._themeManager._colorHover.actor.get_theme_node().get_background_color();
                    return highlightButtons.every(b => highlightMatches(b, color, 1));
                })()''')
                evaluate('highlightButtons.forEach(b => b.remove_style_class_name("focused"));')
                check(f'{theme}-hover-idle-{opacity}', '''(() => {
                    const color = dock._themeManager._colorHover.actor.get_theme_node().get_background_color();
                    return highlightButtons.every(b => highlightMatches(b, color, 1));
                })()''')
                evaluate('highlightButtons.forEach(b => b.remove_style_pseudo_class("hover"));')
            evaluate('manager.settings.set_boolean("shell-menu-colors", false); '
                     'manager.settings.set_double("background-opacity", 0.35); '
                     'highlightButtons.forEach(b => b.add_style_class_name("focused"));')
            check(f'{theme}-custom-focus-opacity', '''highlightButtons.slice(0, 2).every(b =>
                highlightMatches(b, {red:238, green:238, blue:238, alpha:51}, 0.35))''')
            evaluate('manager.settings.set_boolean("shell-menu-colors", true); '
                     'highlightButtons.forEach(b => b.remove_style_class_name("focused"));')
    finally:
        evaluate('highlightProbe.destroy(); interfaceSettings.reset("color-scheme"); '
                 'manager.settings.reset("background-opacity");')


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
    test_highlight_colors(evaluate, check)
    check('no-native-blur', '!dock._themeManager._blurEffect && typeof dock._themeManager._updateBlur === "undefined"')
    evaluate('manager.settings.set_boolean("shell-menu-style", false); manager.settings.set_boolean("shell-menu-colors", false);')
    time.sleep(0.3)
    check('disable-profile', '!dock.has_style_class_name("shell-menu-style") && !dock._themeManager._hoverCss?.includes(":hover")')
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
