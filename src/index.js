#!/usr/bin/env node

const fs = require('fs')
const path = require('path')
const python = require('./py')
// const util = require('util')
// const execFile = util.promisify(require('child_process').execFile)
const { execFile, spawnSync } = require('child_process')
let pkgUp

async function readPackageJson () {
  if (!pkgUp) {
    pkgUp = (await import('pkg-up')).pkgUp
  }

  const pkgPath = await pkgUp()
  if (!pkgPath) {
    throw new Error('Could not find package.json')
  }
  const content = fs.readFileSync(pkgPath, 'utf8')
  return {
    path: pkgPath,
    json: JSON.parse(content)
  }
}

async function savePackageJson(jsonPath, json) {
  fs.writeFileSync(jsonPath, JSON.stringify(json, null, 2))
}

async function readAndEnsureHeaders() {
  const { path: jsonPath, json } = await readPackageJson()
  if (json.asCBind === undefined) {
    json.asCBind = {}
  }
  if (json.asCBind.headers === undefined) {
    json.asCBind.headers = []
  }
  if (json.asCBind.includePath === undefined) {
    json.asCBind.includePath = [
      '/usr/include',
      '/usr/local/include'
    ]
  }
  return {  jsonPath, json }
}

async function add(args) {
  if (args.length === 0) {
    console.error('Usage: as-c-bind add <path to header file>')
    process.exit(1)
  }

  const { jsonPath, json } = await readAndEnsureHeaders()
  for (const arg of args) {
    if (json.asCBind.headers.includes(arg)) {
      console.log(`${arg} is already included - skipping`)
      continue
    }
    let foundPath
    // Check if it exists
    if (fs.existsSync(arg)) {
      json.asCBind.headers.push(arg)
      foundPath = arg
      continue
    }
    // Check if it exists in the include path
    for (const includePath of json.asCBind.includePath) {
      const fullPath = path.join(includePath, arg)
      if (fs.existsSync(fullPath)) {
        json.asCBind.headers.push(arg)
        foundPath = fullPath
        continue
      }
    }
    if (!foundPath) {
      console.error(`Could not find ${arg}`)
      pyProcess.exit(1)
    } else {
      console.log(`Added ${arg} (found at ${foundPath})`)
    }
  }
  savePackageJson(jsonPath, json)

  const execPath = await python.setup()
  const pyProcess = execFile(execPath, [path.join(__dirname, '..', 'py-src', 'gen_header.py'), jsonPath])
  // Pipe stdout and stderr
  pyProcess.stdout.pipe(process.stdout)
  pyProcess.stderr.pipe(process.stderr)
}

async function init(args) {
  if (args.length !== 1) {
    console.error('Usage: as-c-bind init <path to new project>')
    process.exit(1)
  }

  // Run npx asinit <path>
  // TODO: Try to call it directly instead of using npx
  process.stdin.setRawMode(false) // TODO: Is this needed?
  const proc = spawnSync('npx', ['asinit', args[0]], { stdio: 'inherit' })
  process.stdin.setRawMode(true)
  // If the exit code is not 0 or the directory does not exist, exit
  if (proc.status !== 0 || !fs.existsSync(args[0])) {
    console.error('asinit failed')
    process.exit(1)
  }

  // Change directory to the new project
  process.chdir(args[0])

  const npmInstallProcess = spawnSync('npm', ['i', '/home/heath/headerconv2/as-c-bind'], { stdio: 'inherit' })
  if (npmInstallProcess.status !== 0) {
    console.error('npm install failed')
    process.exit(1)
  }

  const asconfig = JSON.parse(fs.readFileSync('asconfig.json', 'utf8'))
  asconfig.options.path = './headers/'
  for (const target of Object.keys(asconfig.targets)) {
    asconfig.targets[target].asCBind = { outDir: `./build/${target}-c/` }
  }
  fs.writeFileSync('asconfig.json', JSON.stringify(asconfig, null, 2))

  const tsconfig = JSON.parse(fs.readFileSync('./assembly/tsconfig.json', 'utf8'))
  if (!tsconfig.compilerOptions) {
    tsconfig.compilerOptions = {}
  }
  tsconfig.compilerOptions.baseUrl = '.'
  if (!tsconfig.compilerOptions.paths) {
    tsconfig.compilerOptions.paths = {}
  }
  tsconfig.compilerOptions.paths['*'] = ['../headers/*/index.ts']
  fs.writeFileSync('./assembly/tsconfig.json', JSON.stringify(tsconfig, null, 2))

  fs.mkdirSync('build/debug-c/')
  fs.mkdirSync('build/release-c/')

  console.log()
  console.log('as-c-bind init complete')
  console.log('You can now add headers with \'npx as-c-bind add <path to header file>\'')
}

async function build(args) {
  if (args.length < 1) {
    console.error('Usage: as-c-bind build <target> [output directory] [asc args]')
    process.exit(1)
  }

  if (!pkgUp) {
    pkgUp = (await import('pkg-up')).pkgUp
  }
  const pkgPath = await pkgUp()
  if (!pkgPath) {
    console.error('Could not find package.json, is this an AssemblyScript project?')
    process.exit(1)
  }
  // Get the directory
  const projectDir = path.dirname(pkgPath)

  // Read asconfig.json
  const asconfig = JSON.parse(fs.readFileSync(path.join(projectDir, 'asconfig.json'), 'utf8'))
  if (!asconfig.targets[args[0]]) {
    console.error(`Could not find target ${args[0]} in asconfig.json`)
    process.exit(1)
  }
  let outDir
  // If the output directory is not specified, use the one from asconfig.json
  if (args.length < 2) {
    outDir = asconfig.targets[args[0]].asCBind.outDir
  } else {
    outDir = args[1]
  }

  const execPath = await python.setup()
  const pyProcess = execFile(execPath, [path.join(__dirname, '..', 'py-src', 'as_to_c.py'), projectDir, args[0], outDir, ...args.slice(2)])
  // Pipe stdout and stderr
  pyProcess.stdout.pipe(process.stdout)
  pyProcess.stderr.pipe(process.stderr)
}

if (require.main === module) {
  const args = process.argv.slice(2)
  switch (args[0]) {
    case "add":
      add(args.slice(1))
      break
    case "init":
      init(args.slice(1))
      break
    case "build":
      build(args.slice(1))
      break
    default:
      console.error(`Unknown subcommand: ${args[0]}`)
      console.error('Available subcommands: add, init, build')
      process.exit(1)
  }
}
