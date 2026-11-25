# House world (Gazebo Harmonic / ROS 2 Jazzy)

Bản đồ nhà 7 phòng (21 m × 15 m) để thu ảnh cho bài toán định vị phân cấp (room classification + fine localization) theo bài báo 2407.10596.

```
 y=7.5  +-------------+---------+-----------+-----------+
        |  Bedroom1   |  Bath   |  Office   | Bedroom2  |
 y=1.5  +-----D-------+---D-----+----D------+----D------+
        |                    Hallway                     |
 y=-1.5 +---------D-------------------+--------D---------+
        |   Living / dining room      D     Kitchen      |
 y=-7.5 +-----------------------------+------------------+
      x=-10.5                       x=1.5             x=10.5      (D = cửa 1.2 m)
```

- `house.sdf` – world (tường cao 2.5 m), sinh ra từ `generate_house.py`.
- `models/` – nội thất tải từ Gazebo Fuel (OpenRobotics), lưu sẵn để chạy offline.
- `rooms.yaml` – bounding box từng phòng, dùng để gán nhãn phòng cho ảnh theo pose robot.
- Mỗi phòng có màu sàn + nội thất riêng và một đèn trần (`lamp_<room>`); có thêm đèn `sun`.

## Chạy

```bash
source /opt/ros/jazzy/setup.bash
cd house_world
export GZ_SIM_RESOURCE_PATH=$PWD/models:$GZ_SIM_RESOURCE_PATH
gz sim house.sdf
```

Sửa layout/đồ đạc: chỉnh `ROOMS` / `FURNITURE` trong `generate_house.py` rồi chạy `python3 generate_house.py`.

World đã có sẵn plugin `Sensors` (ogre2), chỉ cần spawn robot có camera là thu được ảnh.
