import clang.cindex

def decodeName(name):
  result = ''
  name_iter = iter(name)
  for c in name_iter:
    if c == 'X':
      hex = next(name_iter) + next(name_iter)
      result += chr(int(hex, 16))
    else:
      result += c
  return result

def encodeName(name):
  result = ''
  for c in name:
    if c.isalpha() or c.isdigit():
      result += c
    else:
      result += f'X{hex(ord(c))[2:].upper()}'
  return result

def isInt(type):
  type = type.get_canonical()
  # print(type.kind)
  return type.kind in [clang.cindex.TypeKind.INT, clang.cindex.TypeKind.UINT,
                       clang.cindex.TypeKind.CHAR_S, clang.cindex.TypeKind.SCHAR, clang.cindex.TypeKind.UCHAR,
                       clang.cindex.TypeKind.SHORT, clang.cindex.TypeKind.USHORT,
                       clang.cindex.TypeKind.LONG, clang.cindex.TypeKind.ULONG,
                       clang.cindex.TypeKind.LONGLONG, clang.cindex.TypeKind.ULONGLONG]

def isSigned(type):
  type = type.get_canonical()
  return type.kind in [clang.cindex.TypeKind.INT, clang.cindex.TypeKind.CHAR_S, clang.cindex.TypeKind.SCHAR, clang.cindex.TypeKind.SHORT, clang.cindex.TypeKind.LONG, clang.cindex.TypeKind.LONGLONG]

def isFloat(type):
  type = type.get_canonical()
  return type.kind in [clang.cindex.TypeKind.FLOAT, clang.cindex.TypeKind.DOUBLE, clang.cindex.TypeKind.LONGDOUBLE]

def isArray(type):
  type = type.get_canonical()
  return type.kind in [clang.cindex.TypeKind.CONSTANTARRAY, clang.cindex.TypeKind.INCOMPLETEARRAY, clang.cindex.TypeKind.VARIABLEARRAY, clang.cindex.TypeKind.DEPENDENTSIZEDARRAY]

def typeToTS(type, fallback=None, acceptNonPrimitives=True, tsFile = False, visibleWrapper = True):
  type = type.get_canonical()
  size = type.get_size()
  # print(type.kind)
  if type.kind == clang.cindex.TypeKind.VOID:
    return "void"
  elif (type.kind == clang.cindex.TypeKind.POINTER or isArray(type)) and acceptNonPrimitives:
    # TODO: Pointers to pointers, pointers to structs...
    # return f"cPtr<{typeToTS(type.get_pointee(), fallback='void', acceptNonPrimitives=False)}> | null"
    if tsFile:
      return f"cPtrLike"
    else:
      return "cPtr | null" if visibleWrapper else "u64"
  elif isInt(type):
    return f"i{size * 8}" if isSigned(type) else f"u{size * 8}"
  elif isFloat(type):
    # TODO?
    if size > 8:
      return "f64"
    return f"f{size * 8}"
  else:
    if fallback is not None:
      return fallback
    raise Exception(f"Unsupported type: {type.spelling}")

# Converts a C type to the type it will end up being passed to the C code as (after being converted to a TypeScript type and back)
def typeToWrapper(type):
  type = type.get_canonical()
  size = type.get_size()
  # print(type.kind)
  if type.kind == clang.cindex.TypeKind.VOID:
    return "void"
  elif type.kind == clang.cindex.TypeKind.POINTER or isArray(type):
    # Pointer turns into a cPtr<T>, which is passed to C code as a pointer to WebAssembly memory
    # WebAssembly pointers are represented as U32
    # (if I use the value type trick it's still a U32, but it's not a pointer to WebAssembly memory)
    # return "U32"

    # We now represent this as an unboxed U64 and wrap it in the AssemblyScript glue code
    # TODO: Adjust for different pointer sizes (e.g. 32-bit)
    return "U64"
  elif isInt(type):
    # WebAssembly doesn't have signed/unsigned or ints smaller than 32 bits so it's always U32 or U64
    return "U32" if size * 8 <= 32 else "U64"
  elif type.kind == clang.cindex.TypeKind.FLOAT:
    return "F32"
  elif type.kind == clang.cindex.TypeKind.DOUBLE:
    return "F64"
  elif type.kind == clang.cindex.TypeKind.LONGDOUBLE:
    # TODO?
    return "F64"
  else:
    raise Exception(f"Unsupported type: {type.spelling}")

reservedWords = [
  "abstract", "any", "as", "as", "as", "async", "await", "boolean", "break", "continue", "class", "const", "const", "configurable", "constructor", "debugger", "declare", "default", "default", "delete", "do", "while", "enum", "enumerable", "export", "extends", "false", "for", "for", "in", "for", "of", "from", "function", "get", "get", "if", "else", "implements", "import", "import", "instanceof", "interface", "is", "let", "module", "namespace", "never", "new", "new", "null", "null", "number", "private", "protected", "public", "readonly", "require", "return", "set", "set", "static", "string", "super", "switch", "case", "symbol", "this", "this", "this", "this", "true", "try", "catch", "finally", "type", "typeof", "typeof", "undefined", "undefined", "value", "var", "void", "void", "while", "writable", "yield"
]

def ensureArgName(name, i):
  if name is None or name == '':
    return f"arg{i}"
  if name in reservedWords:
    return f"__{name}"
  return name

def hasStruct(function):
  for i, arg in enumerate(function.get_arguments()):
    if arg.type.get_canonical().kind == clang.cindex.TypeKind.RECORD:
      # Struct - not yet supported, skip for now
      # print(f"Function {function.spelling} has struct argument {arg.spelling} - skipping")
      return True

  if function.type.get_result().get_canonical().kind == clang.cindex.TypeKind.RECORD:
    # Struct - not yet supported, skip for now
    # print(f"Function {child.spelling} has struct return value - skipping")
    return True
  return False

# Generates a letter (or multiple letters) for a given number
# e.g. 1 -> "A", 2 -> "B", 3 -> "C", 26 -> "Z", 27 -> "AA", 28 -> "AB"
def numToLetters(num):
  result = ''
  while num > 0:
    num -= 1
    result += chr(ord('A') + num % 26)
    num //= 26
  return result[::-1]
