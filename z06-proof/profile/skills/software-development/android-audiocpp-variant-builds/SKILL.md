---
name: android-audiocpp-variant-builds
description: "Use when cross-building audio.cpp Android backend variants."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [android, audiocpp, ndk, opencl, vulkan]
    related_skills: [oss-checkout-install, fleet-owner-ssh-parity]
---

# audio.cpp Android variant builds

## When to Use

Use for isolated audio.cpp Android arm64 CPU, OpenMP, KleidiAI, Vulkan, OpenCL or
ThinLTO builds and their provenance/ELF qualification.

## Scope

Cross-build isolated arm64 audio.cpp experiments without touching a phone or the
existing baseline. Follow the task's compute admission and Git branch boundaries.

## Procedure

1. Pin and verify audio.cpp HEAD and clean tracked sources. Read its top-level
   CMakeLists and the vendored ggml backend CMake files before selecting options;
   wrapper ENGINE options do not cover all GGML options.
2. Prefer the owner-authorized fleet node. Read `fleet-build --help`, test admission
   with a tiny explicit-node command, and check remote disk capacity before staging
   the NDK. SSH into fish hosts using a quoted `bash -c` body. Do not weaken held
   queues, delete unrelated data, or change HOME to make offload work.
3. Use a different `build/android-<variant>` directory per variant. Never mutate the
   baseline build or source files in place. If fallback is authorized, use the exact
   shared `flock ... nice -n 19 cmake --build ... -j6` boundary; wait for another lock
   owner instead of bypassing it.
4. Set `ANDROID_STL=c++_static`, Android ABI/API, `ENGINE_ENABLE_NATIVE_CPU=OFF`, and
   an explicit device-supported `GGML_CPU_ARM_ARCH`. Snapdragon Oryon v2 lacks SVE,
   SVE2 and SME; do not inherit a host-native ISA.
5. Set both `ENGINE_ENABLE_OPENMP` and `GGML_OPENMP` explicitly. For static OpenMP,
   set FindOpenMP C/CXX flags to `-fopenmp -static-openmp`, library names to `omp`,
   `OpenMP_omp_LIBRARY` to the NDK AArch64 libomp.a, and static OpenMP at final link.
6. Let supported ggml KleidiAI FetchContent fetch its version/hash-pinned archive.
   Confirm NEON dotprod/i8mm rather than SVE/SME kernels are selected.
7. For Vulkan, provide pinned Khronos Vulkan-Headers (including C++ vulkan.hpp),
   the API-specific NDK libvulkan.so stub, and the NDK host `shader-tools/.../glslc`.
   Also pin Khronos SPIRV-Headers and add its include directory: a01aed4's Vulkan
   backend includes `spirv/unified1/spirv.hpp`, which the NDK does not supply. Supplying
   Vulkan-Headers alone passes configuration but fails that backend object compile.
   The shader generator needs host compilers. Record glslc version and unsupported
   feature probes; old NDK glslc can disable cooperative matrices, integer-dot, and
   BF16 even when C++ headers are current.
8. For Adreno OpenCL, pass `GGML_OPENCL=ON`,
   `GGML_OPENCL_USE_ADRENO_KERNELS=ON`, and embed kernels. Build a pinned real Khronos
   OpenCL ICD loader STATIC against pinned OpenCL-Headers. Pass its libOpenCL.a and
   header directory through CMake FindOpenCL; do not ship fake implementation stubs.
   Set runtime `OCL_ICD_FILENAMES=/vendor/lib64/libOpenCL.so` (not OPENCL_ICD_FILENAMES).
   Vendor dlopen access/namespace and ICD compatibility remain device-test gates.
9. Check audio.cpp's CLI parser separately from backend compilation. The a01aed4
   parser has no `--backend opencl`, but `--backend best` calls
   ggml_backend_init_best and can select OpenCL. Require device output proving GPU
   selection; successful exit can also be CPU fallback.
10. Copy large artifacts using Python shutil.copy2; strip with the NDK llvm-strip.
    Check `file` for stripped AArch64 ELF and `llvm-readelf -d` for Android-stock
    DT_NEEDED. Reject unbundled libc++_shared.so/libomp.so/libOpenCL.so.
11. Write BUILD.json for success AND failure, with exact commands, flags, dependency
    pins, compiler versions, elapsed time, host, hashes/sizes, NEEDED, and explicit
    device-test status. Remove stale destination executables after failed reruns.
12. Exercise the real build script and lightweight admission/failure behavior tests,
    run bash -n, aggregate the exact requested variant count, and verify the pushed
    branch using a remote read. Cross-link proof is not on-device inference proof.

## Build reuse

Optional ccache helps full-model builds. Record the ccache version and environment.
Use a source-relative CCACHE_BASEDIR and disabled cwd hashing only when stripped
artifacts make cross-build-directory debug path reuse acceptable. Compiler options
must remain cache-key inputs; never copy incompatible objects to claim a build.
