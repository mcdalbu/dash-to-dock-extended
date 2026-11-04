#!/usr/bin/python3
"""Integration test in a private D-Bus/Wayland session; never changes the desktop.

Run with /usr/bin/python3 tests/shell-menu-headless.py. Requires GNOME Shell 50 or 51, PyGObject
and a usable renderer. The temporary helper enables Eval only on the test bus.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
UUID = 'dash-to-dock-extended@local'


def stage():
    with tempfile.TemporaryDirectory(prefix='shell-soft-dock-test-', ignore_cleanup_errors=True) as temporary:
        base = Path(temporary)
        extension = base / 'data/gnome-shell/extensions' / UUID
        shutil.copytree(ROOT, extension, ignore=shutil.ignore_patterns(
            '*.zip', 'validation', 'tests', '.git', '_build', 'dash-to-dock-extended@local_v*'))
        locale = extension / 'locale/pt_BR/LC_MESSAGES'
        locale.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'po/pt_BR.mo', locale / 'dashtodock.mo')
        if os.environ.get('SOFT_TEST_WITH_SHELL_SOFT'):
            shutil.copytree(ROOT.parent / 'gnome-extended', extension.parent / 'gnome-extended@local',
                            ignore=shutil.ignore_patterns('*.zip', '.git', 'validation', 'tests', '*@local_v*'))
        helper = extension.parent / 'soft-test-helper@local'
        helper.mkdir()
        (helper / 'metadata.json').write_text(json.dumps({
            'uuid': helper.name, 'name': 'Isolated test helper',
            'description': 'Private test session only', 'shell-version': ['50', '51'],
        }))
        (helper / 'extension.js').write_text('''
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
export default class Helper extends Extension {
    enable() { global.context.unsafe_mode = true; }
    disable() { global.context.unsafe_mode = false; }
}
''')
        runtime = base / 'runtime'
        runtime.mkdir(mode=0o700)
        env = dict(os.environ, SOFT_TEST_CHILD='1', XDG_DATA_HOME=str(base / 'data'),
                   XDG_CONFIG_HOME=str(base / 'config'), XDG_CACHE_HOME=str(base / 'cache'),
                   XDG_STATE_HOME=str(base / 'state'), XDG_RUNTIME_DIR=str(runtime))
        env.pop('WAYLAND_DISPLAY', None)
        env.pop('DISPLAY', None)
        try:
            return subprocess.call(['dbus-run-session', '--', '/usr/bin/python3', __file__], env=env)
        finally:
            # GTK can activate the document portal, which creates a FUSE mount
            # in this test's private runtime. Remove only that temporary mount.
            document_mount = runtime / 'doc'
            if os.path.ismount(document_mount):
                unmount = subprocess.run(['fusermount3', '-u', str(document_mount)], capture_output=True)
                # The portal may unmount itself between ismount() and fusermount.
                if unmount.returncode and os.path.ismount(document_mount):
                    unmount.check_returncode()
            time.sleep(0.3)


def test():
    import gi
    gi.require_version('Gio', '2.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gio, GLib, GdkPixbuf

    shell_settings = Gio.Settings.new('org.gnome.shell')
    enabled = ['soft-test-helper@local']
    if os.environ.get('SOFT_TEST_WITH_SHELL_SOFT'):
        enabled.append('gnome-extended@local')
    shell_settings.set_strv('enabled-extensions', enabled + [UUID])
    shell_settings.set_boolean('disable-user-extensions', False)
    shell_settings.set_string('welcome-dialog-last-shown-version', '999')
    Gio.Settings.new('org.gnome.desktop.notifications').set_boolean('show-banners', False)
    Gio.Settings.sync()
    output = ROOT / 'validation'
    output.mkdir(exist_ok=True)
    variant = 'shell-menu-native' if os.environ.get('SOFT_TEST_NATIVE') else 'shell-menu'
    if os.environ.get('SOFT_TEST_LABEL'):
        variant += '-' + os.environ['SOFT_TEST_LABEL']
    if os.environ.get('SOFT_TEST_CONTEXT_COLORS'):
        variant += '-context-colors'
    if os.environ.get('SOFT_TEST_SHADOW_EDGE'):
        variant += '-shadow-edge'
        if os.environ.get('SOFT_TEST_SHADOW_SIZE'):
            variant += '-' + os.environ['SOFT_TEST_SHADOW_SIZE']
    if os.environ.get('SOFT_TEST_WITH_SHELL_SOFT'):
        variant += '-integrated'
    log = (output / f'{variant}-session.log').open('w')
    shell = subprocess.Popen(['gnome-shell', '--headless', '--wayland', '--no-x11',
                              '--virtual-monitor=1440x1000'], stdout=log, stderr=log)
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def evaluate(code):
        result = bus.call_sync('org.gnome.Shell', '/org/gnome/Shell', 'org.gnome.Shell',
                               'Eval', GLib.Variant('(s)', (code,)),
                               GLib.VariantType.new('(bs)'), Gio.DBusCallFlags.NONE, 15000, None)
        ok, value = result.unpack()
        if not ok:
            raise RuntimeError(value or 'Eval is not ready')
        return json.loads(value) if value else None

    results = {}

    def check(name, code):
        value = evaluate(code)
        results[name] = value
        if not value:
            raise AssertionError(name)

    def screenshot(path):
        evaluate('globalThis.captureDone=false; '
                 f'(async()=>{{const stream=Gio.File.new_for_path({json.dumps(str(path))}).replace(null,false, '
                 'Gio.FileCreateFlags.REPLACE_DESTINATION,null);await new Shell.Screenshot().screenshot(false,stream);'
                 'stream.close(null);globalThis.captureDone=true;})()')
        deadline = time.monotonic() + 5
        while not evaluate('captureDone'):
            if time.monotonic() > deadline:
                raise RuntimeError('Shadow screenshot timed out')
            time.sleep(0.03)

    def exterior_difference(on, off, box, margin=24):
        images = [GdkPixbuf.Pixbuf.new_from_file(str(path)) for path in [on, off]]
        a, b = images
        assert a.get_width() == b.get_width() and a.get_height() == b.get_height()
        assert a.get_n_channels() == b.get_n_channels()
        pixels = [image.get_pixels() for image in images]
        left, top, width, height = box
        count, maximum = 0, 0
        for y in range(max(32, int(top)-margin), min(a.get_height(), int(top+height)+margin)):
            for x in range(max(0, int(left)-margin), min(a.get_width(), int(left+width)+margin)):
                if left <= x < left+width and top <= y < top+height:
                    continue
                indices = [y*image.get_rowstride()+x*image.get_n_channels() for image in images]
                difference = max(abs(pixels[0][indices[0]+c]-pixels[1][indices[1]+c]) for c in range(3))
                maximum = max(maximum, difference)
                count += difference >= 3
        return {'pixels': count, 'maximum': maximum}

    try:
        for _ in range(100):
            if shell.poll() is not None:
                raise RuntimeError('Headless Shell exited; see validation/gnome50-session.log')
            try:
                if evaluate('Main.extensionManager.lookup("dash-to-dock-extended@local")?.state === 1'):
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError('Extension did not enable; see validation/gnome50-session.log')

        evaluate('(async()=>{globalThis.extension = Main.extensionManager.lookup("dash-to-dock-extended@local").stateObj; '
                 'globalThis.dockModule = await import(extension.dir.get_child("docking.js").get_uri()); '
                 'globalThis.PM = await import("resource:///org/gnome/shell/ui/popupMenu.js"); globalThis.manager = dockModule.DockManager; Main.overview.hide();})()')
        time.sleep(1)
        evaluate('''(() => {
            const St = imports.gi.St;
            globalThis.backdrop = new St.Widget({width:1440, height:1000, reactive:false});
            const colors = ['#9569b8','#328c9c','#bc9451','#496eb0','#8c597a'];
            for (let x=0;x<1440;x+=80)
                backdrop.add_child(new St.Widget({x,y:32,width:80,height:968,
                    style:`background-color: ${colors[(x/80)%colors.length]};`}));
            Main.uiGroup.insert_child_above(backdrop,global.window_group);
            globalThis.dock = manager.allDocks[0];
            globalThis.background = dock.dash._background;
            globalThis.menu = Main.panel.statusArea.quickSettings.menu;
        })()''')
        if os.environ.get('SOFT_TEST_WITH_SHELL_SOFT'):
            from central_dock import test_central_dock
            test_central_dock(evaluate, check, screenshot, results)
        else:
            from standalone_dock import test_standalone_dock
            test_standalone_dock(evaluate, check, screenshot, results)
        results['passed'] = True
        print(json.dumps(results, indent=2))
    finally:
        (output / f'{variant}-results.json').write_text(json.dumps(results, indent=2) + '\n')
        shell.terminate()
        try:
            shell.wait(timeout=10)
        except subprocess.TimeoutExpired:
            shell.kill()
            shell.wait()
        log.close()


if __name__ == '__main__':
    if os.environ.get('SOFT_TEST_CHILD'):
        test()
    else:
        sys.exit(stage())
