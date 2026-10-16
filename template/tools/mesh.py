"""Tessellate OCC shapes into a small binary mesh format the promo's three.js scenes load.

<name>.json: {"parts": [{"name", "vertices", "triangles", "edges"}], "bbox": [min, max]}
<name>.bin : per part, float32 positions (v*3), float32 normals (v*3), uint32 indices (t*3), float32 edge segments (e*6)
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepLib import BRepLib_ToolTriangulatedShape
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape


def tessellate(shape, lin: float, ang: float = 0.25):
    BRepMesh_IncrementalMesh(shape, lin, False, ang, True)
    pos, nor, idx = [], [], []
    base = 0
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    face_tris = {}
    while exp.More():
        face = TopoDS.Face_s(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        exp.Next()
        if tri is None:
            continue
        if not tri.HasNormals():
            BRepLib_ToolTriangulatedShape.ComputeNormals_s(face, tri)
        trsf = loc.Transformation()
        rev = face.Orientation() == TopAbs_REVERSED
        n = tri.NbNodes()
        for i in range(1, n + 1):
            p = tri.Node(i).Transformed(trsf)
            pos.append((p.X(), p.Y(), p.Z()))
            d = tri.Normal(i)
            v = np.array([d.X(), d.Y(), d.Z()])
            # rotate the normal with the location (no scale in STEP placements)
            m = np.array([[trsf.Value(r, c) for c in (1, 2, 3)] for r in (1, 2, 3)])
            v = m @ v
            if rev:
                v = -v
            nor.append(tuple(v))
        for k in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(k).Get()
            if rev:
                b, c = c, b
            idx.append((base + a - 1, base + b - 1, base + c - 1))
        face_tris[face.__hash__()] = (face, tri, loc)
        base += n
    # feature edges: every B-rep edge as a polyline
    segs = []
    eexp = TopExp_Explorer(shape, TopAbs_EDGE)
    seen = set()
    while eexp.More():
        edge = TopoDS.Edge_s(eexp.Current())
        eexp.Next()
        h = edge.__hash__()
        if h in seen:
            continue
        seen.add(h)
        loc = TopLoc_Location()
        poly = BRep_Tool.Polygon3D_s(edge, loc)
        pts = []
        if poly is not None:
            trsf = loc.Transformation()
            pts = [poly.Nodes().Value(i).Transformed(trsf) for i in range(1, poly.NbNodes() + 1)]
        else:
            # fall back: the edge's polygon on any triangulation it lies on
            for face, tri, floc in face_tris.values():
                pt = BRep_Tool.PolygonOnTriangulation_s(edge, tri, floc)
                if pt is not None:
                    trsf = floc.Transformation()
                    nodes = pt.Nodes()
                    pts = [tri.Node(nodes.Value(i)).Transformed(trsf) for i in range(nodes.Lower(), nodes.Upper() + 1)]
                    break
        for a, b in zip(pts, pts[1:]):
            segs.append((a.X(), a.Y(), a.Z(), b.X(), b.Y(), b.Z()))
    return (np.array(pos, np.float32).reshape(-1, 3), np.array(nor, np.float32).reshape(-1, 3),
            np.array(idx, np.uint32).reshape(-1, 3), np.array(segs, np.float32).reshape(-1, 6))


def solids_of(shape):
    out = []
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    while exp.More():
        out.append(exp.Current())
        exp.Next()
    return out or [shape]


def write(name: str, parts: list[tuple[str, object]], out: Path, lin: float):
    meta, blobs, lo, hi = [], [], np.full(3, 1e9), np.full(3, -1e9)
    for pname, shape in parts:
        p, n, i, e = tessellate(shape, lin)
        if len(p) == 0:
            continue
        lo, hi = np.minimum(lo, p.min(0)), np.maximum(hi, p.max(0))
        meta.append({"name": pname, "vertices": len(p), "triangles": len(i), "edges": len(e)})
        blobs += [p.tobytes(), n.tobytes(), i.tobytes(), e.tobytes()]
    (out / f"{name}.bin").write_bytes(b"".join(blobs))
    (out / f"{name}.json").write_text(json.dumps({"parts": meta, "bbox": [lo.tolist(), hi.tolist()]}))
    tris = sum(m["triangles"] for m in meta)
    print(f"{name}: {len(meta)} parts, {tris} triangles, bbox {np.round(lo,1).tolist()} {np.round(hi,1).tolist()}")


def read_step(path: Path):
    r = STEPControl_Reader()
    assert r.ReadFile(str(path)) == IFSelect_RetDone, path
    r.TransferRoots()
    return r.OneShape()


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[2:]:
        name, path, lin = arg.split("=")
        try:
            shape = read_step(Path(path))
            write(name, [(f"{name}.{k}", s) for k, s in enumerate(solids_of(shape))], out, float(lin))
        except Exception as exc:  # one bad file must not stop the rest
            print(f"{name}: FAILED {type(exc).__name__}: {exc}")
