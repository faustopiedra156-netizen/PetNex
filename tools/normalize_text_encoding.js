const fs = require('fs');
const path = require('path');

const root = process.cwd();

function walk(dir, extensions, ignored = []) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (ignored.some((item) => full.includes(item))) continue;
    if (entry.isDirectory()) {
      results.push(...walk(full, extensions, ignored));
    } else if (extensions.includes(path.extname(entry.name))) {
      results.push(full);
    }
  }
  return results;
}

function replaceAll(text, replacements) {
  let output = text;
  for (const [from, to] of replacements) {
    output = output.split(from).join(to);
  }
  return output;
}

const htmlReplacements = [
  ['\u00c3\u00a1', '&aacute;'],
  ['\u00c3\u00a9', '&eacute;'],
  ['\u00c3\u00ad', '&iacute;'],
  ['\u00c3\u00b3', '&oacute;'],
  ['\u00c3\u00ba', '&uacute;'],
  ['\u00c3\u00b1', '&ntilde;'],
  ['\u00c3\u0081', '&Aacute;'],
  ['\u00c3\u0089', '&Eacute;'],
  ['\u00c3\u008d', '&Iacute;'],
  ['\u00c3\u0093', '&Oacute;'],
  ['\u00c3\u009a', '&Uacute;'],
  ['\u00c3\u0091', '&Ntilde;'],
  ['\u00c2\u00bf', '&iquest;'],
  ['\u00c2\u00a1', '&iexcl;'],
  ['\u00c2\u00b7', '&middot;'],
  ['\u00e2\u0098\u0085', '&#9733;'],
  ['\u00e2\u0080\u00a2', '&bull;'],
];

const pyReplacements = [
  ['\u00c3\u00a1', '\\u00e1'],
  ['\u00c3\u00a9', '\\u00e9'],
  ['\u00c3\u00ad', '\\u00ed'],
  ['\u00c3\u00b3', '\\u00f3'],
  ['\u00c3\u00ba', '\\u00fa'],
  ['\u00c3\u00b1', '\\u00f1'],
  ['\u00c3\u0081', '\\u00c1'],
  ['\u00c3\u0089', '\\u00c9'],
  ['\u00c3\u008d', '\\u00cd'],
  ['\u00c3\u0093', '\\u00d3'],
  ['\u00c3\u009a', '\\u00da'],
  ['\u00c3\u0091', '\\u00d1'],
  ['\u00c2\u00bf', '\\u00bf'],
  ['\u00c2\u00a1', '\\u00a1'],
  ['\u00c2\u00b7', '\\u00b7'],
];

for (const file of walk(path.join(root, 'templates'), ['.html', '.txt'])) {
  const current = fs.readFileSync(file, 'utf8');
  const next = replaceAll(current, htmlReplacements);
  if (next !== current) fs.writeFileSync(file, next, 'utf8');
}

for (const dir of ['citas', 'petcare_loja']) {
  for (const file of walk(path.join(root, dir), ['.py'], [`${path.sep}migrations${path.sep}000`, `${path.sep}migrations${path.sep}0010`, `${path.sep}migrations${path.sep}0011`, `${path.sep}migrations${path.sep}0012`, `${path.sep}migrations${path.sep}0013`, `${path.sep}migrations${path.sep}0014`, `${path.sep}migrations${path.sep}0015`, `${path.sep}migrations${path.sep}0016`])) {
    const current = fs.readFileSync(file, 'utf8');
    const next = replaceAll(current, pyReplacements);
    if (next !== current) fs.writeFileSync(file, next, 'utf8');
  }
}
