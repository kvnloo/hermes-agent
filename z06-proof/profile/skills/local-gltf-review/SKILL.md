---
name: local-gltf-review
description: Use when building a local-only Three.js GLB review tool.
---

# Local GLB review without premature visual claims

- Separate viewer readiness from actual-asset acceptance. Keep the public GLB absent and display `asset-needed` until the real export arrives; never promote a unit fixture to the review asset.
- Reuse an installed Three.js package read-only. Copy it into the owned workspace and use `npm pack --ignore-scripts --offline` to make a local tarball dependency. Installing a local package directory may cause npm to resolve its development dependencies; a packed tarball avoids that. Verify a clean `npm ci --offline --ignore-scripts` against the lockfile.
- Use a small static build with an import map when no bundler is needed. Copy the Three.js build and required addon dependencies locally; never depend on a CDN for private models.
- Attach an export through an explicit version label and computed SHA-256 manifest. Verify the GLB header, byte length, glTF version, mesh presence and self-contained resources before publishing it into the viewer's public directory. Verify the SHA again before browser parsing to catch stale manifest/model pairs.
- Keep standard Blender glTF Y-up conversion; do not apply a second Z-up rotation. Frame the actual geometry bounds with the smaller horizontal/vertical field of view so portrait viewports do not clip the model.
- Exercise GLTFLoader and OrbitControls public APIs in CPU tests with an in-memory geometry fixture. Keep that fixture out of public/build output. Test missing files, malformed binaries, stale hashes, zoom/reset and bounds framing. Do not use source-string tests.
- Bind the review server to loopback, serve only the built artifact, reject write methods and use same-origin resource policy. Own test servers in `try/finally`; verify repeated runs exit cleanly.
- Respect renderer admission boundaries. CPU parsing, HTTP checks and camera math do not require launching a browser or initializing GPU. If those are reserved for a parent/operator, report visual acceptance as pending rather than bypassing the restriction.
- Distinguish material conversion from appearance parity. Procedural Blender shaders may not survive glTF export; neutral review illumination is not Blender lighting reproduction.
