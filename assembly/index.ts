export declare function setMemory8(ptr: u64, value: u8): void
export declare function setMemory16(ptr: u64, value: u16): void
export declare function setMemory32(ptr: u64, value: u32): void
export declare function setMemory64(ptr: u64, value: u64): void

export declare function getMemory8(ptr: u64): u8
export declare function getMemory16(ptr: u64): u16
export declare function getMemory32(ptr: u64): u32
export declare function getMemory64(ptr: u64): u64

declare function getAddr(obj: usize): u64;

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

declare function asCBindMalloc(__size: i32): u64;
declare function asCBindFree(__ptr: u64): void;

function stringToPtr(str: string): /*cPtr<i8>*/ u64 {
  let ptr = asCBindMalloc(str.length + 1)
  for (let i = 0; i < str.length; i++) {
    // ptr[i] = i8(str.charCodeAt(i))
    setMemory8(ptr + i, i8(str.charCodeAt(i)))
  }
  // ptr[str.length] = 0
  setMemory8(ptr + str.length, 0)
  return ptr
}

// @ts-ignore (inline decorator isn't valid in TS)
@inline
export function convertToAddr<T>(obj: T): u64 {
  if (obj === null) {
    return 0
  } if (obj instanceof cPtr) {
    return obj.address
  } else if (isString(obj)) {
    return stringToPtr(obj.toString())
  } else if (isInteger(obj)) {
    return i64(obj)
  } else if (isArray(obj) /*&& isInteger(obj[0])*/) {
    let val = unchecked(obj[0]);
    if (isInteger(val)) return getAddr(obj.dataStart) // non-standard property
    ERROR("Arrays passed as a point mst be an array of integers")
    // return convertArrayToPtr(obj)
  } else {
    ERROR('Unsupported type for pointer. The following types are supported: cPtr, integer, string, array of integers')
    return 0 // Unreachable but sometimes it complains without it
  }
}

// @ts-ignore (inline decorator isn't valid in TS)
@inline
export function freeConverted<T>(obj: T, ptr: u64): void {
  // Only some types need auto-freeing (only the types where memory was allocated by copying)
  if (isString(obj)) {
    asCBindFree(ptr)
  }
}

export function createCPtr(ptr: u64): cPtr | null {
  return ptr === 0 ? null : new cPtr(ptr)
}
