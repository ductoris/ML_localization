#!/usr/bin/env python3
"""Generate a 7-room house world for Gazebo Harmonic, in 3 lighting conditions
(house_cloudy.sdf, house_sunny.sdf, house_night.sdf).

Walls/floors/ceiling are primitives; furniture are Gazebo Fuel models stored in ./models
(run with GZ_SIM_RESOURCE_PATH pointing at that folder).

Layout (top view, metres, origin at house centre, x -> east, y -> north):

 y=7.5  +--------W----+---w-----+----W------+-W---------+
        |  Bedroom1   |  Bath   |  Office   | Bedroom2  |
 y=1.5  +-----D-------+---D-----+----D------+----D------+
        |                    Hallway                     |
 y=-1.5 +---------D-------------------+--------D---------W
        |   Living / dining room      D     Kitchen      |
 y=-7.5 +----W----------W-------------+-------W----------+
      x=-10.5                       x=1.5             x=10.5     (D = door, W = window)
"""
import math
from pathlib import Path

H = 2.5        # wall height (ceiling sits on top)
T = 0.15       # wall thickness
DOOR = 1.2     # door width
DOOR_H = 2.1   # door height
WIN = (0.9, 2.1)  # default window sill / top height
XMAX, YMAX = 10.5, 7.5  # half extents of the house

# name: (xmin, xmax, ymin, ymax, floor rgb, wall rgb)
ROOMS = {
    "bedroom1": (-10.5, -3.75, 1.5, 7.5, (0.55, 0.40, 0.25), (0.85, 0.75, 0.55)),  # warm beige
    "bathroom": (-3.75, 0.0, 1.5, 7.5, (0.75, 0.85, 0.90), (0.55, 0.78, 0.78)),    # teal
    "office":   (0.0, 5.25, 1.5, 7.5, (0.35, 0.35, 0.40), (0.65, 0.70, 0.82)),     # grey-blue
    "bedroom2": (5.25, 10.5, 1.5, 7.5, (0.80, 0.65, 0.70), (0.78, 0.66, 0.80)),    # lilac
    "hallway":  (-10.5, 10.5, -1.5, 1.5, (0.85, 0.80, 0.70), (0.93, 0.90, 0.82)),  # cream
    "living":   (-10.5, 1.5, -7.5, -1.5, (0.45, 0.30, 0.20), (0.62, 0.72, 0.55)),  # sage green
    "kitchen":  (1.5, 10.5, -7.5, -1.5, (0.90, 0.90, 0.85), (0.93, 0.70, 0.50)),   # terracotta
}
EXTERIOR_RGB = (0.80, 0.78, 0.72)

# Walls: (axis it runs along, fixed coord, start, end, openings)
# opening = (centre, width, bottom z, top z)
def door(c):
    return (c, DOOR, 0.0, DOOR_H)


def window(c, w=2.0, sill=WIN[0], top=WIN[1]):
    return (c, w, sill, top)


WALLS = [
    # outer walls
    ("x", YMAX, -XMAX, XMAX, [window(-5.0, 1.6), window(-1.9, 0.8, 1.4), window(2.6), window(6.3, 1.6)]),
    ("x", -YMAX, -XMAX, XMAX, [window(-8.0, 2.5), window(-3.0, 2.5), window(4.5, 1.6)]),
    ("y", -XMAX, -YMAX, YMAX, []),
    ("y", XMAX, -YMAX, YMAX, [window(-5.0, 1.6, 1.1)]),
    # hallway walls with doors into each room
    ("x", 1.5, -XMAX, XMAX, [door(-7.1), door(-1.9), door(2.6), door(7.9)]),
    ("x", -1.5, -XMAX, XMAX, [door(-4.5), door(6.0)]),
    # partitions between north rooms, and living / kitchen
    ("y", -3.75, 1.5, YMAX, []), ("y", 0.0, 1.5, YMAX, []), ("y", 5.25, 1.5, YMAX, []),
    ("y", 1.5, -YMAX, -1.5, [door(-4.5)]),
]

