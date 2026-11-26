import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from xml.dom import minidom
from xml.etree import ElementTree

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.actions import RegisterEventHandler, SetEnvironmentVariable, Shutdown
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro
import yaml


def configure_robot(xacro_path, camera=None, collection=False):
    mappings = {"gazebo": "ignition", "namespace": "/"}
    if camera is not None:
        mappings.update({name: str(value) for name, value in camera.items()})
        mappings["panorama"] = "true"
    robot = xacro.process_file(str(xacro_path), mappings=mappings)
    for plugin in robot.getElementsByTagName("plugin"):
        name = plugin.getAttribute("name")
        if name == "ignition::gazebo::systems::Sensors":
            # The house world already runs a single Ogre2 Sensors system.
            plugin.parentNode.removeChild(plugin)
        elif name == "ignition::gazebo::systems::PosePublisher":
            # Fortress 6.18 requires both model flags to publish the top-level model.
            pose_config = minidom.parseString(
                """
                <plugin filename="libignition-gazebo-pose-publisher-system.so"
                        name="ignition::gazebo::systems::PosePublisher">
                  <publish_model_pose>true</publish_model_pose>
                  <publish_link_pose>false</publish_link_pose>
                  <publish_nested_model_pose>true</publish_nested_model_pose>
                  <use_pose_vector_msg>false</use_pose_vector_msg>
                  <update_frequency>100</update_frequency>
                </plugin>
                """
            )
            plugin.parentNode.replaceChild(robot.importNode(pose_config.documentElement, True), plugin)

    for sensor in robot.getElementsByTagName("sensor"):
        sensor_type = sensor.getAttribute("type")
        if sensor_type == "rgbd_camera" or (
            collection and sensor_type == "gpu_lidar" and sensor.getAttribute("name") != "rplidar"
        ):
            sensor.parentNode.removeChild(sensor)
        elif collection and sensor.getAttribute("name") == "rplidar":
            rate = sensor.getElementsByTagName("update_rate")[0]
            rate.firstChild.nodeValue = "10.0"
    return robot.toxml()


def shutdown_on_failure(event, _context):
    if event.returncode != 0:
        return [Shutdown(reason=f"{event.action.name} exited with code {event.returncode}")]
    return []


def add_calibration_markers(world, x, y, height):
    markers = [
        ("red", 1.15, 0, "1 0 0 1"),
        ("green", 0, 1.15, "0 1 0 1"),
        ("blue", -1.15, 0, "0 0 1 1"),
        ("magenta", 0, -1.15, "1 0 1 1"),
    ]
    for name, dx, dy, color in markers:
        marker = ElementTree.fromstring(f"""
            <model name="panorama_marker_{name}">
              <static>true</static>
              <pose>{x + dx} {y + dy} {height} 0 0 0</pose>
              <link name="marker">
                <visual name="marker">
                  <cast_shadows>false</cast_shadows>
                  <geometry><sphere><radius>0.13</radius></sphere></geometry>
                  <material><ambient>{color}</ambient><diffuse>{color}</diffuse>
                    <emissive>{color}</emissive><specular>0 0 0 1</specular></material>
                </visual>
              </link>
            </model>
        """)
        world.append(marker)


