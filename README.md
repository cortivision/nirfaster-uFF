# nirfaster-uFF

Public repository containing the micro (fast and furious) version of NIRFASTer

- Version: 1.2.1
- Authors: Jiaming Cao (University of Macau), MILab@UoB
- License: BSD

This is a compact (aka micro) version of the NIRFASTer with Python interface, providing the most essential functionalities (that is, forward modeling on standard mesh) in NIRFASTer. This version is created aiming to be easily integratable with other toolkits, but can also be used on its own.

The toolbox can be run on Linux, Mac, and Windows. To use GPU acceleration, you will need to have a Nvidia card with compute capability higer than `sm_50`, i.e. the GTX9xx series.

## Cortivision fork: platform wheels

Our changes live on the `integration` branch (open pull requests against it); `main` mirrors
[milabuob/nirfaster-uFF](https://github.com/milabuob/nirfaster-uFF) unchanged, so taking a new
upstream version is always a fast-forward. To sync:

```bash
git remote add upstream https://github.com/milabuob/nirfaster-uFF.git   # once
git fetch upstream
git push origin upstream/main:main                  # main = the original
git checkout integration && git merge main          # our changes on top; resolve conflicts here
```

This fork packages nirfasteruff's code together with the compiled parts of the upstream release
(solver modules, CUDA DLLs, meshers) as one wheel per platform, so a plain `pip install` gets
everything and nothing has to be unzipped into the package by hand. The wheels are attached to
the GitHub release [`v1.2.1-wheels`](https://github.com/cortivision/nirfaster-uFF/releases/tag/v1.2.1-wheels):

| Wheel | Platform | Contents |
|---|---|---|
| `nirfasteruff-1.2.1-cp313-cp313-win_amd64.whl` | Windows, Python 3.13 | CPU + CUDA solver, meshers |
| `nirfasteruff-1.2.1-cp312-cp312-macosx_13_0_universal2.whl` | macOS 13+, Python 3.12, Apple Silicon + Intel | CPU solver, meshers |

Depend on them by URL, one line per platform, pinned by hash so pip refuses any other file:

```toml
"nirfasteruff @ https://github.com/cortivision/nirfaster-uFF/releases/download/v1.2.1-wheels/nirfasteruff-1.2.1-cp313-cp313-win_amd64.whl#sha256=af15446c44d3c56e69a4892fe6749aa61435d36c957fef7417d220a8c739e24d ; sys_platform == 'win32'",
"nirfasteruff @ https://github.com/cortivision/nirfaster-uFF/releases/download/v1.2.1-wheels/nirfasteruff-1.2.1-cp312-cp312-macosx_13_0_universal2.whl#sha256=2748c5e0a40888125e778250ae22fd0e3f1fd37c7da3bf14d91da53e23cd31cb ; sys_platform == 'darwin'",
```

To publish wheels for a new upstream release:

1. In `tools/build_wheels.py`, update `RELEASE`, `ZIPS` (the zip names and their SHA-256 from the
   upstream release page) and, if the platforms change, `WHEELS`. Update the version in
   `pyproject.toml`.
2. Run `python tools/build_wheels.py`; the wheels land in `dist/` (gitignored). Every zip is
   checked against its SHA-256 first.
3. Install each wheel into a fresh environment on its platform and run `python tools/test_wheel.py`
   from the repo root. It runs the solvers (and compares GPU with CPU where CUDA exists) and both
   meshers on the demo data.
4. Attach the wheels to a new GitHub release, then update the URLs and `#sha256=` hashes in the
   apps that depend on them.

## Dependencies

Packages required:

- NumPy
- Scipy
- psutil
- matplotlib
- scikit-image (*new from version 1.2*)

## How to Install

1. Clone the main repo, which contains two folders: nirfasteruff (THE source code) and demo (a few demo codes)
2. Depending on your system and Python version, download the appropriate zip file(s) from the appropriate Release, and unzip the contents into the *nirfasteruff* folder
3. You should be good to go

Regardless of your setup, you will need to download the CPU library (cpu-*os*-python*), which also includes the mesher binary. If your system is CUDA-enabled, you will *also* need to download the appropriate GPU library (gpu-*os*-python*), in addition.

**Special notes to Mac users**

*Support for Python versions other than 3.10-3.12 are not available at the moment. We are not dropping support for Mac, but will be a little slow in the near future.* Mac may throw a warning that the file is damaged and need to be moved to Trash. You can bypass this by using command

```bash
xattr -c <your_library>.so
```

## The full version

The full version of the package can be found at: https://github.com/milabuob/nirfaster-FF

## Citation

If you are using our toolbox, please cite our papers:

1. Cao, Jiaming, et al. “NIRFASTerFF: An accessible, cross-platform python package for fast photon modeling.” *Journal of Biomedical Optics*, vol. 30, no. 11, 2025, https://doi.org/10.1117/1.jbo.30.11.115001.

2. Dehghani, Hamid, et al. “Near Infrared Optical Tomography using NIRFAST: Algorithm for numerical model and image reconstruction.” *Communications in Numerical Methods in Engineering*, vol. 25, no. 6, 2008, pp. 711–732, https://doi.org/10.1002/cnm.1162.

## The demos

The provided demo codes shows you all the functionalities the micro version. They are commented in detail and should explain the syntaxes reasonably well.

The head model is adapted from the examples in the NeuroDOT toolbox: https://github.com/WUSTL-ORL/NeuroDOT

## Available key functionalities

- I/O of NIRFAST(er) meshes. This is directly compatible with the Matlab version
- Mesh creation from segmented volumetric data, *and segemented 2D image (new from 1.2.0)*
- Conversion from solid mesh to NIRFASTer mesh
- Fluence calculation (CW/FD)

## Changelog

1.2.1

- Fixed a bug in mesh.save_nirfast (all mesh types), where large numbers in mesh.elements were incorrectly truncated. 

1.2.0

- Support for newer GPUs (50xx series)

- Support for Python 3.8 and 3.13 (Windows and Linux only)

- Minor bug fix in gen_intmat

- 2D meshing added

1.0.0

- Added support for Python 3.12
- CGAL mesher separated from the CPU library as a standalone application
- Fixed a bug in gen_intmat, which leads to incorrect data.tomesh() result when xgrid and ygrid have different resolutions
- Fixed a bug which causes crashes when mesh has only one source
- Number of OMP threads in the CPU solvers can now be set using function nirfasteruff.utils.get_nthread()
- GPU solver performance improved
- More efficient source vector calculation
- docstring reformatted for better readability
- Stricter error handling (consistent with the full version), which raises errors instead of printing a message

## Some technical details

The reason for the Mac issue: Mac automatically attaches a quarantine attribute to downloaded files, and the marked files will be checked by the Gatekeeper. Somehow (file I/O, possibly), Apple's gatekeeper is not very happy about my code and refuses to run. This checking can be bypassed by manually removing the quarantine attribute. You can view this by `ls -l@`, and you should see the `com.apple.quarantine` thing.

Speed-critically functions are packed in precompiled libraries, nirfasteruff_cpu and nirfasteruff_cuda. The Linux and Mac versions are statically linked so there is only one file for each library, and no extra dependen is required (need testing). Only limited static linking could be used on Windows (e.g. the CUDA libraries), and consequently the necessary dlls are also included. In order to support older GPUs (sm<7.5), CUDA 12.9 was used to compile the GPU libraries, and this will remain the CUDA version we use for some time unless there is a compelling reason to upgrade. 

#### Potential pitfalls:

- Python by default uses shallow copies, and sometimes fields in the mesh can be accidentally changed because of this. I tried to avoid this by explicitly using deep copies at various places, but undetected problems may still be there
- If a sliced array is fed into the C++ functions, they may throw a type error. This is because the sliced arrays may not be contiguous anymore. Using np.ascontiguousarray(*some_array*, dtype=*some_type*) will solve the problem. I tried to have this safeguard line in most of the high-level functions, but might have overlooked some
- When a C++ function takes a matrix argument, make sure it's actually a matrix. This is especially relevant when you try to feed it with an 1xN matrix. np.atleast2d() can help.
- Will not run on older linux distributions with GLIBC<3.25
