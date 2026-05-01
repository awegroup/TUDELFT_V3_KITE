"""
Compute the total projected (drag) area and mass of the V3 kite bridle line system
from bridle_line_measurements.yaml.

Projected area of a line (perpendicular to flow):
  - Round line:  A = diameter * length
  - Flat strap:  A = width * length   (wider dimension faces the flow)

Line mass:
  - Round line:  m = density * pi * (d/2)^2 * length
  - Flat strap:  m = density * width * thickness * length
"""

import math
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_diameter(value):
    """Return dict with type and dimensions (SI, metres).

    Round line  -> {'type': 'round', 'diameter': float}
    Flat strap  -> {'type': 'flat',  'width': float, 'thickness': float}
    """
    if isinstance(value, (int, float)):
        return {"type": "round", "diameter": float(value)}
    s = str(value)
    if "x" in s:
        w, t = s.split("x")
        return {"type": "flat", "width": float(w), "thickness": float(t)}
    return {"type": "round", "diameter": float(s)}


def line_projected_area(length: float, dim: dict) -> float:
    """Projected area [m²] of a single line segment."""
    if dim["type"] == "round":
        return dim["diameter"] * length
    return dim["width"] * length  # flat strap: wider face to wind


def line_volume(length: float, dim: dict) -> float:
    """Volume [m³] of a single line segment."""
    if dim["type"] == "round":
        r = dim["diameter"] / 2.0
        return math.pi * r**2 * length
    return dim["width"] * dim["thickness"] * length


def line_mass(length: float, dim: dict, density: float) -> float:
    """Mass [kg] of a single line segment."""
    return density * line_volume(length, dim)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    yaml_path = Path(__file__).parent / "bridle_line_measurements.yaml"

    with open(yaml_path) as fh:
        data = yaml.safe_load(fh)

    total_area_m2 = 0.0
    total_line_mass_kg = 0.0
    total_line_volume_m3 = 0.0

    # Lines that exist only once on the kite (not mirrored port/starboard)
    SINGULAR_LINES = {"P_L", "SL"}

    # -----------------------------------------------------------------------
    # Lines (front + rear)
    # -----------------------------------------------------------------------
    for section_label, section_key in [
        ("Front lines", "front_lines"),
        ("Rear lines", "rear_lines"),
    ]:
        section = data[section_key]
        col = {h: i for i, h in enumerate(section["headers"])}

        sec_area = 0.0
        sec_mass = 0.0
        sec_volume = 0.0

        print(f"\n{'─'*72}")
        print(f"  {section_label}")
        print(f"{'─'*72}")
        print(
            f"  {'Name':<22}  {'×':>2}  {'Area [m²]':>12}  {'Vol [m³]':>12}  {'Mass [g]':>10}"
        )
        print(f"  {'─'*22}  {'─'*2}  {'─'*12}  {'─'*12}  {'─'*10}")

        for row in section["data"]:
            name = row[col["name"]]
            length = float(row[col["length_m"]])
            diam_val = row[col["diameter_m"]]
            density = float(row[col["density_kg_per_m3"]])

            mult = 1 if name in SINGULAR_LINES else 2
            dim = parse_diameter(diam_val)
            area = mult * line_projected_area(length, dim)
            vol = mult * line_volume(length, dim)
            mass = density * vol

            sec_area += area
            sec_volume += vol
            sec_mass += mass
            print(
                f"  {name:<22}  {mult:>2}  {area:>12.6f}  {vol:>12.6f}  {mass*1e3:>10.3f}"
            )

        print(f"  {'─'*22}  {'─'*2}  {'─'*12}  {'─'*12}  {'─'*10}")
        print(
            f"  {'SUBTOTAL':<26}  {sec_area:>12.6f}  {sec_volume:>12.6f}  {sec_mass*1e3:>10.3f}"
        )

        total_area_m2 += sec_area
        total_line_volume_m3 += sec_volume
        total_line_mass_kg += sec_mass

    # -----------------------------------------------------------------------
    # Pulleys
    # -----------------------------------------------------------------------
    pulley_props = {
        row[0]: {"size": row[1], "weight_kg": float(row[2])}
        for row in data["pulleys"]["data"]
    }

    # Count how many of each pulley type are assigned; ×2 for port+starboard symmetry
    pulley_counts: dict[str, int] = {}
    for row in data["pulley_assignments"]["data"]:
        ptype = row[2]
        pulley_counts[ptype] = pulley_counts.get(ptype, 0) + 2

    total_pulley_mass_kg = 0.0

    print(f"\n{'─'*58}")
    print(f"  Pulleys")
    print(f"{'─'*58}")
    print(f"  {'Type':<22}  {'Count':>6}  {'Unit [g]':>10}  {'Total [g]':>10}")
    print(f"  {'─'*22}  {'─'*6}  {'─'*10}  {'─'*10}")

    for ptype, count in sorted(pulley_counts.items()):
        unit_kg = pulley_props[ptype]["weight_kg"]
        total_kg = unit_kg * count
        total_pulley_mass_kg += total_kg
        print(f"  {ptype:<22}  {count:>6}  {unit_kg*1e3:>10.1f}  {total_kg*1e3:>10.1f}")

    print(f"  {'─'*22}  {'─'*6}  {'─'*10}  {'─'*10}")
    print(f"  {'SUBTOTAL':<40}  {total_pulley_mass_kg*1e3:>10.1f}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    total_mass_kg = total_line_mass_kg + total_pulley_mass_kg
    ref_mass_kg = float(data["bridle_mass"])
    delta_g = (total_mass_kg - ref_mass_kg) * 1e3

    print(f"\n{'═'*62}")
    print(f"  SUMMARY")
    print(f"{'═'*62}")
    print(f"  Total bridle projected area          : {total_area_m2:.6f} m²")
    print(f"  Total bridle line volume             : {total_line_volume_m3:.6f} m³")
    print(
        f"  Total line mass (excl. pulleys)      : {total_line_mass_kg*1e3:7.1f} g  "
        f"({total_line_mass_kg:.4f} kg)"
    )
    print(
        f"  Total pulley mass                    : {total_pulley_mass_kg*1e3:7.1f} g  "
        f"({total_pulley_mass_kg:.4f} kg)"
    )
    print(f"  {'─'*58}")
    print(
        f"  Total bridle line system mass (computed): {total_mass_kg*1e3:7.1f} g  "
        f"({total_mass_kg:.4f} kg)"
    )
    print(
        f"  Reference bridle line system mass (YAML): {ref_mass_kg*1e3:7.1f} g  "
        f"({ref_mass_kg:.4f} kg)"
    )
    print(f"  {'─'*58}")
    print(f"  Delta                                : {delta_g:+.1f} g")
    print(f"{'═'*62}\n")


if __name__ == "__main__":
    main()