def launch_house(context):
    package_share = Path(get_package_share_directory("house_localization_sim"))
    stock_control = Path(get_package_share_directory("irobot_create_control")) / "config/control.yaml"
    map_dir = Path(LaunchConfiguration("map_dir").perform(context)).expanduser().resolve()
    world_file = map_dir / f'house_{LaunchConfiguration("world").perform(context)}.sdf'
    if not world_file.is_file() or not (map_dir / "models").is_dir():
        raise RuntimeError(f"Expected {world_file} and {map_dir / 'models'}. Set map_dir to the repository's map directory.")

    resource_paths = [
        str(map_dir / "models"),
        str(map_dir),
        str(Path(get_package_share_directory("turtlebot4_description")).parent),
        str(Path(get_package_share_directory("irobot_create_description")).parent),
    ]
    existing_paths = context.environment.get("IGN_GAZEBO_RESOURCE_PATH")
    if existing_paths:
        resource_paths.append(existing_paths)
    control_plugin_path = str(Path(get_package_prefix("ign_ros2_control")) / "lib")
    system_plugin_paths = [control_plugin_path]
    existing_plugins = context.environment.get("IGN_GAZEBO_SYSTEM_PLUGIN_PATH")
    if existing_plugins:
        system_plugin_paths.append(existing_plugins)

    camera = None
    panorama = LaunchConfiguration("panorama").perform(context) == "true"
    markers = LaunchConfiguration("calibration_markers").perform(context) == "true"
    if markers and not panorama:
        raise RuntimeError("calibration_markers requires panorama:=true")
    if panorama:
        camera_file = Path(LaunchConfiguration("camera_config").perform(context)).expanduser()
        config = yaml.safe_load(camera_file.read_text())
        camera = config["rig"]
        height_override = LaunchConfiguration("camera_height").perform(context)
        if height_override:
            camera["camera_height"] = float(height_override)
        if not 0.28 < camera["camera_height"] < 2.5 or camera["update_rate"] <= 0:
            raise ValueError("Camera height or update rate is outside the supported range")
    collection = LaunchConfiguration("collection").perform(context) == "true"
    speed = float(LaunchConfiguration("real_time_factor").perform(context))
    if not 0.1 <= speed <= 4.0:
        raise ValueError("real_time_factor must be between 0.1 and 4.0")
    robot_description = configure_robot(package_share / "urdf/turtlebot4.urdf.xacro", camera, collection)
    partition = context.environment.get("IGN_PARTITION") or f"house_localization_{uuid4().hex}"
    setup_actions = [
        SetEnvironmentVariable("IGN_PARTITION", partition),
        SetEnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", os.pathsep.join(dict.fromkeys(resource_paths))),
        SetEnvironmentVariable("IGN_GAZEBO_SYSTEM_PLUGIN_PATH", os.pathsep.join(system_plugin_paths)),
    ]

    hide_roof = LaunchConfiguration("show_roof").perform(context) == "false"
    if hide_roof or markers or speed != 1.0:
        sdf = ElementTree.parse(world_file)
        world = sdf.find("world[@name='house']")
        if world is None:
            raise RuntimeError(f"No house world found in {world_file}.")
        if speed != 1.0:
            world.find("physics/real_time_factor").text = str(speed)
        if hide_roof:
            ceiling = world.find("model[@name='ceiling']")
            if ceiling is None:
                raise RuntimeError(f"No ceiling model found in {world_file}.")
            world.remove(ceiling)
        if markers:
            x = float(LaunchConfiguration("x").perform(context))
            y = float(LaunchConfiguration("y").perform(context))
            add_calibration_markers(world, x, y, camera["camera_height"])
        preview_dir = TemporaryDirectory(prefix="house_preview_")
        world_file = Path(preview_dir.name) / world_file.name
        sdf.write(world_file, encoding="utf-8", xml_declaration=True)

        def clean_preview(_context):
            preview_dir.cleanup()

        setup_actions.append(RegisterEventHandler(OnShutdown(
            on_shutdown=[OpaqueFunction(function=clean_preview)],
        )))

    gazebo_args = ["ign", "gazebo", "-r", "-v", "3", str(world_file)]
    if LaunchConfiguration("gui").perform(context) == "false":
        gazebo_args.extend(["-s", "--headless-rendering"])

    model_scope = "/world/house/model/turtlebot4"
    lidar_topic = f"{model_scope}/link/rplidar_link/sensor/rplidar/scan"
    pose_topic = "/model/turtlebot4/pose"
    image_bridges = []
    if panorama:
        camera_topics = ("front", "left", "back", "right")
        image_bridges = [
            f"/panorama/source/{side}@sensor_msgs/msg/Image[ignition.msgs.Image"
            for side in camera_topics
        ]
        projection = {
            "source_width": camera["source_width"],
            "source_height": camera["source_height"],
            "horizontal_fov_deg": float(camera["horizontal_fov_deg"]),
            **config["panorama"],
        }
        setup_actions.append(Node(
            package="house_localization_sim",
            executable="panorama_node.py",
            name="panorama",
            parameters=[projection, {"use_sim_time": True}],
            output="screen",
            on_exit=shutdown_on_failure,
        ))
    return [
        *setup_actions,
        ExecuteProcess(
            cmd=gazebo_args,
            name="house_gazebo",
            output="screen",
            on_exit=[Shutdown(reason="Gazebo server exited")],
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description, "use_sim_time": True}],
        ),
        Node(
            package="ros_gz_sim",
            executable="create",
            name="spawn_turtlebot4",
            output="screen",
            arguments=[
                "-world", "house", "-name", "turtlebot4", "-string", robot_description,
                "-x", LaunchConfiguration("x"), "-y", LaunchConfiguration("y"),
                "-z", LaunchConfiguration("z"), "-Y", LaunchConfiguration("yaw"),
            ],
            on_exit=shutdown_on_failure,
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            name="activate_drive",
            output="screen",
            arguments=[
                "joint_state_broadcaster", "diffdrive_controller",
                "--controller-manager-timeout", "60", "--switch-timeout", "20",
                "-p", str(stock_control),
                "-p", str(package_share / "config/drive_limits.yaml"),
            ],
            on_exit=shutdown_on_failure,
        ),
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            name="house_bridge",
            output="screen",
            arguments=[
                "/world/house/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
                f"{lidar_topic}@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
                f"{pose_topic}@geometry_msgs/msg/PoseStamped[ignition.msgs.Pose",
                *image_bridges,
            ],
            remappings=[
                ("/world/house/clock", "/clock"),
                (lidar_topic, "/scan"),
                (pose_topic, "/ground_truth/pose"),
            ],
        ),
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="rplidar_tf",
            arguments=[
                "--frame-id", "rplidar_link", "--child-frame-id", "turtlebot4/rplidar_link/rplidar",
            ],
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "world", default_value="cloudy", choices=["cloudy", "sunny", "night"],
            description="House lighting preset",
        ),
        DeclareLaunchArgument(
            "map_dir", default_value=str(Path.cwd() / "map"),
            description="Directory containing the house SDF files and furniture models",
        ),
        DeclareLaunchArgument(
            "gui", default_value="false", choices=["true", "false"],
            description="Open the Ignition Gazebo GUI",
        ),
        DeclareLaunchArgument(
            "show_roof", default_value="true", choices=["true", "false"],
            description="Keep the ceiling model. Set false for a roofless preview.",
        ),
        DeclareLaunchArgument("panorama", default_value="false", choices=["true", "false"]),
        DeclareLaunchArgument(
            "camera_config",
            default_value=str(Path(get_package_share_directory("house_localization_sim")) / "config/camera.yaml"),
        ),
        DeclareLaunchArgument("camera_height", default_value="", description="Override nominal camera height in metres"),
        DeclareLaunchArgument("calibration_markers", default_value="false", choices=["true", "false"]),
        DeclareLaunchArgument("collection", default_value="false", choices=["true", "false"],
                              description="Disable auxiliary GPU lidar sensors. Keep the RPLIDAR."),
        DeclareLaunchArgument("real_time_factor", default_value="1.0",
                              description="Requested simulation seconds per wall second"),
        DeclareLaunchArgument("x", default_value="0.0", description="Spawn x in metres"),
        DeclareLaunchArgument("y", default_value="0.0", description="Spawn y in metres"),
        DeclareLaunchArgument("z", default_value="0.02", description="Spawn z in metres"),
        DeclareLaunchArgument("yaw", default_value="0.0", description="Spawn yaw in radians"),
        OpaqueFunction(function=launch_house),
    ])
