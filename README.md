# as-c-bind
Use C headers from AssemblyScript

Note that this is currently in an early state and will have a lot of missing features, bugs and performance issues. It is also only tested on Linux.

## Dependencies

First, you need https://github.com/turbolent/w2c2 on your PATH:

```
$ git clone https://github.com/turbolent/w2c2
[output omitted]
$ cd w2c2
~/w2c2 $ make
[output omitted]
~/w2c2 $ sudo ln -s $PWD/w2c2 /usr/local/bin/w2c2
~/w2c2 $ cd ..
```

You also need the `libclang` Python module (and Python) installed:

```
$ python3 -m pip install libclang
```

## Usage:

```
$ mkdir helloworld
$ cd helloworld/
~/helloworld $ npm init -y
[output omitted]
~/helloworld $ npm i https://github.com/Heath123/as-c-bind/ assemblyscript
[output omitted]
~/helloworld $ npx as-c-bind init .
[output omitted]
~/helloworld $ echo "import { puts } from 'stdio.h'; puts('Hello, World!')" > assembly/index.ts
~/helloworld $ npx as-c-bind add stdio.h
stdio.h is already included - skipping
using Python version 3.8.10 found at "/usr/bin/python3"
projectPath: /home/heath/helloworld
Function fscanf has repeated declaration - skipping
Function scanf has repeated declaration - skipping
Function sscanf has repeated declaration - skipping
Function vfscanf has repeated declaration - skipping
Function vscanf has repeated declaration - skipping
Function vsscanf has repeated declaration - skipping
~/helloworld $ npx as-c-bind build debug
using Python version 3.8.10 found at "/usr/bin/python3"
w2c2: skipping custom section 'name' (size 3847)
w2c2: skipping custom section 'sourceMappingURL' (size 17)
Function fscanf has repeated declaration - skipping
Function scanf has repeated declaration - skipping
Function sscanf has repeated declaration - skipping
Function vfscanf has repeated declaration - skipping
Function vscanf has repeated declaration - skipping
Function vsscanf has repeated declaration - skipping
~/helloworld $ gcc build/debug-c/*.c -o helloworld
[output omitted]
~/helloworld $ ./helloworld
Hello, World!
~/helloworld $
```

## Tips

Set and get memory with the `[set/get]Memory[8/16/32/64]()` functions imported from `as-c-bind`. TO get the address of a pointer, access its `addr` property.

You can pass strings, integers (memeory addresses) or arrays of integers in place of pointers. Remember that AssemblyScript is garbage collected, so passing an array of integers will cause problems if the C code expects it to stay around after the call. Also string# are freed immediately after the call is done.

## Limitations

The following things are not yet supported and need to be added:

- Typed pointers (currently, all pointers are interchangable which is not safe)
- Structs/unions (all functions with structs as arguments or results are skipped, unless they are pointers)
- Enums (though simple numeric `#define` constants are supported)
- I haven't tested booleans yet
- Proper conversion of strings to UTF-8 rather than assuming everything is ASCII (shouldn't be too hard)
- Probably many more things I haven't thought of
