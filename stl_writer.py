"""
stl_writer.py
=============
Writes a binary STL file visualising one or more CoordinateFrame objects
as realistic dental implant cylinders.

Each implant is rendered with:
  • Outer surface with a single horizontal ring groove near the base of the screw recess
  • Top annular face with a central screw hole (hex-socket style opening)
  • Inner cylindrical wall of the screw recess
  • Solid flat bottom cap (closed apex)

Public API
----------
  STLWriter(frames, output_path, ...).write()  -> str
"""

import math
import os
import struct

from file_reader import CoordinateFrame, _normalize, _cross, _sub


class STLWriter:
    """
    Parameters
    ----------
    frames         : list[CoordinateFrame]
    output_path    : str
    implant_length : float   total length in mm          (default 8.0)
    outer_radius   : float   outer radius at crest in mm (default 2.7)
    groove_depth   : float   how deep each groove cuts   (default 0.55)
    groove_count   : int     number of ring grooves       (default 9)
    screw_radius   : float   radius of top screw recess  (default 0.9)
    screw_depth    : float   depth of screw recess       (default 2.0)
    segments       : int     circumference divisions      (default 24)
    # legacy CLI args – ignored
    axis_length / shaft_radius
    """

    def __init__(
        self,
        frames: list[CoordinateFrame],
        output_path: str,
        implant_length: float = 8.0,
        outer_radius:   float = 2.7,
        groove_depth:   float = 0.55,
        groove_count:   int   = 9,
        screw_radius:   float = 0.9,
        screw_depth:    float = 2.0,
        segments:       int   = 24,
        axis_length:    float = 10.0,   # ignored
        shaft_radius:   float = 0.3,    # ignored
    ):
        self.frames         = frames
        self.output_path    = output_path
        self.implant_length = implant_length
        self.outer_radius   = outer_radius
        self.groove_depth   = groove_depth
        self.groove_count   = groove_count
        self.screw_radius   = screw_radius
        self.screw_depth    = screw_depth
        self.segments       = max(segments, 6)
        self._tris: list    = []

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    def write(self) -> str:
        self._tris.clear()
        for frame in self.frames:
            self._add_implant(frame.origin, frame.z_axis, frame.x_axis)

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "wb") as fh:
            fh.write(b"\x00" * 80)
            fh.write(struct.pack("<I", len(self._tris)))
            for normal, v1, v2, v3 in self._tris:
                fh.write(struct.pack("<fff", *normal))
                fh.write(struct.pack("<fff", *v1))
                fh.write(struct.pack("<fff", *v2))
                fh.write(struct.pack("<fff", *v3))
                fh.write(b"\x00\x00")

        print(f"  [STL] -> {self.output_path}  ({len(self._tris)} triangles)")
        return self.output_path

    # ------------------------------------------------------------------ #
    #  Geometry                                                            #
    # ------------------------------------------------------------------ #

    def _add_implant(self, origin, z_axis, x_axis):
        """
        Structure
        ---------
        • Outer wall  – cylindrical surface with one ring groove near the upper base
        • Top annular cap – solid ring (r_in → r_out) at z=L, with hole in the middle
        • Bottom and interior left open (empty volume)
        """
        L     = self.implant_length
        r_out = self.outer_radius
        r_val = r_out - self.groove_depth
        r_in  = self.screw_radius
        N     = self.segments

        up = z_axis

        u = _normalize(x_axis)
        v = _normalize(_cross(z_axis, u))

        # Groove: semicircular cross-section, 0.8 mm wide, 1.5 mm below top rim
        gw        = 0.8                   # groove diameter (width along Z)
        gr        = gw / 2.0              # groove radius
        groove_cz = L - gr - 1.5          # Z centre of the semicircle
        arc_steps = 12                    # points along the arc

        profile = [(0.0, r_out), (groove_cz - gr, r_out)]

        for s in range(arc_steps + 1):
            angle = math.pi * s / arc_steps   # 0 → π  (outer → valley → outer)
            z_pt  = groove_cz - gr * math.cos(angle)
            r_pt  = r_out     - gr * math.sin(angle)   # sin≥0, so dips inward
            profile.append((z_pt, r_pt))

        profile.append((L, r_out))

        outer_rings = self._make_rings(profile, origin, z_axis, u, v)
        self._revolve_surface(outer_rings, z_axis)

        # ── Top annular cap (r_in → r_out): upper base with hole ─────────
        top_ctr      = tuple(origin[k] + z_axis[k] * L for k in range(3))
        top_out_ring = outer_rings[-1][2]
        top_in_ring  = self._make_single_ring(top_ctr, r_in, u, v)

        for i in range(N):
            j = (i + 1) % N
            o0, o1 = top_out_ring[i], top_out_ring[j]
            s0, s1 = top_in_ring[i],  top_in_ring[j]
            self._tris.append((up, o0, o1, s1))
            self._tris.append((up, o0, s1, s0))

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _make_single_ring(self, centre, r, u, v):
        N = self.segments
        pts = []
        for i in range(N):
            a = 2.0 * math.pi * i / N
            ca, sa = math.cos(a), math.sin(a)
            pts.append(tuple(centre[k] + r * (ca * u[k] + sa * v[k]) for k in range(3)))
        return pts

    def _make_rings(self, profile, origin, z_axis, u, v):
        """Return list of (z_local, r, ring_pts) for each profile point."""
        result = []
        for z_local, r in profile:
            ctr = tuple(origin[k] + z_axis[k] * z_local for k in range(3))
            result.append((z_local, r, self._make_single_ring(ctr, r, u, v)))
        return result

    def _revolve_surface(self, rings, z_axis):
        """Connect consecutive rings in the profile to form the outer surface."""
        N = self.segments
        for idx in range(len(rings) - 1):
            z0, r0, ring0 = rings[idx]
            z1, r1, ring1 = rings[idx + 1]

            if abs(z0 - z1) < 1e-9:
                # Vertical step (groove side wall) → flat annular face
                # Normal is exactly ±z_axis (no cross-product needed)
                if r1 < r0:
                    # Face points downward (into groove from above)
                    flat_n = tuple(-z_axis[k] for k in range(3))
                    for i in range(N):
                        j = (i + 1) % N
                        a, b = ring0[i], ring0[j]
                        c, d = ring1[i], ring1[j]
                        self._tris.append((flat_n, a, c, d))
                        self._tris.append((flat_n, a, d, b))
                else:
                    # Face points upward (groove exit shoulder)
                    flat_n = z_axis
                    for i in range(N):
                        j = (i + 1) % N
                        a, b = ring0[i], ring0[j]
                        c, d = ring1[i], ring1[j]
                        self._tris.append((flat_n, a, b, d))
                        self._tris.append((flat_n, a, d, c))
            else:
                # Slanted or vertical band (side of cylinder / groove floor)
                for i in range(N):
                    j = (i + 1) % N
                    b0, b1 = ring0[i], ring0[j]
                    t0, t1 = ring1[i], ring1[j]
                    n = _normalize(_cross(_sub(b1, b0), _sub(t0, b0)))
                    self._tris.append((n, b0, b1, t0))
                    self._tris.append((n, b1, t1, t0))

    def _add_disk_cap(self, centre, rim_ring, normal, inward: bool):
        """Triangle fan from centre point to a ring (solid disk)."""
        N = self.segments
        for i in range(N):
            j = (i + 1) % N
            if inward:
                self._tris.append((normal, centre, rim_ring[j], rim_ring[i]))
            else:
                self._tris.append((normal, centre, rim_ring[i], rim_ring[j]))
