import { readFile, writeFile } from 'fs/promises';
import { existsSync } from 'fs';

const pin = process.argv[2];
if (!pin || !/^[0-9]{6,}$/.test(pin)) {
  console.error('Usage: npm run session:add -- <PIN_NUMERIC>');
  process.exit(1);
}

const envPath = '.env.local';
let content = '';
if (existsSync(envPath)) {
  content = await readFile(envPath, 'utf8');
}

const lines = content.split(/\r?\n/).filter(Boolean);
const nextLines = [];
let replaced = false;
for (const line of lines) {
  if (line.startsWith('VITE_PIN=')) {
    nextLines.push(`VITE_PIN=${pin}`);
    replaced = true;
  } else {
    nextLines.push(line);
  }
}
if (!replaced) {
  nextLines.push(`VITE_PIN=${pin}`);
}

await writeFile(envPath, nextLines.join('\n') + '\n', 'utf8');
console.log(`Session PIN written to ${envPath}: VITE_PIN=${pin}`);