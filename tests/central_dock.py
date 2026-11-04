"""GNOME Extended owns the real dock; its renderer must never double-blur."""
import time
import os
import subprocess
from pathlib import Path


def test_central_dock(evaluate, check, screenshot, results):
    evaluate('globalThis.central = Main.extensionManager.lookup("gnome-extended@local").stateObj; '
             'manager.settings.set_boolean("autohide", false); '
             'manager.settings.set_boolean("intellihide", false); '
             'manager.settings.set_boolean("dock-fixed", true); '
             'central._settings.set_boolean("docks", true);')
    time.sleep(0.7)
    evaluate('dock = manager.allDocks[0]; background = dock.dash._background; '
             'globalThis.record = central._docks._records.get(dock); true;')
    check('central-discovers-real-dock', '!!record?.surface?._blur.mapped')
    check('no-duplicate-blur', '!dock._themeManager._blurEffect')
    check('removed-effect-schemas', 'manager.settings.settings_schema.list_keys().every(k => !/^(dock-blur|icon-shadow|dock-outline)/.test(k))')
    check('shell-menu-style-preserved', 'background.get_style().includes("border-top:") && background.get_style().includes("box-shadow: none")')
    check('shell-menu-hover-preserved', '!!dock._themeManager._hoverCss?.includes(":hover")')
    check('central-dock-alpha', 'Math.abs(background.get_theme_node().get_background_color().alpha - 140) <= 1')
    for rate, divisor in enumerate([1, 2, 4]):
        evaluate(f'central._settings.set_int("blur-rate", {rate});')
        time.sleep(0.15)
        check(f'central-dock-rate-{divisor}', f'record.surface._effect.frame_divisor === {divisor}')
    evaluate('central._settings.set_int("blur-radius", 42); central._settings.set_int("brightness", 73); '
             'central._appGrid._settings.set_int("icon-shadow-blur", 9);')
    check('central-shared-blur', 'record.surface._effect.radius === 42 * record.surface._context.scale_factor && '
          'Math.abs(record.surface._effect.brightness - 0.73) < 0.001')
    check('central-shared-shadow-css', 'central._appGrid._css.includes("gnome-extended-dock") && central._appGrid._css.includes("9px rgba")')
    evaluate('globalThis.findDockTestIcon = () => { let icon = null; '
             'const visit = a => { if (a instanceof imports.gi.St.Icon) { icon ??= a; return; } '
             'a.get_children().forEach(visit); }; visit(dock); return icon; }; true;')
    check('central-computed-icon-shadow', 'findDockTestIcon().get_theme_node().get_shadow("icon-shadow").blur === 9 * record.surface._context.scale_factor')
    evaluate('central._appGrid._settings.set_boolean("icon-shadow-dock-enabled", false);')
    check('grid-remains-enabled', 'central._appGrid._settings.get_boolean("icon-shadow-grid-enabled")')
    check('central-shadow-toggle-off', '!findDockTestIcon().get_theme_node().get_shadow("icon-shadow")')
    evaluate('central._appGrid._settings.set_boolean("icon-shadow-dock-enabled", true);')
    check('no-duplicate-icon-shadow', '!dock._themeManager._hoverCss?.includes("icon-shadow:")')
    evaluate('central._settings.set_boolean("docks", false);')
    check('central-toggle-off', '!central._docks._records.get(dock).surface && !dock._themeManager._blurEffect')
    evaluate('central._settings.set_boolean("docks", true);')
    time.sleep(0.2)
    check('central-toggle-on', 'central._docks._records.get(dock).surface._blur.mapped')
    for side in [0, 1, 2, 3]:
        evaluate(f'manager.settings.set_enum("dock-position", {side});')
        time.sleep(0.4)
        evaluate('dock = manager.allDocks[0]; record = central._docks._records.get(dock); true;')
        check(f'central-side-{side}', '''(() => {
            if (!record?.surface?._blur.mapped) return false;
            const a=[...record.box.get_transformed_position(), ...record.box.get_transformed_size()];
            const b=[...record.surface._blur.get_transformed_position(), ...record.surface._blur.get_transformed_size()];
            return a.every((v,i)=>Math.abs(v-b[i])<1);
        })()''')
    screenshot(Path(__file__).resolve().parents[1] / 'validation/central-dock-beta3.png')
    evaluate('central.disable();')
    time.sleep(0.2)
    check('central-cleanup-marker', '!dock.has_style_class_name("gnome-extended-dock")')
    check('dock-has-no-native-blur', '!dock._themeManager._blurEffect')
    evaluate('central.enable();')
    time.sleep(0.3)
    check('central-reenable', '!!central._docks._records.get(dock)?.surface && !dock._themeManager._blurEffect')

    env = dict(os.environ, WAYLAND_DISPLAY='wayland-0', GDK_BACKEND='wayland', GSETTINGS_BACKEND='memory',
               GI_TYPELIB_PATH='/usr/lib64/gnome-shell/girepository-1.0:/usr/lib64/gnome-shell')
    root = Path(__file__).resolve().parents[1]
    prefs = subprocess.run(['gjs', '-m', str(root / 'tests/central-prefs.mjs'), str(root)],
                           env=env, capture_output=True, text=True, timeout=15)
    results['central-preferences'] = dict(passed=prefs.returncode == 0, output=prefs.stdout.strip())
    if prefs.returncode:
        raise RuntimeError(prefs.stderr)
