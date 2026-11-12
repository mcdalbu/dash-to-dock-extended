#!/usr/bin/python3
"""Exercise the palettes in the existing private Shell harness."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dock_harness', ROOT / 'tests/shell-menu-headless.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
harness.__file__ = __file__
os.environ['SOFT_TEST_LABEL'] = 'palettes-v33'


def test_palettes(evaluate, check, screenshot, results):
    evaluate('''globalThis.paletteModule = null;
        import(extension.dir.get_child('ptyxisPalettes.js').get_uri()).then(m=>paletteModule=m);''')
    time.sleep(.3)
    check('catalog-244', 'paletteModule.PTYXIS_PALETTES.length === 244')
    evaluate('manager.settings.set_boolean("shell-menu-colors",true);'
             'manager.settings.set_enum("transparency-mode",1);'
             'manager.settings.set_double("background-opacity",.35);')
    check('all-palettes-apply-with-opacity', '''(() => {
        for (const p of paletteModule.PTYXIS_PALETTES) {
            manager.settings.set_string('dock-palette',p.id);
            dock._themeManager.updateCustomTheme();
            const dark = imports.gi.St.Settings.get().color_scheme !== imports.gi.St.SystemColorScheme.PREFER_LIGHT;
            const hex = p[dark?'dark':'light'].Background;
            const [,c] = (imports.gi.Clutter.Color ?? imports.gi.Cogl.Color).from_string(hex);
            if (!background.get_style().includes(`rgba(${c.red}, ${c.green}, ${c.blue}, 0.35)`))
                throw new Error(p.id+': '+background.get_style());
        } return true;
    })()''')
    evaluate('manager.settings.set_string("dock-palette","gnome");'
             'globalThis.iface = new Gio.Settings({schema_id:"org.gnome.desktop.interface"});'
             'iface.set_string("color-scheme","prefer-light");')
    time.sleep(.6)
    check('light-palette', 'background.get_style().includes("rgba(255, 255, 255, 0.35)")')
    evaluate('iface.set_string("color-scheme","prefer-dark");')
    time.sleep(.6)
    check('dark-palette', 'background.get_style().includes("rgba(28, 28, 31, 0.35)")')
    evaluate('manager.settings.set_string("dock-palette","missing-palette");')
    time.sleep(.3)
    check('invalid-falls-back-to-shell', 'background.get_style().includes("background-color:")')
    evaluate('manager.settings.set_string("dock-palette","gnome");'
             'manager.settings.set_boolean("shell-menu-colors",false);')
    time.sleep(.3)
    check('disable-restores-hover', '!dock._themeManager._hoverFile')
    evaluate('manager.settings.set_boolean("shell-menu-colors",true);')
    time.sleep(.3)
    evaluate('backdrop.hide(); dock._animateIn(0,0);')
    time.sleep(.3)
    screenshot(ROOT / 'validation/palettes-v33-dock.png')
    # Use the private compositor for the real GTK preferences, with settings in memory.
    env = dict(os.environ, GSETTINGS_BACKEND='memory', GDK_BACKEND='wayland', GTK_A11Y='none',
               GI_TYPELIB_PATH='/usr/lib64/gnome-shell/girepository-1.0:/usr/lib64/gnome-shell')
    wayland = evaluate('imports.gi.GLib.getenv("WAYLAND_DISPLAY")')
    if wayland:
        env['WAYLAND_DISPLAY'] = wayland
    proc = subprocess.Popen(['gjs', '-m', str(ROOT / 'tests/palettes-prefs.mjs'), str(ROOT)],
                            env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    screenshot(ROOT / 'validation/palettes-v33-preferences.png')
    stdout, stderr = proc.communicate(timeout=20)
    results['preferences-output'] = stdout + stderr
    if proc.returncode:
        raise RuntimeError(results['preferences-output'])
    results['preferences'] = True


fake = types.ModuleType('standalone_dock')
fake.test_standalone_dock = test_palettes
sys.modules['standalone_dock'] = fake
if __name__ == '__main__':
    if os.environ.get('SOFT_TEST_CHILD'):
        harness.test()
    else:
        sys.exit(harness.stage())
