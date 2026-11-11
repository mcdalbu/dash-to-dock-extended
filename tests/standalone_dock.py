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
        globalThis.highlightMatches = (button, color) => {
            const actual = button.child.get_theme_node().get_background_color();
            return ['red', 'green', 'blue'].every(k => actual[k] === color[k]) &&
                Math.abs(actual.alpha - color.alpha) <= 1;
        };
    })()''')
    try:
        for theme in ['prefer-dark', 'prefer-light']:
            evaluate(f'interfaceSettings.set_string("color-scheme", "{theme}");')
            time.sleep(0.4)
            evaluate('manager.settings.set_boolean("shell-menu-colors", false); '
                     'highlightButtons.forEach(b => b.add_style_class_name("focused"));')
            evaluate('globalThis.defaultFocusColors = highlightButtons.slice(0, 2).map(b => { '
                     'const c = b.child.get_theme_node().get_background_color(); '
                     'return {red:c.red, green:c.green, blue:c.blue, alpha:c.alpha}; });')
            evaluate('manager.settings.set_boolean("shell-menu-colors", true);')
            for opacity in [0, 0.35, 1]:
                evaluate(f'manager.settings.set_double("background-opacity", {opacity}); '
                         'highlightButtons.forEach(b => b.add_style_class_name("focused"));')
                time.sleep(0.1)
                check(f'{theme}-default-focus-opacity-{opacity}',
                      'highlightButtons.slice(0, 2).every((b, i) => highlightMatches(b, defaultFocusColors[i]))')
                evaluate('highlightButtons.forEach(b => b.add_style_pseudo_class("hover"));')
                check(f'{theme}-hover-focused-{opacity}', '''(() => {
                    const color = dock._themeManager._colorHover.actor.get_theme_node().get_background_color();
                    return highlightButtons.every(b => highlightMatches(b, color));
                })()''')
                evaluate('highlightButtons.forEach(b => b.remove_style_class_name("focused"));')
                check(f'{theme}-hover-idle-{opacity}', '''(() => {
                    const color = dock._themeManager._colorHover.actor.get_theme_node().get_background_color();
                    return highlightButtons.every(b => highlightMatches(b, color));
                })()''')
                evaluate('highlightButtons.forEach(b => b.remove_style_pseudo_class("hover"));')
            evaluate('manager.settings.set_boolean("shell-menu-colors", false); '
                     'manager.settings.set_double("background-opacity", 0.35); '
                     'highlightButtons.forEach(b => b.add_style_class_name("focused"));')
            check(f'{theme}-custom-default-focus',
                  'highlightButtons.slice(0, 2).every((b, i) => highlightMatches(b, defaultFocusColors[i]))')
            evaluate('manager.settings.set_boolean("shell-menu-colors", true); '
                     'highlightButtons.forEach(b => b.remove_style_class_name("focused"));')
    finally:
        evaluate('highlightProbe.destroy(); interfaceSettings.reset("color-scheme"); '
                 'manager.settings.reset("background-opacity");')


def test_dynamic_transparency(evaluate, check):
    evaluate('manager.settings.set_enum("transparency-mode", 3);')
    time.sleep(.3)
    evaluate('''globalThis.transparency = dock._themeManager._transparency;
        globalThis.nearDock = false;
        globalThis.dockProximityChecks = 0;
        globalThis.dockStyleUpdates = 0;
        transparency._dockIsNear = () => { dockProximityChecks++; return nearDock; };
        transparency._updateSolidStyle();
        globalThis.dockStyleSignal = transparency.connect('solid-style-updated', () => dockStyleUpdates++);
        dockProximityChecks = 0;
        for (let i = 0; i < 10; i++) transparency._queueSolidStyle();''')
    try:
        time.sleep(.2)
        check('dynamic-dock-batches-proximity-and-skips-unchanged-style',
              'dockProximityChecks === 1 && dockStyleUpdates === 0')
        evaluate('nearDock = true; transparency._queueSolidStyle();')
        time.sleep(.2)
        check('dynamic-dock-applies-changed-style',
              'dockProximityChecks === 2 && dockStyleUpdates === 1 && dock.has_style_class_name("opaque")')
    finally:
        evaluate('transparency.disconnect(dockStyleSignal); delete transparency._dockIsNear; '
                 'manager.settings.reset("transparency-mode");')


def test_intellihide_batching(evaluate, check):
    evaluate('''globalThis.overlapProbe = dock._intellihide;
        globalThis.overlapWasEnabled = overlapProbe._isEnabled;
        globalThis.overlapTarget = overlapProbe._targetBox;
        if (!overlapWasEnabled) overlapProbe.enable();
        overlapProbe.updateTargetBox(new imports.gi.Clutter.ActorBox({x1:0,y1:0,x2:20,y2:500}));''')
    time.sleep(.4)
    evaluate('''globalThis.overlapChecks = 0;
        const original = overlapProbe._doCheckOverlap;
        overlapProbe._doCheckOverlap = function () { overlapChecks++; return original.call(this); };
        overlapProbe._checkOverlap();''')
    try:
        time.sleep(.35)
        check('intellihide-single-event-checks-once', 'overlapChecks === 1 && !overlapProbe._checkOverlapTimeoutId')
        evaluate('overlapChecks = 0; for (let i=0; i<10; i++) overlapProbe._checkOverlap()')
        time.sleep(.35)
        check('intellihide-burst-keeps-one-trailing-check', 'overlapChecks === 2 && !overlapProbe._checkOverlapTimeoutId')
    finally:
        evaluate('delete overlapProbe._doCheckOverlap; '
                 'if (!overlapWasEnabled) overlapProbe.disable(); '
                 'overlapProbe.updateTargetBox(overlapTarget);')


def test_intellihide_window_signals(evaluate, check):
    evaluate('''globalThis.signalsProbe = dock._intellihide;
        globalThis.intelliWasEnabled = signalsProbe._isEnabled;
        globalThis.probeActor = new imports.gi.St.Widget();
        globalThis.probeMetaWindow = {get_compositor_private: () => probeActor};
        globalThis.windowCallbacks = 0;
        signalsProbe._handledWindow = actor => actor === probeActor;
        signalsProbe._checkOverlap = () => windowCallbacks++;
        signalsProbe.disable();''')
    try:
        check('disabled-intellihide-ignores-new-windows', '''(() => {
            signalsProbe._windowCreated(null, probeMetaWindow);
            probeActor.notify('allocation');
            return signalsProbe._trackedWindows.size === 0 && windowCallbacks === 0;
        })()''')
        check('intellihide-registers-and-disconnects-once', '''(() => {
            signalsProbe.enable();
            signalsProbe._addWindowSignals(probeActor);
            signalsProbe._addWindowSignals(probeActor);
            probeActor.notify('allocation');
            signalsProbe.disable();
            probeActor.notify('allocation');
            return signalsProbe._trackedWindows.size === 0 && windowCallbacks === 1;
        })()''')
    finally:
        evaluate('''delete signalsProbe._handledWindow;
            delete signalsProbe._checkOverlap;
            probeActor.destroy();
            if (intelliWasEnabled) signalsProbe.enable();''')


def test_number_overlays(evaluate, check):
    # Theme changes from the preceding test may rebuild the icon actors.
    time.sleep(.5)
    check('unchanged-hidden-number-overlays-skip-writes', '''(() => {
        const icons = dock.dash.getAppIcons();
        if (!icons.length) return false;
        let styles = 0, numbers = 0;
        const restore = [];
        for (const icon of icons) {
            icon.toggleNumberOverlay(false);
            const style = icon._numberOverlayLabel.set_style;
            const text = icon._numberOverlayLabel.set_text;
            icon._numberOverlayLabel.set_style = function (...args) {
                styles++; return style.apply(this, args);
            };
            icon._numberOverlayLabel.set_text = function (...args) {
                numbers++; return text.apply(this, args);
            };
            restore.push(() => {
                delete icon._numberOverlayLabel.set_style;
                delete icon._numberOverlayLabel.set_text;
            });
        }
        try {for (let i=0; i<3; i++) dock.dash._redisplay();}
        finally {restore.forEach(f => f());}
        return styles === 0 && numbers === 0;
    })()''')
    state = evaluate('''dock.dash.toggleNumberOverlay(true);
        dock.dash.getAppIcons().map(icon => ({
        order: icon._numberOverlayOrder, visible: icon._numberOverlayBin.visible,
        style: icon._numberOverlayLabel.get_style(),
        text: icon._numberOverlayLabel.get_text(),
    }))''')
    assert all(icon['order'] < 0 or (icon['visible'] and icon['style'] and
               'font-size' in icon['style'] and icon['text'] == str(icon['order']))
               for icon in state), state
    check('number-overlays-style-on-first-show', 'true')
    evaluate('dock.dash.toggleNumberOverlay(false)')


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
    test_number_overlays(evaluate, check)
    test_dynamic_transparency(evaluate, check)
    test_intellihide_batching(evaluate, check)
    test_intellihide_window_signals(evaluate, check)
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
