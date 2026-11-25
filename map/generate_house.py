#!/usr/bin/env python3
"""Generate a 7-room house world (house.sdf) for Gazebo Harmonic.

Walls/floors are primitives; furniture are Gazebo Fuel models stored in ./models
(run with GZ_SIM_RESOURCE_PATH pointing at that folder).

Layout (top view, metres, origin at house centre, x -> east, y -> north):

 y=7.5  +-------------+---------+-----------+-----------+
        |  Bedroom1   |  Bath   |  Office   | Bedroom2  |
 y=1.5  +-----D-------+---D-----+----D------+----D------+
        |                    Hallway                     |
 y=-1.5 +---------D-------------------+--------D---------+
        |   Living / dining room      D     Kitchen      |
 y=-7.5 +-----------------------------+------------------+
      x=-10.5                       x=1.5             x=10.5
"""
from pathlib import Path

H = 2.5     # wall height
T = 0.15    # wall thickness
DOOR = 1.2  # door opening width
XMAX, YMAX = 10.5, 7.5  # half extents of the house

# name: (xmin, xmax, ymin, ymax, floor rgb)
ROOMS = {
    "bedroom1": (-10.5, -3.75, 1.5, 7.5, (0.55, 0.40, 0.25)),   # wood
    "bathroom": (-3.75, 0.0, 1.5, 7.5, (0.75, 0.85, 0.90)),     # light blue tile
    "office":   (0.0, 5.25, 1.5, 7.5, (0.35, 0.35, 0.40)),      # grey carpet
    "bedroom2": (5.25, 10.5, 1.5, 7.5, (0.80, 0.65, 0.70)),     # pink carpet
    "hallway":  (-10.5, 10.5, -1.5, 1.5, (0.85, 0.80, 0.70)),   # beige
    "living":   (-10.5, 1.5, -7.5, -1.5, (0.45, 0.30, 0.20)),   # dark wood
    "kitchen":  (1.5, 10.5, -7.5, -1.5, (0.90, 0.90, 0.85)),    # white tile
}

WALL_RGB = (0.92, 0.90, 0.85)

