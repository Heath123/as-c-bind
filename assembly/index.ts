export declare function setMemory8(ptr: u64, value: u8): void
export declare function setMemory16(ptr: u64, value: u16): void
export declare function setMemory32(ptr: u64, value: u32): void
export declare function setMemory64(ptr: u64, value: u64): void

export declare function getMemory8(ptr: u64): u8
export declare function getMemory16(ptr: u64): u16
export declare function getMemory32(ptr: u64): u32
export declare function getMemory64(ptr: u64): u64

declare function getAddr(obj: usize): u64;

/*
// @ts-ignore: decorator
@inline
function getMemory<T extends number>(ptr: u64): T {
  if (sizeof<T>() == 1) {
    return reinterpret<T>(getMemory8(ptr))
  } else if (sizeof<T>() == 2) {
    return reinterpret<T>(getMemory16(ptr))
  } else if (sizeof<T>() == 4) {
    return reinterpret<T>(getMemory32(ptr))
  } else {
    ERROR("Unsupported size - only 8, 16, and 32 bit types are supported")
  }
}

// @ts-ignore: decorator
@inline
function setMemory<T extends number>(ptr: u64, value: T): void {
  if (sizeof<T>() == 1) {
    setMemory8(ptr, u8(value))
  } else if (sizeof<T>() == 2) {
    setMemory16(ptr, u16(value))
  } else if (sizeof<T>() == 4) {
    setMemory32(ptr, u32(value))
  } else {
    ERROR("Unsupported size - only 8, 16, and 32 bit types are supported")
  }
}
*/

/*
export class cPtr<T> {
  constructor(ptr: u64) {
    this.address = ptr
  }
  cast<U>(): cPtr<U> {
    return new cPtr<U>(this.address)
  }
  [key: u64]: T
  @inline @operator("[]")
  private __get(index: u64): T {
    if (!isInteger<T>()) {
      ERROR("Unsupported type for pointer - only integer types are supported")
    }
    return getMemory
    // @ts-ignore
    <T>
    (this.address + (index * sizeof<T>()))
  }
  @inline @operator("[]=")
  private __set(index: u64, value: T): void {
    if (!isInteger<T>()) {
      ERROR("Unsupported type for pointer - only integer types are supported")
    }
    setMemory(this.address + (index * sizeof<T>()),
    // @ts-ignore
    value)
  }
  address: u64
}
*/

export class cPtr {
  constructor(ptr: u64) {
    this.address = ptr
  }
  // cast<U>(): cPtr<U> {
  //   return new cPtr<U>(this.address)
  // }
  address: u64
  static null: cPtr = new cPtr(0)
}

declare function asCBindMalloc(__size: i32): cPtr | null;
declare function asCBindFree(__ptr: cPtr | null): void;

function stringToPtr(str: string): /*cPtr<i8>*/ cPtr {
  let ptr = asCBindMalloc(str.length + 1)!
  for (let i = 0; i < str.length; i++) {
    // ptr[i] = i8(str.charCodeAt(i))
    setMemory8(ptr.address + i, i8(str.charCodeAt(i)))
  }
  // ptr[str.length] = 0
  setMemory8(ptr.address + str.length, 0)
  return ptr
}

// @ts-ignore (inline decorator isn't valid in TS)
@inline
export function convertArrayToPtr<T>(obj: T[]): cPtr | null {
  if (isInteger<T>()) {
    // dataStart, at offset 4, points to the actual data
    let dataStart = load<usize>(changetype<usize>(obj) + 4)
    return new cPtr(getAddr(dataStart))
  } else {
    ERROR("Only arrays of integer types can be passed as pointers")
    return null // unreachable
  }
}

// @ts-ignore (inline decorator isn't valid in TS)
@inline
export function convertToPtr<T>(obj: T): cPtr | null {
  if (obj instanceof cPtr) {
    return obj
  } else if (isString(obj)) {
    return stringToPtr(obj.toString())
  } else if (isInteger(obj)) {
    return new cPtr(obj)
  } else if (isArray(obj) /*&& isInteger(obj[0])*/) {
    return convertArrayToPtr(obj)
  } else {
    ERROR('Unsupported type for pointer. The following types are supported: cPtr, string, array of integers')
    return null // unreachable
  }
}

// @ts-ignore (inline decorator isn't valid in TS)
@inline
export function freeConverted<T>(obj: T, ptr: cPtr | null): void {
  // Only some types need auto-freeing (only the types where memory was allocated by copying)
  if (isString(obj)) {
    asCBindFree(ptr)
  }
}

