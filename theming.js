// -*- mode: js; js-indent-level: 4; indent-tabs-mode: nil -*-

import {
    Clutter,
    Cogl,
    Gio,
    GObject,
    Meta,
    St,
} from './dependencies/gi.js';

import {Main, PopupMenu} from './dependencies/shell/ui.js';
import {getPalette} from './ptyxisPalettes.js';
import {shellMenuSurfaceStyle} from './shellMenuStyle.js';

import {
    Docking,
    Utils,
} from './imports.js';

const {signals: Signals} = imports;
let hoverStyleId = 0;
const opacityFraction = (value, maximum = 100) => Math.max(0, Math.min(1, value / maximum));

/*
 * DEFAULT:  transparency given by theme
 * FIXED:    constant transparency chosen by user
 * DYNAMIC:  apply 'transparent' style when no windows are close to the dock
 * */
const TransparencyMode = {
    DEFAULT:  0,
    FIXED:    1,
    DYNAMIC:  3,
};

const Labels = Object.freeze({
    TRANSPARENCY: Symbol('transparency'),
    THEME_CHANGED: Symbol('theme-changed'),
});

export const PositionStyleClass = Object.freeze([
    'top',
    'right',
    'bottom',
    'left',
]);

function selectedPalette() {
    const {settings} = Docking.DockManager;
    return settings.shellMenuColors
        ? getPalette(settings.dockPalette,
            St.Settings.get().color_scheme !== St.SystemColorScheme.PREFER_LIGHT)
        : null;
}

function paletteColor(value, alpha = 255) {
    const Color = Clutter.Color ?? Cogl.Color;
    const [, color] = Color.from_string(value);
    color.alpha = alpha;
    return color;
}

function getShellMenuBox() {
    return Main.panel?.statusArea?.quickSettings?.menu?.box ??
        Main.panel?.statusArea?.dateMenu?.menu?.box;
}

/**
 * Apply surface options after the upstream theme/transparency styles, including
 * window-driven transparency changes. Keep icon actors and theme radii intact.
 *
 * @param dock
 * @param baseStyle
 * @param dynamicAlpha
 */
function applyDockSurfaceStyle(dock, baseStyle, dynamicAlpha) {
    const {settings} = Docking.DockManager;
    const background = dock.dash._background;
    let style = baseStyle ?? (background.get_style() || '');
    if (style && !style.trimEnd().endsWith(';'))
        style += ';';
    style += 'box-shadow: none;';
    const menu = settings.shellMenuStyle ? getShellMenuBox() : null;
    if (menu && settings.shellMenuStyle) {
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        style += shellMenuSurfaceStyle(menu.get_theme_node(), scale,
            settings.shellMenuKeepDockRadius, settings.shellMenuShadow,
            settings.dockShadowIntensity, settings.dockShadowSize);
    }
    const colorMenu = settings.shellMenuColors ? dock._themeManager?._colorMenu?.box : null;
    const palette = selectedPalette();
    if (colorMenu || palette) {
        const color = palette ? paletteColor(palette.Background)
            : colorMenu.get_theme_node().get_background_color();
        const alpha = dynamicAlpha ?? (settings.transparencyMode === TransparencyMode.FIXED
            ? opacityFraction(settings.backgroundOpacity, 1)
            : background.get_theme_node().get_background_color().alpha / 255);
        style += `background-color: rgba(${color.red}, ${color.green}, ${color.blue}, ${alpha});`;
    }
    if (colorMenu || palette)
        style += 'background-image: none;';
    // Apply palette colors after the per-side Shell borders so they cannot
    // overwrite the selected theme. Keep the existing widths and corner radii.
    if (palette) {
        const color = paletteColor(palette.Foreground, 48);
        style += `border-color: rgba(${color.red}, ${color.green}, ${color.blue}, ${color.alpha / 255});`;
    }
    background.set_style(style);
}

/**
 * Manage theme customization and custom theme support
 */