# (Fuel model folder in ./models, x, y, yaw in degrees[, z])
FURNITURE = [
    # Bedroom 1
    ("Bed", -7.5, 6.1, 0), ("LampAndStand", -9.3, 7.0, 0), ("LampAndStand", -5.7, 7.0, 0),
    ("WhiteCabinet", -10.15, 4.0, 90), ("Bookshelf", -9.3, 1.85, 180), ("Chair", -4.4, 2.4, 135),
    # Bathroom
    ("Bathtub", -1.9, 6.95, 0), ("Toilet", -3.25, 4.5, 0), ("BathroomSink", -0.1, 4.0, -90, 0.5),
    # Office
    ("Office_Desk", 2.6, 7.0, -90), ("OfficeChairBlack", 2.6, 6.1, 0),
    ("Bookshelf", 4.95, 3.6, -90), ("Bookshelf", 4.95, 4.6, -90), ("Cabinet", 0.4, 4.0, 90),
    ("Office_Desk", 2.6, 3.4, 90), ("OfficeChairBlack", 2.6, 2.6, 180),
    # Bedroom 2
    ("Bed", 9.0, 6.1, 0), ("LampAndStand", 7.3, 7.0, 0), ("WhiteCabinet", 10.15, 3.0, -90),
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


def material(rgb):
    r, g, b = rgb
    return (f"<material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse>"
            f"<specular>0.1 0.1 0.1 1</specular></material>")


def box_link(name, x, y, z, sx, sy, sz, rgb):
    """A link with one box; (x, y, z) is the box centre."""
    geom = f"<geometry><box><size>{sx} {sy} {sz}</size></box></geometry>"
    return (f'<link name="{name}"><pose>{x} {y} {z} 0 0 0</pose>'
            f'<collision name="c">{geom}</collision>'
            f'<visual name="v">{geom}{material(rgb)}</visual></link>')


def static_model(name, links):
    return f'<model name="{name}"><static>true</static>{"".join(links)}</model>'


def wall_segments(axis, fixed, start, end, doors):
    """Split a straight wall into box links, leaving gaps at door centres."""
    cuts = [start]
    for c in sorted(doors):
        cuts += [c - DOOR / 2, c + DOOR / 2]
    cuts.append(end)
    out = []
    for a, b in zip(cuts[::2], cuts[1::2]):
        mid, length = (a + b) / 2, b - a
        if axis == "x":   # wall runs along x at y = fixed
            out.append((mid, fixed, length, T))
        else:             # wall runs along y at x = fixed
            out.append((fixed, mid, T, length))
    return out


def walls():
    e = T / 2  # extend outer walls so corners close
    segs = []
    # outer walls
    segs += wall_segments("x", YMAX, -XMAX - e, XMAX + e, [])
    segs += wall_segments("x", -YMAX, -XMAX - e, XMAX + e, [])
    segs += wall_segments("y", -XMAX, -YMAX, YMAX, [])
    segs += wall_segments("y", XMAX, -YMAX, YMAX, [])
    # hallway walls with doors into each room
    segs += wall_segments("x", 1.5, -XMAX, XMAX, [-7.1, -1.9, 2.6, 7.9])
    segs += wall_segments("x", -1.5, -XMAX, XMAX, [-4.5, 6.0])
    # partitions between north rooms
    for x in (-3.75, 0.0, 5.25):
        segs += wall_segments("y", x, 1.5, YMAX, [])
    # living / kitchen partition with a door
    segs += wall_segments("y", 1.5, -YMAX, -1.5, [-4.5])
    links = [box_link(f"wall_{i}", x, y, H / 2, sx, sy, H, WALL_RGB)
             for i, (x, y, sx, sy) in enumerate(segs)]
    return static_model("walls", links)


def floors():
    links = [box_link(f"floor_{n}", (x0 + x1) / 2, (y0 + y1) / 2, 0.005,
                      x1 - x0, y1 - y0, 0.01, rgb)
             for n, (x0, x1, y0, y1, rgb) in ROOMS.items()]
    return static_model("floors", links)


def furniture():
    out, count = [], {}
    for model, x, y, yaw, *z in FURNITURE:
        count[model] = count.get(model, 0) + 1
        out.append(f"<include><uri>model://{model}</uri><name>{model}_{count[model]}</name>"
                   f"<pose>{x} {y} {z[0] if z else 0.01} 0 0 {yaw * 3.14159265 / 180:.4f}</pose><static>true</static></include>")
    # the library has no TV, so put a flat black screen on the TV stand
    out.append(static_model("tv", [box_link("screen", -6.5, -1.85, 0.95, 1.4, 0.05, 0.8, (0.02, 0.02, 0.03))]))
    return "\n".join(out)


def lights():
    out = ['<light type="directional" name="sun"><cast_shadows>true</cast_shadows>'
           '<pose>0 0 10 0 0 0</pose><diffuse>0.6 0.6 0.6 1</diffuse>'
           '<specular>0.2 0.2 0.2 1</specular><direction>-0.5 0.2 -0.9</direction></light>']
    for n, (x0, x1, y0, y1, _) in ROOMS.items():  # one ceiling lamp per room
        out.append(f'<light type="point" name="lamp_{n}"><pose>{(x0 + x1) / 2} {(y0 + y1) / 2} {H - 0.1} 0 0 0</pose>'
                   f'<diffuse>0.5 0.5 0.45 1</diffuse><specular>0.1 0.1 0.1 1</specular>'
                   f'<attenuation><range>10</range><constant>0.5</constant><linear>0.1</linear>'
                   f'<quadratic>0.02</quadratic></attenuation><cast_shadows>false</cast_shadows></light>')
    return "".join(out)


def world():
    return f"""<?xml version="1.0"?>
<sdf version="1.9">
<world name="house">
<physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size><real_time_factor>1.0</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
<scene><ambient>0.4 0.4 0.4 1</ambient><background>0.7 0.7 0.7 1</background><shadows>true</shadows></scene>
{lights()}
<model name="ground"><static>true</static><link name="l">
<collision name="c"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry></collision>
<visual name="v"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>{material((0.5, 0.6, 0.4))}</visual>
</link></model>
{floors()}
{walls()}
{furniture()}
</world>
</sdf>
"""


def rooms_yaml():
    lines = ["# Room bounding boxes (world frame, metres) for labelling images by robot pose"]
    for n, (x0, x1, y0, y1, _) in ROOMS.items():
        lines.append(f"{n}: {{xmin: {x0}, xmax: {x1}, ymin: {y0}, ymax: {y1}}}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    here = Path(__file__).parent
    (here / "house.sdf").write_text(world())
    (here / "rooms.yaml").write_text(rooms_yaml())
    print("wrote house.sdf and rooms.yaml")
