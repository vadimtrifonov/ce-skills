import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect_nif.py"
_SPEC = importlib.util.spec_from_file_location("inspect_nif", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def shape(starfield=False, internal=False):
    scale = _MODULE.BSGEOMETRY_SCALE if starfield else 1.0
    return SimpleNamespace(
        blockname="BSGeometry" if starfield else "BSTriShape",
        properties=SimpleNamespace(
            vertexCount=0 if starfield else 3,
            triangleCount=0 if starfield else 1,
            hasVertexColors=False,
        ),
        is_internal_geom=internal,
        mesh_count=2,
        mesh_path=mock.Mock(side_effect=lambda slot: f"demo/lod{slot}"),
        load_mesh=mock.Mock(return_value=True),
        select_mesh=mock.Mock(),
        verts=[(-scale, 0, 0), (scale, 0, 0), (0, 2 * scale, 0)],
        tris=[(0, 1, 2)],
        uvs=[(0, 0), (1, 0), (0.5, 1)],
        normals=[(0, 0, 1)] * 3,
        colors=[],
    )


class InspectionTests(unittest.TestCase):
    def setUp(self):
        _MODULE.ERRORS.clear()
        _MODULE.MESHES.clear()
        _MODULE.MATERIALS.clear()

    def test_mesh_paths_resolve_only_beneath_data_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in (r"demo\lod0", "geometries/demo/lod0.mesh", r"Data\Geometries\demo\lod0.mesh"):
                with self.subTest(name=name):
                    path = _MODULE.mesh_asset_path(name)
                    self.assertEqual(path, "geometries/demo/lod0.mesh")
                    asset = _MODULE.resolve_asset(path, root)
                    self.assertEqual(Path(asset["loose_path"]), root / path)
            for name in ("../escape", "/absolute", "C:/absolute"):
                with self.subTest(name=name):
                    asset = _MODULE.resolve_asset(_MODULE.mesh_asset_path(name), root)
                    self.assertFalse(asset["exists_loose"])
                    self.assertIn("invalid_reason", asset)
        self.assertEqual(_MODULE.mesh_asset_path(""), "")

    def test_external_lod_uses_loaded_counts_and_nif_space_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            mesh = root / "geometries/demo/lod1.mesh"
            mesh.parent.mkdir(parents=True)
            mesh.write_bytes(b"mesh fixture")
            model = shape(starfield=True)
            result = _MODULE.geometry_report(model, "shape", True, root, 1)
            model.load_mesh.assert_called_once_with(b"mesh fixture", 1)
            self.assertEqual(result["status"], "loaded")
            self.assertEqual((result["vertex_count"], result["triangle_count"]), (3, 1))
            self.assertEqual(result["actual_triangle_count"], 1)
            self.assertEqual(result["bounds"], {"min": [-1, 0, 0], "max": [1, 2, 0]})
            self.assertEqual(result["lod"], 1)
            self.assertEqual(result["mesh_paths"], ["geometries/demo/lod0.mesh", "geometries/demo/lod1.mesh"])
            dependencies = _MODULE.dependency_report(root)["meshes"]
            self.assertEqual([item["exists_loose"] for item in dependencies], [False, True])
        self.assertEqual(_MODULE.ERRORS, [])

    def test_unloaded_geometry_reports_dependencies_not_zero_counts(self):
        model = shape(starfield=True)
        result = _MODULE.geometry_report(model, "shape", False, None, 0)
        self.assertEqual(result["status"], "not_loaded")
        self.assertIsNone(result["vertex_count"])
        self.assertIsNone(result["triangle_count"])
        self.assertNotIn("bounds", result)
        self.assertEqual(len(_MODULE.MESHES), 2)
        model.load_mesh.assert_not_called()
        self.assertEqual(_MODULE.ERRORS, [])

    def test_missing_or_rejected_geometry_stays_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            mesh = root / "geometries/demo/lod1.mesh"
            mesh.parent.mkdir(parents=True)
            mesh.write_bytes(b"rejected fixture")
            for data_root, lod, message in (
                (None, 0, "requires --data-root"),
                (root, 0, "loose mesh not found"),
                (root, 1, "could not load mesh"),
                (root, 3, "LOD 3 is absent"),
            ):
                with self.subTest(lod=lod, message=message):
                    _MODULE.ERRORS.clear()
                    model = shape(starfield=True)
                    model.load_mesh.return_value = False
                    result = _MODULE.geometry_report(model, "shape", True, data_root, lod)
                    self.assertEqual(result["status"], "unavailable")
                    for field in ("vertex_count", "triangle_count", "actual_vertex_count", "actual_triangle_count", "bounds"):
                        self.assertIsNone(result[field])
                    self.assertIn(message, _MODULE.ERRORS[0]["error"])
                    if lod != 1:
                        model.load_mesh.assert_not_called()

    def test_internal_geometry_needs_no_external_files(self):
        model = shape(starfield=True, internal=True)
        result = _MODULE.geometry_report(model, "shape", True, None, 1)
        model.select_mesh.assert_called_once_with(1)
        model.load_mesh.assert_not_called()
        self.assertEqual(result["storage"], "internal")
        self.assertEqual(result["status"], "loaded")
        self.assertEqual(result["triangle_count"], 1)
        self.assertEqual(result["mesh_paths"], [])
        self.assertEqual(_MODULE.MESHES, set())

    def test_skyrim_counts_and_bounds_are_unchanged(self):
        model = shape()
        for include_geometry in (False, True):
            with self.subTest(include_geometry=include_geometry):
                result = _MODULE.geometry_report(model, "shape", include_geometry, None, 0)
                self.assertEqual((result["vertex_count"], result["triangle_count"]), (3, 1))
                if include_geometry:
                    self.assertEqual(result["bounds"], {"min": [-1, 0, 0], "max": [1, 2, 0]})
        model.verts = model.tris = model.uvs = model.normals = []
        model.properties.vertexCount = model.properties.triangleCount = 0
        empty = _MODULE.geometry_report(model, "shape", True, None, 0)
        self.assertEqual(empty["status"], "loaded")
        self.assertEqual(empty["actual_vertex_count"], 0)
        self.assertIsNone(empty["bounds"])

    def test_summary_does_not_turn_unknown_counts_into_partial_totals(self):
        shapes = [{"geometry": {"vertex_count": 3}}, {"geometry": {"vertex_count": None}}]
        self.assertIsNone(_MODULE.geometry_total(shapes, "vertex_count"))
        self.assertEqual(_MODULE.geometry_total(shapes[:1], "vertex_count"), 3)
        self.assertEqual(_MODULE.geometry_total([], "vertex_count"), 0)

    def test_global_transform_composes_translation_rotation_and_scale(self):
        local = SimpleNamespace(
            translation=(1, 2, 3),
            rotation=((1, 0, 0), (0, 0, -1), (0, 1, 0)),
            scale=3,
        )
        parent = SimpleNamespace(
            id=1, parent=None,
            transform=SimpleNamespace(
                translation=(10, 20, 30),
                rotation=((0, -1, 0), (1, 0, 0), (0, 0, 1)),
                scale=2,
            ),
        )
        root = SimpleNamespace(
            id=0, parent=None,
            transform=SimpleNamespace(
                translation=(5, 6, 7),
                rotation=((0, 0, 1), (0, 1, 0), (-1, 0, 0)),
                scale=0.5,
            ),
        )
        node = SimpleNamespace(id=2, transform=local, parent=None)
        for depth, translation, rotation, scale in (
            (0, [1, 2, 3], [[1, 0, 0], [0, 0, -1], [0, 1, 0]], 3),
            (1, [6, 22, 36], [[0, 0, 1], [1, 0, 0], [0, 1, 0]], 6),
            (2, [23, 17, 4], [[0, 1, 0], [1, 0, 0], [0, 0, -1]], 3),
        ):
            with self.subTest(depth=depth):
                if depth == 1:
                    node.parent = parent
                elif depth == 2:
                    parent.parent = root
                self.assertEqual(_MODULE.global_transform_report(node), {
                    "translation": translation, "rotation": rotation, "scale": scale,
                })
        self.assertEqual(_MODULE.ERRORS, [])

    def test_physics_system_body_index_is_not_a_nif_block_id(self):
        physics = SimpleNamespace(id=3, blockname="bhkPhysicsSystem")
        collision = SimpleNamespace(id=2, blockname="bhkNPCollisionObject", physics_system=physics, body_id=0)
        node = SimpleNamespace(id=0, blockname="NiNode", name="Root", collision_object=collision)
        nif = SimpleNamespace(nodes={"Root": node}, node_ids={0: node})
        result = _MODULE.collision_reports(nif, True)[0]
        self.assertEqual(result["physics_system"], {"id": 3, "type": "bhkPhysicsSystem"})
        self.assertEqual(result["body_index"], 0)
        self.assertNotIn("body", result)
        self.assertEqual(_MODULE.ERRORS, [])

    def test_starfield_material_references_are_not_skyrim_texture_slots(self):
        material = r"Materials\Architecture\Metal.mat"
        model = SimpleNamespace(
            file=SimpleNamespace(game="SF"),
            shader=SimpleNamespace(id=4, blockname="BSLightingShaderProperty", name=material),
        )
        result = _MODULE.shader_report(model, "shape")
        self.assertEqual(result["material_path"], material)
        self.assertIsNone(result["textures"])
        self.assertNotIn("flags_1", result)
        self.assertEqual(_MODULE.MATERIALS, {material})


if __name__ == "__main__":
    unittest.main()