export class ThemeManager {
    constructor(dock) {
        this._signalsHandler = new Utils.GlobalSignalsHandler(this);
        this._bindSettingsChanges();
        this._actor = dock;
        this._dash = dock.dash;

        // Resolve the same theme hierarchy as the stock dash icon context menu.
        // Keep this probe hidden and outside the dock's CSS selectors.
        this._colorMenu = new PopupMenu.PopupMenu(dock, 0.5, Utils.getPosition());
        this._colorMenu.actor.add_style_class_name('app-menu');
        Main.uiGroup.add_child(this._colorMenu.actor);
        this._colorMenu.actor.hide();
        this._colorSeparator = new PopupMenu.PopupSeparatorMenuItem();
        this._colorMenu.addMenuItem(this._colorSeparator);
        this._colorHover = new PopupMenu.PopupMenuItem('');
        this._colorMenu.addMenuItem(this._colorHover);
        this._colorHover.actor.add_style_pseudo_class('hover');
        for (const actor of [this._colorMenu.box, this._colorSeparator._separator, this._colorHover.actor]) {
            this._signalsHandler.add(
                [actor, 'style-changed', () => this._queueUpdateShellMenuStyle()],
                [actor, 'notify::style', () => this._queueUpdateShellMenuStyle()]);
        }
        this._signalsHandler.add(this._dash._box, 'child-added',
            () => this._updateSeparatorColor());

        // initialize colors with generic values
        this._customizedBackground = {red: 0, green: 0, blue: 0, alpha: 0};
        this._customizedBorder = {red: 0, green: 0, blue: 0, alpha: 0};
        this._transparency = new Transparency(dock);

        this._signalsHandler.add([
            // update :overview pseudoclass
            Main.overview,
            'showing',
            this._onOverviewShowing.bind(this),
        ], [
            Main.overview,
            'hiding',
            this._onOverviewHiding.bind(this),
        ]);


        // Opening Quick Settings emits style changes even when its surface is
        // unchanged. Rebuilding the dock theme then would restart transparency
        // transitions. Compare the settled menu surface before applying it.
        const menuBox = getShellMenuBox();
        if (menuBox) {
            this._signalsHandler.add(
                [menuBox, 'style-changed', () => this._queueUpdateShellMenuStyle()],
                [menuBox, 'notify::style', () => this._queueUpdateShellMenuStyle()]);
        }

        this._signalsHandler.add(St.Settings.get(), 'notify::color-scheme',
            () => this._queueUpdateCustomTheme());
        this._signalsHandler.addWithLabel(Labels.THEME_CHANGED,
            St.ThemeContext.get_for_stage(global.stage), 'changed',
            () => this._queueUpdateCustomTheme(),
            Utils.SignalsHandlerFlags.CONNECT_AFTER);

        const maybeUpdateCustomTheme = () => {
            if (this._actor.mapped) {
                this._signalsHandler.unblockWithLabel(Labels.THEME_CHANGED);
                this._queueUpdateCustomTheme();
            } else {
                this._dequeueUpdateCustomTheme();
                this._signalsHandler.blockWithLabel(Labels.THEME_CHANGED);
            }
        };

        this._signalsHandler.add(this._actor, 'notify::mapped',
            () => maybeUpdateCustomTheme(),
            Utils.SignalsHandlerFlags.CONNECT_AFTER);

        maybeUpdateCustomTheme();

        // Set the initial overview pseudo-class state.
        if (Main.overview.visible)
            this._onOverviewShowing();
        else
            this._onOverviewHiding();

        // destroy themeManager when the managed actor is destroyed (e.g. extension unload)
        // in order to disconnect signals
        this._signalsHandler.add(this._actor, 'destroy', () => this.destroy());
    }

    destroy() {
        if (this._destroyed)
            return;
        this._destroyed = true;
        this._disableHoverStyle();
        this._restoreSeparatorColor();
        this._colorMenu?.destroy();
        this.emit('destroy');
        this._transparency.destroy();
        this._dequeueUpdateCustomTheme();
    }

