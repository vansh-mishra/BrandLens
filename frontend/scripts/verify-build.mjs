import { existsSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const dist = join(process.cwd(), 'dist')
const index = join(dist, 'index.html')
const assets = join(dist, 'assets')

function fail(message) {
  console.error(`Frontend build verification failed: ${message}`)
  process.exit(1)
}

if (!existsSync(index) || !statSync(index).isFile()) {
  fail('dist/index.html was not created. Run `npm run build` first.')
}
if (!existsSync(assets) || !statSync(assets).isDirectory()) {
  fail('dist/assets directory was not created.')
}

const files = readdirSync(assets)
const jsFiles = files.filter(file => /\.js$/i.test(file) && statSync(join(assets, file)).size > 0)
const cssFiles = files.filter(file => /\.css$/i.test(file) && statSync(join(assets, file)).size > 0)

if (jsFiles.length === 0) fail('No non-empty compiled JavaScript bundle was found in dist/assets.')
if (cssFiles.length === 0) fail('No non-empty compiled CSS bundle was found in dist/assets.')

console.log('Frontend production build verified.')
console.log(`  Entry point: ${index}`)
console.log(`  JavaScript bundles: ${jsFiles.length}`)
console.log(`  CSS bundles: ${cssFiles.length}`)
