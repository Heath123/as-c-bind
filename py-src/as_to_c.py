from utils import *
from gen_glue import *

import sys
import os
import subprocess
import shutil
import json

# Get the path from the command line
if len(sys.argv) != 3:
  print("Usage: as-to-c.py <path to AssemblyScript project> <path to output directory>")
  exit(1)

path = sys.argv[1]

# # Delete the temp folder if it exists
# if os.path.exists("temp"):
#   shutil.rmtree("temp")

# # Create a new temp folder
# os.mkdir("temp")

# Save the current working directory
cwd = os.getcwd()

# chdir to the AssemblyScript project
os.chdir(path)

# Run npm run asbuild:debug
asc = subprocess.run(["npm", "run", "asbuild:debug"])
if asc.returncode != 0:
  raise Exception("Failed to build AssemblyScript project")

# Run w2c2 on build/debug.wasm and capture the stdout (stderr goes to the console)
w2c2 = subprocess.run(["/home/heath/w2c2/w2c2", "build/debug.wasm"], stdout=subprocess.PIPE)

# Get the stdout
code = w2c2.stdout.decode("utf-8")

# chdir back to the original working directory
os.chdir(cwd)

# chdir to the target directory
os.chdir(sys.argv[2])

# Write the code to compiled.c
with open("compiled.c", "w") as f:
  f.write(code)

glue = genGlueStart()

# Loop over the directories in path/headers with os.listdir
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