    _queueUpdateCustomTheme() {
        if (this._updateLater)
            return;

        this._updateLater = Utils.laterAdd(Meta.LaterType.BEFORE_REDRAW, () => {
            this._updateLater = 0;
            this.updateCustomTheme();
        });
    }

    _getShellMenuSignature() {
        const {settings} = Docking.DockManager;
        const menu = settings.shellMenuStyle || settings.shellMenuColors ? getShellMenuBox() : null;
        if (!menu)
            return null;
        const node = menu.get_theme_node();
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        // Dock opacity is independent of the menu opacity. In particular,
        // ignore Gnome Extended briefly restoring its original menu fill.
        const surface = settings.shellMenuStyle ? shellMenuSurfaceStyle(
            node, scale, settings.shellMenuKeepDockRadius, settings.shellMenuShadow,
            settings.dockShadowIntensity, settings.dockShadowSize) : '';
        // Hidden popup descendants need their parent styles resolved first
        // when Shell replaces the theme (in particular dark/light switching).
        for (const actor of [this._colorMenu.actor, this._colorMenu.box,
            this._colorSeparator.actor, this._colorSeparator._separator, this._colorHover.actor])
            actor.ensure_style();
        const fill = settings.shellMenuColors ? [
            this._colorMenu.box.get_theme_node().get_background_color().to_string(),
            this._colorSeparator._separator.get_theme_node().get_background_color().to_string(),
            this._colorHover.actor.get_theme_node().get_background_color().to_string(),
        ].join(';') : '';
        return `${fill};${surface}`;
    }

    _queueUpdateShellMenuStyle() {
        const {settings} = Docking.DockManager;
        if (this._shellMenuLater || !(settings.shellMenuStyle || settings.shellMenuColors))
            return;
        this._shellMenuLater = Utils.laterAdd(Meta.LaterType.BEFORE_REDRAW, () => {
            const signature = this._getShellMenuSignature();
            this._shellMenuLater = 0;
            if (signature !== this._shellMenuSignature)
                this.updateCustomTheme();
        });
    }

    _dequeueUpdateCustomTheme() {
        if (this._shellMenuLater) {
            Utils.laterRemove(this._shellMenuLater);
            this._shellMenuLater = 0;
        }
        if (!this._updateLater)
            return;

        Utils.laterRemove(this._updateLater);
        delete this._updateLater;
    }

    _onOverviewShowing() {
        this._actor.add_style_pseudo_class('overview');
    }

    _onOverviewHiding() {
        this._actor.remove_style_pseudo_class('overview');
    }

    _updateDashOpacity() {
        const newAlpha = opacityFraction(Docking.DockManager.settings.backgroundOpacity, 1);

        const [backgroundColor, borderColor] = this._getDefaultColors();

        if (!backgroundColor)
            return;

        // Get the background and border alphas. We check the background alpha
        // for a minimum of .001 to prevent division by 0 errors
        const backgroundAlpha = Math.max(Math.round(backgroundColor.alpha / 2.55) / 100, .001);
        let borderAlpha = Math.round(borderColor.alpha / 2.55) / 100;

        // The border and background alphas should remain in sync
        // We also limit the borderAlpha to a maximum of 1 (full opacity)
        borderAlpha = Math.min((borderAlpha / backgroundAlpha) * newAlpha, 1);

        this._customizedBackground = `rgba(${
            backgroundColor.red},${
            backgroundColor.green},${
            backgroundColor.blue},${
            newAlpha})`;

        this._customizedBorder = `rgba(${
            borderColor.red},${
            borderColor.green},${
            borderColor.blue},${
            borderAlpha})`;
    }