# (Fuel model folder in ./models, x, y, yaw in degrees[, z])
FURNITURE = [
    # Bedroom 1: double bed against north wall, two lamps, wardrobe, bookshelf, armchair
    ("Bed", -7.5, 6.1, 0), ("LampAndStand", -9.3, 7.0, 0), ("LampAndStand", -5.7, 7.0, 0),
    ("WhiteCabinet", -10.15, 4.0, 90), ("Bookshelf", -9.3, 1.85, 180), ("Chair", -4.4, 2.4, 135),
    # Bathroom
    ("Bathtub", -1.9, 6.95, 0), ("Toilet", -3.25, 4.5, 0), ("BathroomSink", -0.1, 4.0, -90, 0.5),
    # Office
    ("Office_Desk", 2.6, 7.0, -90), ("OfficeChairBlack", 2.6, 6.1, 0),
    ("Bookshelf", 4.95, 3.6, -90), ("Bookshelf", 4.95, 4.6, -90), ("Cabinet", 0.4, 4.0, 90),
    ("Office_Desk", 2.6, 3.4, 90), ("OfficeChairBlack", 2.6, 2.6, 180),
    # Bedroom 2: bed against east wall (different from bedroom 1), desk, armchair, wardrobe
    ("Bed", 9.1, 4.5, -90), ("LampAndStand", 10.0, 6.3, 0), ("WhiteCabinet", 8.8, 7.15, 0),
    ("Desk", 5.6, 4.0, 0), ("WoodenChair", 6.2, 4.0, 180), ("MiniSofa", 6.0, 2.3, 0),
    # Hallway
    ("Cabinet", -10.1, 0.0, 90), ("LampAndStand", 10.1, 0.0, 0), ("Bookshelf", -8.0, -1.15, 180),
    ("Chair", 0.2, -1.0, 90),
    # Living / dining room
    ("Sofa", -6.5, -6.8, 90), ("CoffeeTable", -6.5, -5.3, 0), ("TVStand", -6.5, -1.8, 0),
    ("MiniSofa", -8.6, -5.3, 0), ("MiniSofa", -4.4, -5.3, 0), ("Bookshelf", -10.15, -4.5, 90),
    ("LampAndStand", -10.0, -7.0, 0),
    ("Dining_Table", -1.0, -4.5, 0), ("WoodenChair", -1.8, -5.0, 0), ("WoodenChair", -1.8, -4.0, 0),
    ("WoodenChair", -0.2, -5.0, 180), ("WoodenChair", -0.2, -4.0, 180),
    # Kitchen
    ("KitchenCountertop", 10.0, -5.0, 0), ("Refrigerator", 2.2, -7.0, 0),
    ("KitchenSink", 6.4, -7.0, 0), ("KitchenSink", 7.2, -7.0, 0), ("KitchenSink", 8.0, -7.0, 0),
    ("Fridge", 3.2, -7.1, 0), ("Dining_Table", 5.5, -4.5, 90),
    ("WoodenChair", 5.0, -5.3, 90), ("WoodenChair", 6.0, -5.3, 90),
    ("WoodenChair", 5.0, -3.7, -90), ("WoodenChair", 6.0, -3.7, -90),
]

# Paintings / posters: (x, y on the wall's centre line, direction it faces, width, height,
# centre z, canvas rgb, inner-rectangle rgb)
PAINTINGS = [
    (-7.5, 7.5, "-y", 1.2, 0.6, 1.75, (0.15, 0.25, 0.55), (0.95, 0.80, 0.30)),   # bedroom1 over bed
    (-3.75, 4.0, "-x", 0.7, 0.9, 1.5, (0.85, 0.30, 0.25), (0.20, 0.20, 0.20)),   # bedroom1 east wall
    (0.0, 5.8, "-x", 0.5, 0.7, 1.6, (0.95, 0.95, 0.90), (0.20, 0.55, 0.70)),     # bathroom
    (0.0, 6.0, "+x", 1.0, 0.7, 1.5, (0.10, 0.10, 0.10), (0.90, 0.45, 0.10)),     # office
    (5.25, 6.3, "-x", 1.6, 1.0, 1.4, (0.98, 0.98, 0.98), (0.98, 0.98, 0.98)),    # office whiteboard
    (5.25, 5.8, "+x", 0.6, 0.9, 1.5, (0.95, 0.70, 0.20), (0.30, 0.15, 0.45)),    # bedroom2 poster
    (-4.5, 1.5, "-y", 0.8, 0.6, 1.5, (0.20, 0.45, 0.25), (0.90, 0.90, 0.80)),    # hallway
    (5.0, 1.5, "-y", 0.8, 0.6, 1.5, (0.60, 0.15, 0.15), (0.95, 0.85, 0.60)),     # hallway
    (-1.5, -1.5, "+y", 1.0, 0.7, 1.5, (0.25, 0.30, 0.60), (0.85, 0.40, 0.35)),   # hallway
    (8.5, -1.5, "+y", 0.6, 0.8, 1.5, (0.10, 0.10, 0.10), (0.85, 0.85, 0.85)),    # hallway
    (-1.0, -1.5, "-y", 1.5, 0.9, 1.6, (0.90, 0.85, 0.70), (0.25, 0.45, 0.65)),   # living over table
    (-5.5, -7.5, "+y", 0.9, 0.6, 1.5, (0.55, 0.20, 0.30), (0.95, 0.75, 0.55)),   # living south wall
    (1.5, -6.3, "+x", 0.6, 0.6, 1.6, (0.95, 0.95, 0.95), (0.10, 0.10, 0.10)),    # kitchen west wall
    (8.5, -1.5, "-y", 0.8, 0.6, 1.6, (0.30, 0.55, 0.30), (0.95, 0.90, 0.40)),    # kitchen north wall
]

