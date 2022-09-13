from utils import *
import sys
import os
import json
import shutil

# Get the path from the command line
if len(sys.argv) != 2:
  # print("Usage: gen-header.py <path to C header> <path to AssemblyScript project>")
  print("Usage: gen-header.py <path to project package.json>")
  exit(1)

# headerPath = sys.argv[1]
# projectPath = sys.argv[2]
packageJsonPath = sys.argv[1] 
projectPath = os.path.dirname(packageJsonPath)
print("projectPath: " + projectPath)

# Read the package.json file
with open(packageJsonPath) as f:
  packageJson = json.load(f)

# Loop over the header files
for header in packageJson["asCBind"]["headers"]:
  headerPath = None
  # Check if it exists
  if os.path.exists(header):
    headerPath = header
  else:
    # Check if it exists in the include path
    for includePath in packageJson["asCBind"]["includePath"]:
      fullPath = os.path.join(includePath, header)
      if os.path.exists(fullPath):
        headerPath = fullPath
        break
  if not headerPath:
    raise Exception("Could not find header file: " + header)

  index = clang.cindex.Index.create()
  tu = index.parse(headerPath, options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)

  asFile = """
  import { cPtr, convertToAddr, freeConverted, createCPtr } from 'as-c-bind/assembly'
  """.strip() + "\n"

  # tsFile = """
  # import { cPtr, convertToAddr, freeConverted } from 'as-c-bind/assembly'
  # type cPtrLike = cPtr | null | string | number | number[]
  # """.strip() + "\n"

  headerDefines = {}
  for child in tu.cursor.get_children():
    if child.kind != clang.cindex.CursorKind.MACRO_DEFINITION:
      continue

    # Check if they are actually in the file
    if child.location.file is None:
      continue
    # print(child.location.file)

    tokens = list(child.get_tokens())
    if len(tokens) != 2:
      continue

    if tokens[0].kind != clang.cindex.TokenKind.IDENTIFIER or tokens[0].spelling != child.spelling:
      continue

    if tokens[1].kind != clang.cindex.TokenKind.LITERAL:
      continue

    if child.spelling.startswith("_"):
      # Probably for internal use or a compiler define, skip
      continue

    value = tokens[1].spelling
    # If it ends with letters, remove them
    # TODO: Handle types and everything properly
    value = value.rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    headerDefines[child.spelling] = f"export const {child.spelling} = {value}"

  # Add the header defines to the ts file
  asFile += "\n".join(headerDefines.values()) + "\n"

  declared = []
  for child in tu.cursor.get_children():
    # print(child.kind)
    # TODO: callbacks
    if child.kind == clang.cindex.CursorKind.FUNCTION_DECL and child.type.kind == clang.cindex.TypeKind.FUNCTIONPROTO:
      # print("Found function: " + child.spelling)
      if child.spelling in declared:
        # Repeated declaration, like in stdlib.h - skip
        print(f"Function {child.spelling} has repeated declaration - skipping")
        continue

      if hasStruct(child):
        # Struct - not yet supported, skip for now
        print(f"Function {child.spelling} has struct - skipping")
        continue

      declared.append(child.spelling)
      as_declaration = f"declare function {child.spelling}_internal("
      # ts_declaration = f"export declare function {child.spelling}("

      has_args = False
      for i, arg in enumerate(child.get_arguments()):
        has_args = True
        as_declaration += f"{ensureArgName(arg.spelling, i)}: {typeToTS(arg.type, visibleWrapper=False)}, "
        # ts_declaration += f"{ensureArgName(arg.spelling, i)}: {typeToTS(arg.type, tsFile=True)}, "

      if has_args:
        as_declaration = as_declaration[:-2]
        # ts_declaration = ts_declaration[:-2]

      as_declaration += f"): {typeToTS(child.type.get_result(), visibleWrapper=False)}\n"
      # ts_declaration += f"): {typeToTS(child.type.get_result(), tsFile=True)}\n"

      # Now add a wrapper using generics (no unions in AS) to take multiple types
      as_declaration += f"export function {child.spelling}"
      as_declaration += "<"
      for i, arg in enumerate(child.get_arguments()):
        if arg.type.get_canonical().kind == clang.cindex.TypeKind.POINTER:
          as_declaration += f"{numToLetters(i + 1)}, "
      if as_declaration.endswith(", "):
        as_declaration = as_declaration[:-2]
        as_declaration += ">"
      else:
        as_declaration = as_declaration[:-1]

      as_declaration += "("
      has_args = False
      for i, arg in enumerate(child.get_arguments()):
        has_args = True
        as_declaration += f"{ensureArgName(arg.spelling, i)}: "
        if arg.type.get_canonical().kind == clang.cindex.TypeKind.POINTER:
          as_declaration += numToLetters(i + 1)
        else:
          as_declaration += typeToTS(arg.type)
        as_declaration += ", "

      if has_args:
        as_declaration = as_declaration[:-2]
      as_declaration += ")"

      as_declaration += f": {typeToTS(child.type.get_result())} {{\n"

      for i, arg in enumerate(child.get_arguments()):
        if arg.type.get_canonical().kind == clang.cindex.TypeKind.POINTER:
          argname = ensureArgName(arg.spelling, i)
          as_declaration += f"  let {argname}_conv = convertToAddr({argname})\n"
      
      # Call the _internal function
      as_declaration += "  " if child.type.get_result().kind == clang.cindex.TypeKind.VOID else "  let _func_call_result = "
      as_declaration += f"{child.spelling}_internal("
      for i, arg in enumerate(child.get_arguments()):
        as_declaration += ensureArgName(arg.spelling, i)
        if arg.type.get_canonical().kind == clang.cindex.TypeKind.POINTER:
          as_declaration += "_conv"
        as_declaration += ", "
      if has_args:
        as_declaration = as_declaration[:-2]
      as_declaration += ")\n"

      # Free the converted arguments if necessary
      for i, arg in enumerate(child.get_arguments()):
        if arg.type.get_canonical().kind == clang.cindex.TypeKind.POINTER:
          argname = ensureArgName(arg.spelling, i)
          as_declaration += f"  freeConverted({argname}, {argname}_conv)\n"

      if child.type.get_canonical().get_result().kind != clang.cindex.TypeKind.VOID:
        # If it's a pointer, convert it to a cPtr object
        if child.type.get_result().get_canonical().kind == clang.cindex.TypeKind.POINTER:
          as_declaration += f"  return createCPtr(_func_call_result)\n"
        else:
          as_declaration += "  return _func_call_result\n"
      as_declaration += "}\n"

      asFile += as_declaration
      # tsFile += ts_declaration
    # elif child.kind == clang.cindex.CursorKind.STRUCT_DECL:
    #   for field in child.get_children():
    #     print("-", field.kind, field.spelling, field.type.kind)


  # Create <project path>/headers/<header name>/ (remove it if it already exists)
  folderPath = os.path.join(projectPath, "headers", os.path.basename(headerPath))
  if os.path.exists(folderPath):
    shutil.rmtree(folderPath)
  os.makedirs(folderPath)

  # Write the AS file to as.ts
  # with open(os.path.join(folderPath, "as.ts"), "w") as f:
  with open(os.path.join(folderPath, "index.ts"), "w") as f:
    f.write(asFile)

  # Write the TS file to index.ts
  # with open(os.path.join(folderPath, "index.ts"), "w") as f:
  #   f.write(tsFile)

  # Create a package.json file in the header folder
  with open(os.path.join(folderPath, "package.json"), "w") as f:
    f.write(json.dumps({
      "ascMain": "index.ts",
    }, indent=2))

  # Create a meta.json file in the header folder
  with open(os.path.join(folderPath, "meta.json"), "w") as f:
    f.write(json.dumps({
      "origPath": os.path.abspath(headerPath)
    }, indent=2))