    _getDefaultColors() {
        const palette = selectedPalette();
        if (palette)
            return [paletteColor(palette.Background), paletteColor(palette.Foreground, 48)];
        const menu = Docking.DockManager.settings.shellMenuColors ? this._colorMenu?.box : null;
        if (menu) {
            const node = menu.get_theme_node();
            return [node.get_background_color(), node.get_border_color(St.Side.TOP)];
        }
        // Remove custom style
        const oldStyle = this._dash._background.get_style();
        this._dash._background.set_style(null);

        const themeNode = this._dash._background.get_theme_node();
        this._dash._background.set_style(oldStyle);

        const backgroundColor = themeNode.get_background_color();

        // Just in case the theme has different border colors ..
        // We want to find the inside border-color of the dock because it is
        // the side most visible to the user. We do this by finding the side
        // opposite the position
        const position = Utils.getPosition();
        let side = position + 2;
        if (side > 3)
            side = Math.abs(side - 4);

        const borderColor = themeNode.get_border_color(side);

        return [backgroundColor, borderColor];
    }

    _updateDashColor() {
        // Retrieve the color. If needed we will adjust it before passing it to
        // this._transparency.
        let [backgroundColor] = this._getDefaultColors();

        if (!backgroundColor)
            return;

        const {settings} = Docking.DockManager;

        if (settings.customBackgroundColor && !(settings.shellMenuColors && this._colorMenu)) {
            // When applying a custom color, we need to check the alpha value,
            // if not the opacity will always be overridden by the color below.
            // Note that if using 'dynamic' transparency modes,
            // the opacity will be set by the opaque/transparent styles anyway.
            let newAlpha = Math.round(backgroundColor.alpha / 2.55) / 100;

            ({backgroundColor} = settings);
            // backgroundColor is a string like rgb(0,0,0)
            const Color = Clutter.Color ?? Cogl.Color;
            const [ret, color] = Color.from_string(backgroundColor);
            if (!ret) {
                logError(new Error(`${backgroundColor} is not a valid color string`));
                return;
            }

            if (settings.transparencyMode === TransparencyMode.FIXED) {
                newAlpha = opacityFraction(settings.backgroundOpacity, 1);
                this._customizedBackground =
                    `rgba(${color.red}, ${color.green}, ${color.blue}, ${newAlpha})`;
            } else {
                this._customizedBackground = backgroundColor;
            }

            this._customizedBorder = this._customizedBackground;

            color.alpha = newAlpha * 255;
            this._transparency.setColor(color);
        } else {
            // backgroundColor is a {Clutter,Cogl}.Color object
            this._transparency.setColor(backgroundColor);
        }
    }

    _disableHoverStyle() {
        if (this._hoverFile) {
            this._unloadHoverStylesheet();
            this._hoverFile.delete(null);
        }
        this._hoverFile = null;
        this._hoverTheme = null;
        this._hoverCss = null;
        if (this._hoverClass)
            this._actor.remove_style_class_name(this._hoverClass);
    }

    _unloadHoverStylesheet() {
        // Shell copies custom stylesheets to the replacement theme. The old
        // theme stored here can differ from the current theme during teardown
        // on unlock. Remove both references before deleting the temporary file.
        const theme = St.ThemeContext.get_for_stage(global.stage).get_theme();
        for (const owner of new Set([this._hoverTheme, theme]))
            owner?.unload_stylesheet(this._hoverFile);
    }

