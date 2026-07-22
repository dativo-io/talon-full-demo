import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const invoicePath = fileURLToPath(new URL('../src/invoice.mjs', import.meta.url));
const buggyLine = '    return sum + Math.round(taxed * 100) / 100;';
const fixedLine = '    return sum + taxed;';

const source = await readFile(invoicePath, 'utf8');
const occurrences = source.split(buggyLine).length - 1;

if (occurrences !== 1) {
  throw new Error(`expected exactly one known billing regression, found ${occurrences}`);
}

await writeFile(invoicePath, source.replace(buggyLine, fixedLine));
console.log('Applied the expected one-line billing correction.');
