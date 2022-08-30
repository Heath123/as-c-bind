#!/usr/bin/env node

const fs = require('fs')
const path = require('path')
const python = require('./py')
// const util = require('util')
// const execFile = util.promisify(require('child_process').execFile)
const execFile = require('child_process').execFile
let pkgUp

async function readPackageJson () {
  if (!pkgUp) {
    pkgUp = (await import('pkg-up')).pkgUp
  }

  const path = await pkgUp()
  if (!path) {
    throw new Error('Could not find package.json')
  }
  const content = fs.readFileSync(path, 'utf8')
  return {
    path: path,
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
    pyProcess.exit(1)
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

if (require.main === module) {
  const args = process.argv.slice(2)
  switch (args[0]) {
    case "add":
      add(args.slice(1))
      break
    default:
      console.error(`Unknown subcommand: ${args[0]}`)
      process.exit(1)
  }
}