    _updateHoverStyle() {
        const {settings} = Docking.DockManager;
        const menuHover = settings.shellMenuColors && this._colorHover?.actor;
        if (!menuHover) {
            this._disableHoverStyle();
            return;
        }

        // A scoped stylesheet also covers icons created/replaced after startup,
        // without overwriting their inline styles. Keep menu hover colors and
        // their cleanup in one stylesheet.
        this._hoverClass ??= `shell-menu-hover-profile-${++hoverStyleId}`;
        let css = '';
        if (menuHover) {
            const palette = selectedPalette();
            const color = palette ? paletteColor(palette.Foreground, 32)
                : menuHover.get_theme_node().get_background_color();
            const scope = `#dashtodockContainer.${this._hoverClass} #dash .dash-item-container`;
            css += `${scope} .app-well-app:hover .overview-icon,` +
                `${scope} .overview-tile:hover .overview-icon,` +
                `${scope} .show-apps:hover .overview-icon {` +
                `background-color: rgba(${color.red}, ${color.green}, ${color.blue}, ${color.alpha / 255}) !important;}`;
        }
        const theme = St.ThemeContext.get_for_stage(global.stage).get_theme();
        if (this._hoverTheme === theme && this._hoverCss === css)
            return;

        if (!this._hoverFile) {
            const [file, stream] = Gio.File.new_tmp('dash-to-dock-extended-hover-XXXXXX');
            stream.close(null);
            this._hoverFile = file;
        } else {
            this._unloadHoverStylesheet();
        }
        this._hoverFile.replace_contents(css, null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        // Cache before loading: load_stylesheet emits ThemeContext::changed.
        this._hoverCss = css;
        this._hoverTheme = theme;
        this._actor.add_style_class_name(this._hoverClass);
        theme.load_stylesheet(this._hoverFile);
    }

    _updateCustomStyleClasses() {
        if (Docking.DockManager.settings.shellMenuStyle)
            this._actor.add_style_class_name('shell-menu-style');
        else
            this._actor.remove_style_class_name('shell-menu-style');
        const {settings} = Docking.DockManager;

        if (settings.applyCustomTheme)
            this._actor.add_style_class_name('dashtodock');
        else
            this._actor.remove_style_class_name('dashtodock');

        this._updateHoverStyle();

        if (settings.customThemeShrink)
            this._actor.add_style_class_name('shrink');
        else
            this._actor.remove_style_class_name('shrink');

        if (settings.runningIndicatorStyle !== 0)
            this._actor.add_style_class_name('running-dots');
        else
            this._actor.remove_style_class_name('running-dots');

        // If not the built-in theme option is not selected
        if (!settings.applyCustomTheme) {
            if (settings.forceStraightCorner)
                this._actor.add_style_class_name('straight-corner');
            else
                this._actor.remove_style_class_name('straight-corner');
        } else {
            this._actor.remove_style_class_name('straight-corner');
        }
    }

    _restoreSeparatorColor() {
        if (this._styledSeparator) {
            this._styledSeparator.disconnect(this._separatorDestroyId);
            this._styledSeparator.set_style(this._separatorOriginalStyle);
        }
        this._styledSeparator = null;
        this._separatorDestroyId = 0;
    }

    _updateSeparatorColor() {
        const separator = this._dash._separator;
        if (this._styledSeparator && this._styledSeparator !== separator)
            this._restoreSeparatorColor();
        if (!Docking.DockManager.settings.shellMenuColors) {
            this._restoreSeparatorColor();
            return;
        }
        if (!separator || !this._colorSeparator)
            return;
        if (!this._styledSeparator) {
            this._styledSeparator = separator;
            this._separatorOriginalStyle = separator.get_style();
            this._separatorDestroyId = separator.connect('destroy', () => {
                this._styledSeparator = null;
                this._separatorDestroyId = 0;
            });
        }
        const palette = selectedPalette();
        const color = palette ? paletteColor(palette.Foreground, 64)
            : this._colorSeparator._separator.get_theme_node().get_background_color();
        const original = this._separatorOriginalStyle?.trim() || '';
        const prefix = original && !original.endsWith(';') ? `${original};` : original;
        separator.set_style(`${prefix}background-color: ` +
            `rgba(${color.red}, ${color.green}, ${color.blue}, ${color.alpha / 255});`);
    }

    updateCustomTheme() {
        if (!this._actor.mapped)
            return;

        const signature = this._getShellMenuSignature();
        this._updateCustomStyleClasses();
        this._updateDashOpacity();
        this._updateDashColor();
        if (!this._adjustTheme())
            applyDockSurfaceStyle(this._actor);
        this._updateSeparatorColor();
        this._shellMenuSignature = signature;
        this.emit('updated');
    }

    /**
     * Reimported back and adapted from atomdock
     */
    _adjustTheme() {
        const {settings} = Docking.DockManager;

        // Remove prior style edits
        this._dash._background.set_style(null);
        this._transparency.disable();

        // If built-in theme is enabled do nothing else
        if (settings.applyCustomTheme)
            return false;

        let newStyle = '';
        const position = Utils.getPosition(settings);

        // obtain theme border settings
        const themeNode = this._dash._background.get_theme_node();
        const borderColor = themeNode.get_border_color(St.Side.TOP);
        const borderWidth = themeNode.get_border_width(St.Side.TOP);

        // We're copying border and corner styles to left border and top-left
        // corner, also removing bottom border and bottom-right corner styles
        let borderMissingStyle = '';

        if (this._rtl && (position !== St.Side.RIGHT)) {
            borderMissingStyle = `border-right: ${borderWidth}px solid ${
                borderColor.to_string()};`;
        } else if (!this._rtl && (position !== St.Side.LEFT)) {
            borderMissingStyle = `border-left: ${borderWidth}px solid ${
                borderColor.to_string()};`;
        }

        newStyle = borderMissingStyle;

        if (newStyle) {
            // I do call set_style possibly twice so that only the background gets the transition.
            // The transition-property css rules seems to be unsupported
            this._dash._background.set_style(newStyle);
        }

        // Customize background
        const fixedTransparency = settings.transparencyMode === TransparencyMode.FIXED;
        const defaultTransparency = settings.transparencyMode === TransparencyMode.DEFAULT;
        if (!defaultTransparency && !fixedTransparency) {
            this._transparency.enable();
            return true;
        } else if (!defaultTransparency || settings.customBackgroundColor) {
            newStyle = `${newStyle}background-color:${this._customizedBackground}; ` +
                       `border-color:${this._customizedBorder}; ` +
                       'transition-delay: 0s; transition-duration: 0.250s;';
            this._dash._background.set_style(newStyle);
        }
        return false;
    }

    _bindSettingsChanges() {
        const keys = ['transparency-mode',
            'dock-palette',
            'shell-menu-style',
            'shell-menu-colors',
            'shell-menu-keep-dock-radius',
            'shell-menu-shadow',
            'dock-shadow-intensity',
            'dock-shadow-size',
            'customize-alphas',
            'min-alpha',
            'max-alpha',
            'background-opacity',
            'custom-background-color',
            'background-color',
            'apply-custom-theme',
            'custom-theme-shrink',
            'custom-theme-running-dots',
            'extend-height',
            'force-straight-corner'];

        const sliderKeys = new Set(['dock-shadow-intensity', 'dock-shadow-size',
            'min-alpha', 'max-alpha', 'background-opacity']);
        this._signalsHandler.addWithLabel(Labels.THEME_CHANGED, ...keys.map(key => [
            Docking.DockManager.settings,
            `changed::${key}`,
            () => sliderKeys.has(key) ? this._queueUpdateCustomTheme() : this.updateCustomTheme(),
        ]));
    }
}
Signals.addSignalMethods(ThemeManager.prototype);

/**
 * The following class is based on the following upstream commit:
 * https://git.gnome.org/browse/gnome-shell/commit/?id=447bf55e45b00426ed908b1b1035f472c2466956
 * Transparency when free-floating
 */
class Transparency {
    constructor(dock) {
        this._dash = dock.dash;
        this._actor = this._dash._container;
        this._dockActor = dock;
        this._dock = dock;
        this._panel = Main.panel;
        this._position = Utils.getPosition();

        // All these properties are replaced with the ones in the .dummy-opaque
        // and .dummy-transparent css classes
        this._backgroundColor = '0,0,0';
        this._transparentAlpha = '0.2';
        this._opaqueAlpha = '1';
        this._transparentAlphaBorder = '0.1';
        this._opaqueAlphaBorder = '0.5';
        this._transparentTransition = '0ms';
        this._opaqueTransition = '0ms';
        this._base_actor_style = '';

        this._signalsHandler = new Utils.GlobalSignalsHandler();
        this._trackedWindows = new Map();
        this._solidLater = 0;
    }

