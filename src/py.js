const process = require('process')
const { execFile } = require('child_process')
const findPython = require('./find-python')

test = function test (found) {
// findPython(null, (err, found) => {
//   if (err != null) {
//     console.error(err)
//     process.exit(1)
//   }
  // python3 -c "import clang.cindex"
  return new Promise((resolve, reject) => {
    execFile(found, ['-c', 'import clang.cindex'], (err, stdout, stderr) => {
      if (err != null) {
        console.error(err)
        if (stderr.includes("ModuleNotFoundError")) {
          console.error("Clang Python bindings not found!")
          console.error("Please install the libclang Python module with:")
          console.error(`${found} -m pip install libclang`)
        }
        process.exit(1)
      }
      if (stderr.length > 0) {
        console.error(stderr)
        process.exit(1)
      }
      // console.log(stdout)
      resolve()
    })
  })
}

function findPythonAsync (found) {
  return new Promise((resolve, reject) => {
    findPython(null, (err, found) => {
      if (err != null) {
        console.error(err)
        process.exit(1)
      }
      resolve(found)
    })
  })
}

exports.setup = async function () {
  const found = await findPythonAsync()
  await test(found)
  return found
}
