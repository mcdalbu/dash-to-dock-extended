// Verify Shell menu border/corner scaling, including the option to keep dock corners.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../shellMenuStyle.js'), 'utf8')
    .replace(/\bexport /g, '') + '\nthis.style = shellMenuSurfaceStyle;', sandbox);
const node = {
    get_border_width: side => 2 * (side + 1),
    get_border_color: () => ({red: 10, green: 20, blue: 30, alpha: 128}),
    get_box_shadow: () => ({xoffset: -4, yoffset: 6, blur: 16, spread: 2, inset: false,
        color: {red: 10, green: 20, blue: 30, alpha: 128}}),
    get_border_radius: side => 12 + side * 2,
};
for (const scale of [1, 2]) {
    const css = sandbox.style(node, scale);
    for (const [side, i] of ['top', 'right', 'bottom', 'left'].map((side, i) => [side, i]))
        assert(css.includes(`border-${side}: ${2 * (i + 1) / scale}px solid rgba(10, 20, 30, ${128 / 255});`));
    assert(css.includes(`border-radius: ${[12, 14, 16, 18].map(v => `${v / scale}px`).join(' ')};`));
    assert(css.includes(`box-shadow: ${[-4, 6, 16, 2].map(v => `${v / scale}px`).join(' ')} rgba(10, 20, 30, ${128 / 255});`));
    assert(sandbox.style(node, scale, false, false).includes('box-shadow: none;'));
    assert(sandbox.style(node, scale, false, true, 0).includes('box-shadow: none;'));
    assert(sandbox.style(node, scale, false, true, 100, 0).includes('box-shadow: none;'));
    const adjusted = sandbox.style(node, scale, false, true, 50, 150);
    assert(adjusted.includes(`box-shadow: ${[-4, 6, 16, 2].map(v => `${v / scale * 1.5}px`).join(' ')} rgba(10, 20, 30, ${128 / 255 * 0.5});`));
    const kept = sandbox.style(node, scale, true);
    assert(!kept.includes('border-radius:'));
    assert(kept.includes('border-top:'));
}
console.log('PASS: Shell menu borders/corners at 1x/2x; optional dock radius; optional outer shadow, intensity and size');
