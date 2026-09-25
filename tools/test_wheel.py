"""Check that an installed nirfasteruff wheel really works, by running each compiled part
on real data rather than just importing it.

Install the wheel for your platform into a fresh environment, then from the repo root:
    python tools/test_wheel.py

It uses the demo data in demo/ and checks: the CPU solver (CW and frequency domain, 2D
and 3D), the CUDA solver against the CPU one where a CUDA GPU exists (two independent
implementations have to agree), the Triangle mesher and the CGAL mesher. Exits non-zero
if anything fails.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import scipy.io as sio

import nirfasteruff as ff

DEMO = Path(__file__).resolve().parent.parent / "demo"
GPU_TOLERANCE = 1e-4  # max relative difference between CPU and GPU boundary data
results = []


def check(name, func):
    """Run one check and record the outcome"""
    start = time.perf_counter()
    try:
        detail = func()
        ok = True
    except Exception as exc:  # report every failure, keep going
        detail, ok = f"{type(exc).__name__}: {exc}", False
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name:34s} {time.perf_counter() - start:6.1f}s  {detail or ''}")


def mesh_2d():
    mesh = ff.base.stndmesh()
    mesh.from_mat(str(DEMO / "circle_stnd"))
    return mesh


def mesh_3d():
    mesh = ff.base.stndmesh()
    mesh.from_file(str(DEMO / "slab_stnd"))
    return mesh


def solve(mesh, freq, solver):
    data, _ = mesh.femdata(freq, solver=solver)
    return data


def cw_2d_cpu():
    amp = np.asarray(solve(mesh_2d(), 0, "CPU").amplitude)
    assert amp.size and np.all(np.isfinite(amp)) and np.all(amp > 0), "boundary data not finite/positive"
    return f"{amp.size} channels"


def fd_2d_cpu():
    data = solve(mesh_2d(), 1e8, "CPU")
    phase = np.asarray(data.phase)
    assert np.all(np.isfinite(phase)) and np.any(phase != 0), "no phase at 100 MHz"
    return f"phase range {phase.min():.1f}..{phase.max():.1f} deg"


def cw_3d_cpu():
    amp = np.asarray(solve(mesh_3d(), 0, "CPU").amplitude)
    assert amp.size and np.all(np.isfinite(amp)) and np.all(amp > 0), "boundary data not finite/positive"
    return f"{amp.size} channels"


def gpu_matches_cpu(make_mesh, freq):
    def run():
        cpu = np.asarray(solve(make_mesh(), freq, "CPU").amplitude)
        gpu = np.asarray(solve(make_mesh(), freq, "GPU").amplitude)
        rel = np.max(np.abs(gpu - cpu) / np.abs(cpu))
        assert rel < GPU_TOLERANCE, f"GPU differs from CPU by {rel:.2e}"
        return f"max relative difference {rel:.1e}"
    return run


def triangle_mesher():
    yy, xx = np.mgrid[:80, :80]
    radius = np.hypot(xx - 40, yy - 40)
    img = np.zeros((80, 80), dtype=np.int32)
    img[radius < 35] = 1
    img[radius < 15] = 2
    ele, nodes = ff.meshing.img2mesh(img, ff.utils.MeshingParams2D(max_area=4.0))
    assert len(ele) and len(nodes), "empty mesh"
    assert set(np.unique(ele[:, -1])) == {1, 2}, "regions lost"
    return f"{len(ele)} triangles, {len(nodes)} nodes"


def cgal_mesher():
    vol = sio.loadmat(str(DEMO / "headvol.mat"))["mask"]
    params = ff.utils.MeshingParams(general_cell_size=8.0, facet_size=4.0, facet_distance=2.0, lloyd_smooth=0)
    ele, nodes = ff.meshing.RunCGALMeshGenerator(vol, params)
    assert len(ele) and len(nodes), "empty mesh"
    return f"{len(ele)} tetrahedra, {len(nodes)} nodes, {len(np.unique(ele[:, -1]))} regions"


def main():
    installed = Path(ff.__file__).resolve()
    if DEMO.parent in installed.parents:
        sys.exit(f"nirfasteruff is imported from the repo ({installed}), not from the installed wheel")
    cuda = ff.utils.isCUDA()
    print(f"nirfasteruff {ff.__version__} from {installed.parent}")
    print(f"Python {sys.version.split()[0]} on {sys.platform} | CUDA available: {cuda}\n")
    os.chdir(tempfile.mkdtemp(prefix="nirfaster-test-"))  # the meshers write scratch files to the cwd

    check("2D circle, CW, CPU solver", cw_2d_cpu)
    check("2D circle, 100 MHz, CPU solver", fd_2d_cpu)
    check("3D slab, CW, CPU solver", cw_3d_cpu)
    if cuda:
        check("2D circle, CW, GPU = CPU", gpu_matches_cpu(mesh_2d, 0))
        check("2D circle, 100 MHz, GPU = CPU", gpu_matches_cpu(mesh_2d, 1e8))
        check("3D slab, CW, GPU = CPU", gpu_matches_cpu(mesh_3d, 0))
    else:
        print("SKIP  GPU checks (no CUDA device)")
    check("Triangle mesher (2D image)", triangle_mesher)
    check("CGAL mesher (3D head volume)", cgal_mesher)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