    enable() {
        // ensure I never double-register/inject
        // although it should never happen
        this.disable();

        this._base_actor_style = this._actor.get_style();
        if (!this._base_actor_style)
            this._base_actor_style = '';


        let addedSignal = 'child-added';
        let removedSignal = 'child-removed';

        // for compatibility with Gnome Shell 45
        if (GObject.signal_lookup('actor-added', global.window_group)) {
            addedSignal = 'actor-added';
            removedSignal = 'actor-removed';
        }

        this._signalsHandler.addWithLabel(Labels.TRANSPARENCY, [
            global.window_group,
            addedSignal,
            this._onWindowActorAdded.bind(this),
        ], [
            global.window_group,
            removedSignal,
            this._onWindowActorRemoved.bind(this),
        ], [
            global.window_manager,
            'switch-workspace',
            this._queueSolidStyle.bind(this),
        ], [
            Main.overview,
            'hiding',
            this._queueSolidStyle.bind(this),
        ], [
            Main.overview,
            'showing',
            this._queueSolidStyle.bind(this),
        ]);

        for (const child of global.window_group.get_children())
            this._onWindowActorAdded(null, child);

        this._updateStyles();
        this._updateSolidStyle();

        this.emit('transparency-enabled');
    }

    disable() {
        // ensure I never double-register/inject
        // although it should never happen
        this._signalsHandler.removeWithLabel(Labels.TRANSPARENCY);
        if (this._solidLater) {
            Utils.laterRemove(this._solidLater);
            this._solidLater = 0;
        }
        this._lastSolidStyle = null;
        this._lastIsNear = null;

        for (const key of this._trackedWindows.keys()) {
            this._trackedWindows.get(key).forEach(id => {
                key.disconnect(id);
            });
        }
        this._trackedWindows.clear();

        this.emit('transparency-disabled');
    }