# Lighting conditions as in the COLD dataset used by the paper (cloudy / sunny / night).
# With the ceiling, sunlight only enters through the windows.
PRESETS = {
    "cloudy": dict(ambient=0.4, background=(0.7, 0.7, 0.72), sun=(0.35, 0.35, 0.38),
                   sun_dir="-0.3 0.4 -0.6", lamp=(0.35, 0.35, 0.33)),
    # sunny: lamps are off in reality; the weak warm "lamp" light stands in for sunlight
    # bouncing around the room, which the renderer does not simulate
    "sunny":  dict(ambient=0.55, background=(0.55, 0.7, 0.95), sun=(1.0, 0.95, 0.85),
                   sun_dir="-0.5 0.6 -0.45", lamp=(0.28, 0.26, 0.22)),
    "night":  dict(ambient=0.05, background=(0.02, 0.02, 0.05), sun=(0.0, 0.0, 0.0),
                   sun_dir="-0.3 0.4 -0.6", lamp=(0.8, 0.7, 0.5)),
}


def rgb_str(c):
    return f"{c[0]} {c[1]} {c[2]} 1"


def material(rgb):
    return (f"<material><ambient>{rgb_str(rgb)}</ambient><diffuse>{rgb_str(rgb)}</diffuse>"
            f"<specular>0.1 0.1 0.1 1</specular></material>")


def box_link(name, x, y, z, sx, sy, sz, rgb, collide=True):
    """A link with one box; (x, y, z) is the box centre."""
    geom = f"<geometry><box><size>{sx} {sy} {sz}</size></box></geometry>"
    col = f'<collision name="c">{geom}</collision>' if collide else ""
    return (f'<link name="{name}"><pose>{x} {y} {z} 0 0 0</pose>{col}'
            f'<visual name="v">{geom}{material(rgb)}</visual></link>')


def static_model(name, links):
    return f'<model name="{name}"><static>true</static>{"".join(links)}</model>'


def room_at(x, y):
    for n, (x0, x1, y0, y1, *_) in ROOMS.items():
        if x0 < x < x1 and y0 < y < y1:
            return n
    return None


def wall_pieces(start, end, openings):
    """Split a wall into (a, b, z_bottom, z_top) pieces around its openings."""
    pieces, pos = [], start
    for c, w, zb, zt in sorted(openings):
        a, b = c - w / 2, c + w / 2
        pieces.append((pos, a, 0.0, H))
        if zb > 0:
            pieces.append((a, b, 0.0, zb))   # sill
        pieces.append((a, b, zt, H))         # lintel
        pos = b
    pieces.append((pos, end, 0.0, H))
    return pieces


def walls():
    """Each wall is two half-thickness layers, coloured by the room on that side,
    and also split where it passes from one room to the next."""
    links, glass = [], []
    for axis, f, start, end, openings in WALLS:
        # room boundaries along this wall, so each room gets its own colour
        cuts = sorted({v for r in ROOMS.values() for v in ((r[0], r[1]) if axis == "x" else (r[2], r[3]))})
        for a0, b0, zb, zt in wall_pieces(start, end, openings):
            pts = [a0] + [c for c in cuts if a0 < c < b0] + [b0]
            for a, b in zip(pts, pts[1:]):
                mid = (a + b) / 2
                for side in (1, -1):
                    off = f + side * T / 4
                    probe = (mid, f + side * T) if axis == "x" else (f + side * T, mid)
                    room = room_at(*probe)
                    rgb = ROOMS[room][5] if room else EXTERIOR_RGB
                    x, y = (mid, off) if axis == "x" else (off, mid)
                    sx, sy = (b - a, T / 2) if axis == "x" else (T / 2, b - a)
                    links.append(box_link(f"w{len(links)}", x, y, (zb + zt) / 2, sx, sy, zt - zb, rgb))
        for c, w, zb, zt in openings:
            if zb > 0:  # window glass: visual only, does not block light
                x, y = (c, f) if axis == "x" else (f, c)
                sx, sy = (w, 0.01) if axis == "x" else (0.01, w)
                glass.append(f'<link name="g{len(glass)}"><pose>{x} {y} {(zb + zt) / 2} 0 0 0</pose>'
                             f'<visual name="v"><cast_shadows>false</cast_shadows><transparency>0.85</transparency>'
                             f'<geometry><box><size>{sx} {sy} {zt - zb}</size></box></geometry>'
                             f'{material((0.7, 0.85, 0.95))}</visual></link>')
    return static_model("walls", links) + static_model("windows", glass)


