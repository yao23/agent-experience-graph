const fs = require('node:fs');
const path = require('node:path');

const extensionRoot = path.resolve(__dirname, '..');
const source = path.resolve(extensionRoot, '..', '..', 'experiments', 'public-repair-lab');
const destination = path.resolve(extensionRoot, 'repair-lab');

if (!fs.existsSync(source)) {
  throw new Error(`Repair lab source not found: ${source}`);
}

fs.rmSync(destination, {recursive: true, force: true});
fs.cpSync(source, destination, {
  recursive: true,
  filter: candidate => !candidate.includes(`${path.sep}__pycache__`)
});