    destroy() {
        this.disable();
        this._signalsHandler.destroy();
    }

    _onWindowActorAdded(container, metaWindowActor) {
        // The group also holds backgrounds and other extensions' blur actors.
        if (!(metaWindowActor instanceof Meta.WindowActor) ||
            metaWindowActor.get_meta_window()?.get_wm_class() === 'Gnome-shell' ||
            this._trackedWindows.has(metaWindowActor))
            return;

        const signalIds = [];
        ['notify::allocation', 'notify::visible'].forEach(s => {
            signalIds.push(metaWindowActor.connect(s, this._queueSolidStyle.bind(this)));
        });
        this._trackedWindows.set(metaWindowActor, signalIds);
        if (container)
            this._queueSolidStyle();
    }

    _onWindowActorRemoved(container, metaWindowActor) {
        if (!this._trackedWindows.get(metaWindowActor))
            return;

        this._trackedWindows.get(metaWindowActor).forEach(id => {
            metaWindowActor.disconnect(id);
        });
        this._trackedWindows.delete(metaWindowActor);
        this._queueSolidStyle();
    }

    _queueSolidStyle() {
        if (this._solidLater)
            return;
        this._solidLater = Utils.laterAdd(Meta.LaterType.BEFORE_REDRAW, () => {
            this._solidLater = 0;
            this._updateSolidStyle();
        });
    }

    _updateSolidStyle() {
        const isNear = this._dockIsNear();
        const style = isNear ? this._opaque_style : this._transparent_style;
        if (isNear === this._lastIsNear && style === this._lastSolidStyle)
            return;
        this._lastIsNear = isNear;
        this._lastSolidStyle = style;
        this._dockActor.remove_style_class_name(isNear ? 'transparent' : 'opaque');
        this._dockActor.add_style_class_name(isNear ? 'opaque' : 'transparent');

        const alpha = isNear ? this._opaqueAlpha : this._transparentAlpha;
        applyDockSurfaceStyle(this._dock, style, Math.round(alpha * 255) / 255);
        this.emit('solid-style-updated', isNear);
    }