def floors():
    links = [box_link(f"floor_{n}", (x0 + x1) / 2, (y0 + y1) / 2, 0.005,
                      x1 - x0, y1 - y0, 0.01, r[0])
             for n, (x0, x1, y0, y1, *r) in ROOMS.items()]
    return static_model("floors", links)


def ceiling():
    return static_model("ceiling", [box_link("c", 0, 0, H + 0.05, 2 * XMAX + T, 2 * YMAX + T, 0.1,
                                             (0.95, 0.95, 0.93))])


def paintings():
    links = []
    for i, (x, y, facing, w, h, z, c1, c2) in enumerate(PAINTINGS):
        sign = 1 if facing[0] == "+" else -1
        for j, (depth, scale, rgb) in enumerate(((0.03, 1.0, (0.2, 0.15, 0.1)),   # frame
                                                 (0.04, 0.9, c1),                  # canvas
                                                 (0.045, 0.5, c2))):               # motif
            d = T / 2 + depth / 2
            px, py = (x + sign * d, y) if facing[1] == "x" else (x, y + sign * d)
            sx, sy = (depth, w * scale) if facing[1] == "x" else (w * scale, depth)
            links.append(box_link(f"p{i}_{j}", px, py, z, sx, sy, h * scale, rgb, collide=False))
    return static_model("paintings", links)


def furniture():
    out, count = [], {}
    for model, x, y, yaw, *z in FURNITURE:
        count[model] = count.get(model, 0) + 1
        out.append(f"<include><uri>model://{model}</uri><name>{model}_{count[model]}</name>"
                   f"<pose>{x} {y} {z[0] if z else 0.01} 0 0 {yaw * 3.14159265 / 180:.4f}</pose><static>true</static></include>")
    # the library has no TV or rug, so add simple ones
    out.append(static_model("tv", [box_link("screen", -6.5, -1.85, 0.95, 1.4, 0.05, 0.8, (0.02, 0.02, 0.03))]))
    out.append(static_model("rug_bedroom2", [box_link("r", 7.3, 4.5, 0.012, 1.6, 2.2, 0.005, (0.15, 0.45, 0.50), False)]))
    return "\n".join(out)


def lights(p):
    out = [f'<light type="directional" name="sun"><cast_shadows>true</cast_shadows>'
           f'<pose>0 0 10 0 0 0</pose><diffuse>{rgb_str(p["sun"])}</diffuse>'
           f'<specular>0.2 0.2 0.2 1</specular><direction>{p["sun_dir"]}</direction></light>']
    for n, (x0, x1, y0, y1, *_) in ROOMS.items():  # ceiling lamps, one per ~7 m of room length
        k = math.ceil((x1 - x0) / 7)
        for i in range(k):
            x = x0 + (i + 0.5) * (x1 - x0) / k
            name = f"lamp_{n}" if k == 1 else f"lamp_{n}_{i}"
            out.append(f'<light type="point" name="{name}"><pose>{x} {(y0 + y1) / 2} {H - 0.1} 0 0 0</pose>'
                       f'<diffuse>{rgb_str(p["lamp"])}</diffuse><specular>0.1 0.1 0.1 1</specular>'
                       f'<attenuation><range>10</range><constant>0.5</constant><linear>0.1</linear>'
                       f'<quadratic>0.02</quadratic></attenuation><cast_shadows>true</cast_shadows></light>')
    return "".join(out)


def world(p):
    return f"""<?xml version="1.0"?>
<sdf version="1.9">
<world name="house">
<physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size><real_time_factor>1.0</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
<scene><ambient>{p["ambient"]} {p["ambient"]} {p["ambient"]} 1</ambient><background>{rgb_str(p["background"])}</background><shadows>true</shadows></scene>
{lights(p)}
<model name="ground"><static>true</static><link name="l">
<collision name="c"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry></collision>
<visual name="v"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>{material((0.5, 0.6, 0.4))}</visual>
</link></model>
{floors()}
{walls()}
{ceiling()}
{paintings()}
{furniture()}
</world>
</sdf>
"""


def rooms_yaml():
    lines = ["# Room bounding boxes (world frame, metres) for labelling images by robot pose"]
    for n, (x0, x1, y0, y1, *_) in ROOMS.items():
        lines.append(f"{n}: {{xmin: {x0}, xmax: {x1}, ymin: {y0}, ymax: {y1}}}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    here = Path(__file__).parent
    for name, preset in PRESETS.items():
        (here / f"house_{name}.sdf").write_text(world(preset))
    (here / "rooms.yaml").write_text(rooms_yaml())
    print("wrote house_{cloudy,sunny,night}.sdf and rooms.yaml")
