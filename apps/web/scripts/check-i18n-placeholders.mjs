// Fails the build when a t('key') call omits the values that the message needs.
//
// next-intl does not throw on a missing placeholder — it renders the literal
// "{hero}" to the user. That shipped once on the programmatic SEO pages
// ("Situational answers to what {hero} does best"), where it was live on 127
// pages before anyone noticed. A build failure is cheaper than that.
//
// The checker tracks the namespace bound by the nearest preceding
// useTranslations()/getTranslations() in the file, so a key name that carries a
// placeholder in one namespace but not another is not a false positive.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const messages = JSON.parse(
  readFileSync(join(webRoot, 'src/i18n/messages/en.json'), 'utf8'),
);

function resolve(namespace, key) {
  let node = messages[namespace];
  for (const part of key.split('.')) {
    if (node == null || typeof node !== 'object') return undefined;
    node = node[part];
  }
  return typeof node === 'string' ? node : undefined;
}

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) yield* walk(full);
    else if (full.endsWith('.tsx') || full.endsWith('.ts')) yield full;
  }
}

const NS = /\b(?:useTranslations|getTranslations)\(\s*['"]([\w.]+)['"]\s*\)/;
const CALL = /\bt\(\s*['"]([\w.]+)['"]\s*\)/g;

const violations = [];
for (const file of walk(join(webRoot, 'src'))) {
  let namespace = null;
  readFileSync(file, 'utf8')
    .split('\n')
    .forEach((line, i) => {
      const ns = line.match(NS);
      if (ns) namespace = ns[1];
      if (!namespace) return;
      for (const match of line.matchAll(CALL)) {
        const value = resolve(namespace, match[1]);
        if (value !== undefined && /\{\w+\}/.test(value)) {
          violations.push(
            `${file.replace(webRoot + '/', '')}:${i + 1}  ` +
              `t('${match[1]}') in '${namespace}' needs a value`,
          );
        }
      }
    });
}

if (violations.length) {
  console.error('i18n: message needs a value but none was passed:');
  for (const v of violations) console.error('  ' + v);
  process.exit(1);
}
console.log('i18n placeholders ok');
