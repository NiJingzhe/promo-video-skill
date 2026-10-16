"""EXAMPLE for a parametric CAD notebook: copy and adapt the names. Mesh every intermediate solid of the u_link body notebook, one file per feature cell."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mesh import write  # noqa: E402
from simplecadapi.runtime import run_notebook  # noqa: E402

NB = Path(sys.argv[1])
OUT = Path(sys.argv[2])
STAGES = ["u_rod", "split_plane", "motor_pockets", "boss_columns", "boss_holes", "gussets", "gusset_chamfer", "edge_fillet", "cable_windows"]
run = run_notebook(NB)
for k, name in enumerate(STAGES):
    solid = run.values[name]
    write(f"ulink_s{k}", [(name, solid.wrapped)], OUT, 0.04)
for c in run.cells[:3]:
    print(c)
