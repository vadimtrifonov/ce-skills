# Starfield NIF Inspection

## Geometry

`BSGeometry` can embed geometry or reference external `.mesh` files.
Load external geometry from an extracted Data-like directory:

```bash
mise exec -- python scripts/inspect_nif.py "<model.nif>" \
  --geometry --data-root "<extracted-Data>" -o "<report.json>"
```

`geometry.mesh_paths` lists external paths in LOD order; `dependencies.meshes` includes their loose-file checks.
`--geometry` reads LOD 0 by default; add `--lod 1`, `2`, or `3` to select another slot.
An absent slot is reported as unavailable, not replaced with LOD 0.

Vertex and triangle counts remain `null` until geometry is loaded.
Bounds remove PyNifly V28.3.0's [69.969 vertex scale](https://github.com/BadDogSkyrim/PyNifly/blob/V28.3.0/NiflyDLL/NiflyWrapper.cpp#L7130-L7137) so they use the same coordinates as the NIF transform translations.

## Materials and collision

Shader reports include `.mat` paths, but do not decode material resources or enumerate their textures.
A failed loose-file check does not establish that a material is absent from archives or a CDB.
Collision reports identify the physics-system block and body index; Havok payloads are not decoded.
