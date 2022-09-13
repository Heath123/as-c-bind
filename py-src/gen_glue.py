from utils import *

def genGlueStart():
  return """#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "w2c2_base.h"

extern wasmMemory *e_memory;

// We now have it unboxed on the C side and box/unbox it in AS code, so these are no-ops
// TODO: Avoid generating them entirely

// #define convPtr(offset) (void*) i64_load(e_memory, offset)
// extern U32 (*e_createCVoidPtr)(U64);
// #define convPtrBack(ptr) e_createCVoidPtr((U64) ptr)

#define convPtr(offset) (void*) offset
#define convPtrBack(ptr) (U64) ptr

extern void init();

void printStr(U32 offset) {
  // Print the string
  // Ignore every other byte, as this is UTF-16
  // This is a hack, but it's good enough for now

  // The length is half of rtSize
  int length = i32_load(e_memory, offset - 4) / 2;
  for (int i = 0; i < length; i++) {
    // Load and print the character at the address
    // We multiply i by 2 as we are skipping every other byte
    printf("%c", i32_load(e_memory, offset + i * 2));
  }
}

void f_env_abort_impl(U32 message, U32 filename, U32 line, U32 col) {
  printStr(filename);
  printf(":%d:%d: ", line, col);
  printStr(message);
  printf("\\n");
  exit(1);
}
void (*f_env_abort)(U32, U32, U32, U32) = &f_env_abort_impl;

void trap(Trap trap) {
  exit(1);
}

// Set memory

void f_index_setMemory8_impl(U64 ptr, U32 value) {
  memcpy((void*) ptr, &value, 1);
}
void (*f_index_setMemory8)(U64, U32) = &f_index_setMemory8_impl;

void f_index_setMemory16_impl(U64 ptr, U32 value) {
  memcpy((void*) ptr, &value, 2);
}
void (*f_index_setMemory16)(U64, U32) = &f_index_setMemory16_impl;

void f_index_setMemory32_impl(U64 ptr, U32 value) {
  memcpy((void*) ptr, &value, 4);
}
void (*f_index_setMemory32)(U64, U32) = &f_index_setMemory32_impl;

void f_index_setMemory64_impl(U64 ptr, U64 value) {
  memcpy((void*) ptr, &value, 8);
}
void (*f_index_setMemory64)(U64, U64) = &f_index_setMemory64_impl;

// Get memory

U32 f_index_getMemory8_impl(U64 ptr) {
  U32 value;
  memcpy(&value, (void*) ptr, 1);
  return value;
}
U32 (*f_index_getMemory8)(U64) = &f_index_getMemory8_impl;

U32 f_index_getMemory16_impl(U64 ptr) {
  U32 value;
  memcpy(&value, (void*) ptr, 2);
  return value;
}
U32 (*f_index_getMemory16)(U64) = &f_index_getMemory16_impl;

U32 f_index_getMemory32_impl(U64 ptr) {
  U32 value;
  memcpy(&value, (void*) ptr, 4);
  return value;
}
U32 (*f_index_getMemory32)(U64) = &f_index_getMemory32_impl;

U64 f_index_getMemory64_impl(U64 ptr) {
  U64 value;
  memcpy(&value, (void*) ptr, 8);
  return value;
}
U64 (*f_index_getMemory64)(U64) = &f_index_getMemory64_impl;

// Get the address of a value in WASM memory
// TODO: Fix the fact that this might not work if the memory is realloced

U64 f_index_getAddr_impl(U32 offset) {
  return (U64) &e_memory->data[offset];
}
U64 (*f_index_getAddr)(U32) = &f_index_getAddr_impl;

// Memory allocation and deallocation

U32 f_index_asCBindMalloc_impl(U32 size) {
  return convPtrBack(malloc(size));
}
U32 (*f_index_asCBindMalloc)(U32) = &f_index_asCBindMalloc_impl;

void f_index_asCBindFree_impl(U64 ptr) {
  free(convPtr(ptr));
}
void (*f_index_asCBindFree)(U32) = &f_index_asCBindFree_impl;

// Generated glue code

"""

def genGlue(tu):
  # functionAssignments = "f_env_abort = f_env_abort_impl;\n  f_index_setMemory8 = f_index_setMemory8_impl;\n"
  cGlue = ""

  declared = []
  for child in tu.cursor.get_children():
    if child.kind == clang.cindex.CursorKind.FUNCTION_DECL:
      if child.spelling in declared:
        # Repeated declaration, like in stdlib.h - skip
        print(f"Function {child.spelling} has repeated declaration - skipping")
        continue

      if hasStruct(child):
        # Struct - not yet supported, skip for now
        print(f"Function {child.spelling} has struct - skipping")
        continue

      declared.append(child.spelling)
      name = f"f_{encodeName('index')}_{encodeName(child.spelling + '_internal')}"
      argsList = ""
      for i, arg in enumerate(child.get_arguments()):
        if i > 0:
          argsList += ", "
        argsList += f"{typeToWrapper(arg.type)} {ensureArgName(arg.spelling, i)}"

      cGlue += f"{typeToWrapper(child.type.get_result())} {name}_impl({argsList}) {{\n"

      # Call the underlying function
      # TODO: Clean up this mess
      cGlue += "  return " if child.type.get_result().get_canonical().kind != clang.cindex.TypeKind.VOID else "  "
      if child.type.get_result().get_canonical().kind == clang.cindex.TypeKind.POINTER:
        cGlue += "convPtrBack("
      
      # cGlue += f"{child.spelling}({', '.join([f'convPtr({ensureArgName(arg.spelling)})' if arg.type.get_canonical().kind == clang.cindex.TypeKind.POINTER else ensureArgName(arg.spelling) for arg in child.get_arguments()])})" # + arg['suffix']
      cGlue += f"{child.spelling}("
      for i, arg in enumerate(child.get_arguments()):
        if i > 0:
          cGlue += ", "
        argname = ensureArgName(arg.spelling, i)
        if arg.type.get_canonical().kind == clang.cindex.TypeKind.POINTER:
          cGlue += f"convPtr({argname})"
        else:
          cGlue += argname
          
      if child.type.get_result().get_canonical().kind == clang.cindex.TypeKind.POINTER:
        # Close convPtrBack invocation
        cGlue += ")"
      cGlue += ");\n"
      cGlue += "}\n"

      cGlue += f"{typeToWrapper(child.type.get_result())} (*{name})({argsList}) = &{name}_impl;\n\n"

  return cGlue

def genGlueEnd():
  return f"""
int main() {{
  init();
  return 0;
}}"""
