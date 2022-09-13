from utils import *
from gen_glue import *

import sys
import os
import subprocess
import shutil
import json

# Get the path from the command line
if len(sys.argv) < 4:
  print("Usage: as-to-c.py <path to AssemblyScript project> <target> <path to output directory> [asc args]")
  exit(1)

path = sys.argv[1]

# Check if w2c2 is on the path
if not shutil.which("w2c2"):
  print("w2c2 not found! Please make sure it is on your path.")
  exit(1)

# Load <path>/asconfig.json
with open(os.path.join(path, "asconfig.json")) as f:
  config = json.load(f)

if sys.argv[2] not in config["targets"]:
  print(f"Target {sys.argv[2]} not found in asconfig.json")
  exit(1)

filename = config["targets"][sys.argv[2]]["outFile"]

# # Delete the temp folder if it exists
# if os.path.exists("temp"):
#   shutil.rmtree("temp")

# # Create a new temp folder
# os.mkdir("temp")

# Save the current working directory
cwd = os.getcwd()

# chdir to the AssemblyScript project
os.chdir(path)

# Rename the file to [filename].old if it exists
if os.path.exists(filename):
  os.rename(filename, filename + ".old")

asc = subprocess.run(["npx", "asc", "assembly/index.ts", "--target", sys.argv[2], "--disable", "bulk-memory"] + sys.argv[4:])
if asc.returncode != 0:
  # Put the .old file back if it exists
  if os.path.exists(filename + ".old"):
    os.rename(filename + ".old", filename)
  print("Failed to build AssemblyScript project")
  exit(1)

# Check if the file exists
if not os.path.exists(filename):
  # Project not built
  # Put the .old file back if it exists
  os.rename(filename + ".old", filename)
  print("Project was not built")
  sys.exit(1)
else:
  # Project built
  # Delete the .old file if it exists
  if os.path.exists(filename + ".old"):
    os.remove(filename + ".old")

# Run w2c2 on build/debug.wasm and capture the stdout (stderr goes to the console)
w2c2 = subprocess.run(["w2c2", filename], stdout=subprocess.PIPE)
if w2c2.returncode != 0:
  print("Failed to run w2c2")
  exit(1)

# Get the stdout
code = w2c2.stdout.decode("utf-8")

# chdir back to the original working directory
os.chdir(cwd)

# chdir to the target directory
os.chdir(sys.argv[3])

# Write the code to compiled.c
with open("compiled.c", "w") as f:
  f.write(code)

glue = ""

# Read the package.json file
with open(os.path.join(path, "package.json")) as f:
  packageJson = json.load(f)

if not "asCBind" in packageJson:
  packageJson["asCBind"] = {}
if not "headers" in packageJson["asCBind"]:
  packageJson["asCBind"]["headers"] = []

# Loop over the header files
for header in packageJson["asCBind"]["headers"]:
  glue += f"#include \"{header}\"\n"

glue += genGlueStart()

# Loop over the directories in path/headers with os.listdir
if os.path.exists(os.path.join(cwd, path, "headers")):
  for directory in os.listdir(os.path.join(cwd, path, "headers")):

    # Check if the directory is a directory
    if not os.path.isdir(os.path.join(cwd, path, "headers", directory)):
      continue

    # Read meta.json from the directory
    with open(os.path.join(cwd, path, "headers", directory, "meta.json")) as f:
      meta = json.load(f)
    
    index = clang.cindex.Index.create()
    tu = index.parse(meta["origPath"])
    glue += genGlue(tu)

glue += genGlueEnd()

# Write the glue to glue.c
with open("glue.c", "w") as f:
  f.write(glue)

# Copy ../w2c2_base.h, relative to the path of the current script, to the target directory
# Also allow overriding the path to w2c2_base.h in package.json
if "w2c2BasePath" in packageJson["asCBind"]:
  w2c2BasePath = packageJson["asCBind"]["w2c2BasePath"]
  # Make sure it's relative to the project folder
  if not os.path.isabs(w2c2BasePath):
    w2c2BasePath = os.path.join(path, w2c2BasePath)
else:
  w2c2BasePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "w2c2_base.h")

shutil.copy(w2c2BasePath, "w2c2_base.h")
