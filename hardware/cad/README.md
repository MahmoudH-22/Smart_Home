# CAD (SolidWorks)

Put the SolidWorks files here: `.SLDPRT` (parts), `.SLDASM` (assembly) and `.SLDDRW` (drawings).

- One part per laser-cut panel, named like the DXF files (`front`, `back`, `left`, `right`, `base`, `lid`, …).
- Export the drawings needed for the report (front, side, top and isometric views showing where the sensors and actuators sit) as **PDF** into `docs/reports/`.
- SolidWorks files are binary. Commit them only when a version is finished, not after every small change.
- `hardware/laser_dxf/` has the exact panel outlines. In SolidWorks, use **File → Open → DXF** on a part file to start each sketch.
