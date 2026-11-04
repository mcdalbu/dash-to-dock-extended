import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';

Gio.Resource.load('/usr/share/gnome-shell/org.gnome.Shell.Extensions.src.gresource')._register();
const root = ARGV[0];
const {default: Preferences} = await import(`file://${root}/prefs.js`);
const [, data] = GLib.file_get_contents(`${root}/metadata.json`);
const metadata = JSON.parse(new TextDecoder().decode(data));
metadata.dir = Gio.File.new_for_path(root);
metadata.path = root;
Adw.init();
const preferences = new Preferences(metadata);
// The real preferences service registers the extension before resolving __().
// Our standalone test imports from the source folder, whose name omits @local.
const {ExtensionPreferences} = await import('resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js');
ExtensionPreferences.lookupByUUID = uuid =>
    [metadata.uuid, GLib.path_get_basename(root)].includes(uuid) ? preferences : null;
ExtensionPreferences.lookupByURL = () => preferences;
const window = new Adw.PreferencesWindow();
preferences.fillPreferencesWindow(window);
const controls = new Map();
let link;
const named = new Map();
function visit(widget) {
    if (widget.name?.startsWith('setting-')) named.set(widget.name.slice(8), widget);
    if (widget.get_buildable_id?.()) controls.set(widget.get_buildable_id(), widget);
    if (widget instanceof Gtk.Button && widget.label === 'Abrir GNOME Extended') link = widget;
    for (let child = widget.get_first_child(); child; child = child.get_next_sibling()) visit(child);
}
visit(window);
for (const id of ['dock_blur_switch', 'dock_blur_radius_scale', 'dock_blur_brightness_scale',
    'dock_blur_corner_radius_scale', 'icon_shadow_switch', 'icon_shadow_intensity_scale',
    'icon_shadow_offset_x_scale', 'icon_shadow_offset_y_scale', 'icon_shadow_blur_scale',
    'dock_outline_switch', 'dock_outline_intensity_scale', 'dock_shadow_size_scale', 'dock_shadow_intensity_scale']) {
    if (controls.has(id)) throw new Error(`Removed control remains: ${id}`);
}
for (const id of ['shell_menu_style_switch', 'shell_menu_colors_switch', 'shell_menu_keep_dock_radius_switch']) {
    if (!controls.get(id)?.get_ancestor(Gtk.ListBoxRow).visible) throw new Error(`Shell control missing: ${id}`);
}
const settings = preferences.getSettings();
const shadowToggle = named.get('shell-menu-shadow');
const shadowIntensity = named.get('dock-shadow-intensity');
const shadowSize = named.get('dock-shadow-size');
if (!shadowToggle || !shadowIntensity || !shadowSize) throw new Error('Outer shadow controls missing');
shadowToggle.active = false;
if (settings.get_boolean('shell-menu-shadow') || shadowSize.sensitive || shadowIntensity.sensitive)
    throw new Error('Outer shadow off binding');
shadowToggle.active = true;
shadowIntensity.value = 75;
shadowSize.value = 150;
if (settings.get_int('dock-shadow-intensity') !== 75 || settings.get_int('dock-shadow-size') !== 150)
    throw new Error('Outer shadow percentages');
settings.set_boolean('shell-menu-style', false);
if (shadowToggle.sensitive || shadowSize.sensitive) throw new Error('Shell profile controls sensitivity');
if (!link) throw new Error('Central preferences link missing');
window.destroy();
print('Dock preferences: blur/icon-shadow/manual-outline controls removed; optional outer shadow works; central preferences button exists');
