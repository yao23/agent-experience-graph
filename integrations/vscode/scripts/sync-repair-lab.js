const fs = require('node:fs');
const path = require('node:path');

const extensionRoot = path.resolve(__dirname, '..');
const source = path.resolve(extensionRoot, '..', '..', 'experiments', 'public-repair-lab');
const destination = path.resolve(extensionRoot, 'repair-lab');
const verifiedSource = path.resolve(extensionRoot, '..', '..', 'experiences', 'verified.json');
const verifiedDestination = path.resolve(extensionRoot, 'verified-experiences', 'verified.json');

if (!fs.existsSync(source)) {
  throw new Error(`Repair lab source not found: ${source}`);
}

fs.rmSync(destination, {recursive: true, force: true});
fs.cpSync(source, destination, {
  recursive: true,
  filter: candidate => !candidate.includes(`${path.sep}__pycache__`)
});

if (!fs.existsSync(verifiedSource)) {
  throw new Error(`Verified experience library not found: ${verifiedSource}`);
}
fs.mkdirSync(path.dirname(verifiedDestination), {recursive: true});
fs.copyFileSync(verifiedSource, verifiedDestination);
