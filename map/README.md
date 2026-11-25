# House world (Gazebo Harmonic / ROS 2 Jazzy)

Bản đồ nhà 7 phòng (21 m × 15 m) để thu ảnh cho bài toán định vị phân cấp (room classification + fine localization) theo bài báo 2407.10596.

```
 y=7.5  +--------W----+---w-----+----W------+-W---------+
        |  Bedroom1   |  Bath   |  Office   | Bedroom2  |
 y=1.5  +-----D-------+---D-----+----D------+----D------+
        |                    Hallway                     |
 y=-1.5 +---------D-------------------+--------D---------W
        |   Living / dining room      D     Kitchen      |
 y=-7.5 +----W----------W-------------+-------W----------+
      x=-10.5                       x=1.5             x=10.5     (D = cửa 1.2 m, W = cửa sổ)
```

7 nhãn phòng: `bedroom1`, `bathroom`, `office`, `bedroom2`, `hallway`, `living`, `kitchen`.

- `house_cloudy.sdf`, `house_sunny.sdf`, `house_night.sdf` – cùng một world với 3 điều kiện ánh sáng như bộ COLD trong bài báo, sinh ra từ `generate_house.py`:
  - cloudy: ánh sáng dịu, nắng yếu, đèn trần bật nhẹ.
  - sunny: nắng mạnh chiếu xiên qua cửa sổ tạo vệt sáng và bóng đổ, trời xanh.
  - night: trời tối, chỉ có đèn trần (ánh vàng).
- Nhà có trần (cao 2.5 m), nên nắng chỉ vào được qua cửa sổ (kính trong, không chặn sáng).
- Mỗi phòng có màu tường, màu sàn, tranh treo tường và nội thất riêng. Hai phòng ngủ khác nhau ở màu tường, vị trí giường (tường bắc / tường đông) và đồ riêng (giá sách + ghế bành / thảm + bàn học).
- Đèn: `sun` và đèn trần `lamp_<phòng>`. Phòng dài có nhiều đèn: `lamp_hallway_0..2`, `lamp_living_0..1`, `lamp_kitchen_0..1`.
- `models/` – nội thất tải từ Gazebo Fuel (OpenRobotics), lưu sẵn để chạy offline.
- `rooms.yaml` – bounding box từng phòng, dùng để gán nhãn phòng cho ảnh theo pose robot.

## Chạy

```bash
source /opt/ros/jazzy/setup.bash
cd house_world
export GZ_SIM_RESOURCE_PATH=$PWD/models:$GZ_SIM_RESOURCE_PATH
gz sim house_cloudy.sdf   # hoặc house_sunny.sdf / house_night.sdf
```

Vì có trần, nhìn từ trên xuống trong GUI chỉ thấy mái. Muốn xem bên trong: đưa camera GUI vào trong nhà, hoặc xóa model `ceiling` trong Entity tree (chỉ ảnh hưởng phiên đang chạy).

Sửa layout/đồ đạc: chỉnh `ROOMS` / `WALLS` / `FURNITURE` / `PAINTINGS`; sửa ánh sáng: chỉnh `PRESETS` trong `generate_house.py`, rồi chạy `python3 generate_house.py` để sinh lại cả 3 file.

World đã có sẵn plugin `Sensors` (ogre2), chỉ cần spawn robot có camera là thu được ảnh.