    _dockIsNear() {
        if (this._dockActor.has_style_pseudo_class('overview'))
            return false;
        /* Get all the windows in the active workspace that are in the primary monitor and visible */
        const activeWorkspace = global.workspace_manager.get_active_workspace();
        const dash = this._dash;
        /* Check if at least one window is near enough to the panel.
         * If the dock is hidden, we need to account for the space it would take
         * up when it slides out. This is avoid an ugly transition.
         * */
        let factor = 0;
        if (!Docking.DockManager.settings.dockFixed &&
            this._dock.dockState === Docking.State.HIDDEN)
            factor = 1;
        const [leftCoord, topCoord] = this._actor.get_transformed_position();
        let threshold;
        if (this._position === St.Side.LEFT)
            threshold = leftCoord + this._actor.get_width() * (factor + 1);
        else if (this._position === St.Side.RIGHT)
            threshold = leftCoord - this._actor.get_width() * factor;
        else if (this._position === St.Side.TOP)
            threshold = topCoord + this._actor.get_height() * (factor + 1);
        else
            threshold = topCoord - this._actor.get_height() * factor;

        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        return activeWorkspace.list_windows().some(metaWindow => {
            if (metaWindow.get_monitor() !== dash._monitorIndex ||
                !metaWindow.showing_on_its_workspace() ||
                metaWindow.get_window_type() === Meta.WindowType.DESKTOP ||
                metaWindow.skip_taskbar)
                return false;

            const frame = metaWindow.get_frame_rect();
            if (this._position === St.Side.LEFT)
                return frame.x < threshold + 5 * scale;
            if (this._position === St.Side.RIGHT)
                return frame.x + frame.width > threshold - 5 * scale;
            if (this._position === St.Side.TOP)
                return frame.y < threshold + 5 * scale;
            return frame.y + frame.height > threshold - 5 * scale;
        });
    }

    _updateStyles() {
        this._getAlphas();

        this._transparent_style = `${this._base_actor_style
        }background-color: rgba(${
            this._backgroundColor}, ${this._transparentAlpha});` +
            `border-color: rgba(${
                this._backgroundColor}, ${this._transparentAlphaBorder});` +
            `transition-duration: ${this._transparentTransition}ms;`;

        this._opaque_style = `${this._base_actor_style
        }background-color: rgba(${
            this._backgroundColor}, ${this._opaqueAlpha});` +
            `border-color: rgba(${
                this._backgroundColor},${this._opaqueAlphaBorder});` +
            `transition-duration: ${this._opaqueTransition}ms;`;

        this.emit('styles-updated');
    }

    setColor(color) {
        this._backgroundColor = `${color.red},${color.green},${color.blue}`;
        this._updateStyles();
    }

    _getAlphas() {
        // Create dummy object and add to the uiGroup to get it to the stage
        const dummyObject = new St.Bin({
            name: 'dashtodockContainer',
        });
        Main.uiGroup.add_child(dummyObject);

        dummyObject.add_style_class_name('dummy-opaque');
        let themeNode = dummyObject.get_theme_node();
        this._opaqueAlpha = themeNode.get_background_color().alpha / 255;
        this._opaqueAlphaBorder = themeNode.get_border_color(0).alpha / 255;
        this._opaqueTransition = themeNode.get_transition_duration();

        dummyObject.add_style_class_name('dummy-transparent');
        themeNode = dummyObject.get_theme_node();
        this._transparentAlpha = themeNode.get_background_color().alpha / 255;
        this._transparentAlphaBorder = themeNode.get_border_color(0).alpha / 255;
        this._transparentTransition = themeNode.get_transition_duration();

        Main.uiGroup.remove_child(dummyObject);

        const {settings} = Docking.DockManager;

        if (settings.customizeAlphas) {
            this._opaqueAlpha = settings.maxAlpha;
            this._opaqueAlphaBorder = this._opaqueAlpha / 2;
            this._transparentAlpha = settings.minAlpha;
            this._transparentAlphaBorder = this._transparentAlpha / 2;
        }
    }
}
Signals.addSignalMethods(Transparency.prototype);
