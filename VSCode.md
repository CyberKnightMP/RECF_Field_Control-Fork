## Intellisense Completion

Use the following include paths for intellisense completion:

`${env:PROS_TOOLCHAIN}/arm-none-eabi/include`,

`${env:PROS_TOOLCHAIN}/lib/gcc/arm-none-eabi/6.3.1/include`,

`${workspaceRoot}`,

`${workspaceRoot}/include`

Add "_INTELLISENSE" to your defines to fix certain intellisense errors that will actually compile without issue

## VS Code setup

Install the PROS extension (`sigbots.pros`) and the Microsoft C/C++ extension. The workspace C/C++ configuration is in `.vscode/c_cpp_properties.json`; it uses the PROS ARM GCC compiler, Cortex-A9 V5 target flags, repository headers, and the `_INTELLISENSE` define.

The compiler path assumes the PROS extension's default Windows install under `%APPDATA%`. If you installed the toolchain elsewhere, update `compilerPath` in that file to the corresponding `arm-none-eabi-gcc` executable.

The full PROS kernel build also requires the `firmware/libv5rts` submodule. Initialize it with:

```sh
git submodule update --init --recursive
```