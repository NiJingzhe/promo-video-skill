"""EXAMPLE for a parametric CAD notebook: copy and adapt the names. Mesh the U link body for other parameter values: the example's notebook, run on a copy whose
dimensions.py has different defaults (the notebook reads its sizes from DIMS = ULinkDimensions())."""
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mesh import write  # noqa: E402

SRC = Path(sys.argv[1])  # examples/u_link_motor_mount
OUT = Path(sys.argv[2])
# each variant: "L=128,D=30,r_corner=22" (any float field of ULinkDimensions)
VARIANTS = [dict((k, float(x)) for k, x in (kv.split("=") for kv in v.split(","))) for v in sys.argv[3:] if not v.startswith("--")]


def run(values: dict[str, float]):
    from simplecadapi.runtime import run_notebook

    work = Path(tempfile.mkdtemp(prefix="ulink-"))
    for f in ("u_link.py", "common.py", "dimensions.py"):
        shutil.copy(SRC / f, work / f)
    dims = (work / "dimensions.py").read_text()
    for name, value in values.items():
        dims, n = re.subn(rf"^(    {name}: float = )[0-9.]+", rf"\g<1>{value}", dims, count=1, flags=re.M)
        assert n == 1, name
    (work / "dimensions.py").write_text(dims)
    sys.path.insert(0, str(work))
    for mod in ("dimensions", "common"):
        sys.modules.pop(mod, None)
    shutil.copy(SRC / "shell.py", work / "shell.py")
    try:
        body = run_notebook(work / "u_link.py", cache=False, product=False).values["cable_windows"]
        shell = run_notebook(work / "shell.py", cache=False, product=False).values["countersunk_holes"] if WITH_SHELL else None
    finally:
        sys.path.remove(str(work))
    return body, shell


WITH_SHELL = "--shell" in sys.argv
VARIANTS = [v for v in VARIANTS if v]
from simplecadapi import ql  # noqa: E402

for values in VARIANTS:
    t = time.time()
    body, shell = run(values)
    name = "ulink_" + "_".join(f"{k}{v:g}" for k, v in values.items())
    write(name, [(name, body.wrapped)], OUT, 0.05)
    if shell is not None:
        write(name + "_assembly", [(name + ".body", body.wrapped), (name + ".shell", shell.wrapped)], OUT, 0.05)
    print(f"  {name}: volume={body.get_volume():.3f} faces={len(ql.faces().resolve(body))} in {time.time() - t:.1f}s", flush=True)
