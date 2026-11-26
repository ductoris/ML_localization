# House world (ROS 2 Humble / Ignition Fortress)

Bản đồ nhà 7 phòng (21 m × 15 m) để thu ảnh cho bài toán định vị phân cấp (room classification + fine localization) theo bài báo 2407.10596.

Môi trường mô phỏng của dự án là Ubuntu 22.04, ROS 2 Humble và Ignition Fortress. Máy đã có Ignition Gazebo 6.18.0, `turtlebot4_ignition_bringup` 1.0.3 và `ros_gz_bridge`. Fortress trên máy tải được cả bốn plugin trong các file SDF 1.9 hiện có, nên dùng trực tiếp các world đã kiểm tra bên dưới. [Tài liệu TurtleBot 4 Simulator](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html)

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
- Hai ghế văn phòng quay về phía bàn và được đẩy một phần vào dưới mặt bàn. Cụm bàn gần cửa đã được dịch sâu vào phòng để chừa khoảng sàn trống sau ngưỡng cửa rộng 1,2 m.
- Đèn: `sun` và đèn trần `lamp_<phòng>`. Phòng dài có nhiều đèn: `lamp_hallway_0..2`, `lamp_living_0..1`, `lamp_kitchen_0..1`.
- `models/` – nội thất tải từ Gazebo Fuel (OpenRobotics), lưu sẵn để chạy offline.
- `rooms.yaml` – bounding box từng phòng, dùng để gán nhãn phòng cho ảnh theo pose robot.

## Chạy

Từ thư mục gốc của repo, chạy máy chủ mô phỏng không mở giao diện. Thay `cloudy` bằng `sunny` hoặc `night` để chọn ánh sáng.

```bash
source /opt/ros/humble/setup.bash
cd map
export IGN_GAZEBO_RESOURCE_PATH="$PWD/models${IGN_GAZEBO_RESOURCE_PATH:+:$IGN_GAZEBO_RESOURCE_PATH}"
ign gazebo -s -r -v 4 house_cloudy.sdf
```

Để mở giao diện trên máy có môi trường đồ họa, bỏ tùy chọn `-s`. Kiểm tra ngắn bằng cách thêm `--iterations 5000` vào lệnh trên. Trong phiên đang chạy, topic `/world/house/stats` cung cấp số bước và thời gian mô phỏng.

Vì có trần, nhìn từ trên xuống trong GUI chỉ thấy mái. Muốn xem bên trong: đưa camera GUI vào trong nhà, hoặc xóa model `ceiling` trong Entity tree (chỉ ảnh hưởng phiên đang chạy).

Sửa layout/đồ đạc: chỉnh `ROOMS` / `WALLS` / `FURNITURE` / `PAINTINGS`; sửa ánh sáng: chỉnh `PRESETS` trong `generate_house.py`, rồi chạy `python3 generate_house.py` để sinh lại cả 3 file.

## Kiểm tra giai đoạn 1

Cả ba world chạy ở chế độ server trên Fortress 6.18.0 với giới hạn 5.000 bước, thoát mã 0 và phát thống kê có thời gian mô phỏng dương. Log xác nhận tải các plugin Physics, UserCommands, SceneBroadcaster và Sensors với cấu hình Ogre2. Mesh của Chair và CoffeeTable sinh cảnh báo về hai thuộc tính vật liệu `d` và `Tr`. Giai đoạn này xác minh khởi động world và bước vật lý. Việc render ảnh, kiểm tra ánh sáng trong ảnh và điều khiển robot sẽ được kiểm tra riêng.


## Các giai đoạn triển khai

Xem [launch TurtleBot 4 và thiết kế đánh giá bảy phòng](../simulation/README.md).

| Giai đoạn | Tiêu chí kiểm tra |
| --- | --- |
| 2. TurtleBot 4 | Launch chọn được ba world, robot spawn trong hành lang, lidar có dữ liệu và vận tốc tiến giới hạn khoảng 0,3 m/s. |
| 3. Camera 360° | Thử `wideanglecamera` với Ogre2 trước. Nếu không đạt dải góc cần thiết hoặc không render được, thử bốn camera cùng tâm, đồng bộ và ghép bằng remap. Kiểm tra bốn mốc màu, kiểm tra quay 90° dịch vòng 128 px, xác nhận 5 Hz theo thời gian mô phỏng và đặt ảnh RGB 512 × 128 cạnh ảnh thật để nhóm duyệt. Chiều cao 0,8 m là giả định ban đầu. Dải góc dọc, phép chiếu và hướng panorama cần hiệu chỉnh. |
| 4. Thu thử một phòng | So khớp ảnh với ground truth Gazebo theo timestamp. Kiểm tra tên file, CSV, nhãn phòng và đọc thử bằng `ImageFolder`. |
| 5. Thu dữ liệu | Sau khi ảnh mẫu được duyệt và chạy thử đạt yêu cầu, thu đủ bảy nhãn. Baseline cloudy và validation xen kẽ, mỗi tập cách khoảng 20 cm dọc quỹ đạo. Chạy lượt riêng cho từng tập test và thống nhất cách loại ảnh ở ngưỡng cửa. |
| 6. Train và đánh giá | Dùng cấu hình mô phỏng bảy lớp và ánh xạ thư mục nhất quán giữa các tập. Lấy descriptor từ average pooling, tìm láng giềng Euclid gần nhất trong phòng dự đoán và lưu kết quả vào thư mục mô phỏng. Chạy MobileNetV3 và AlexNet trước, cân nhắc ConvNeXt Large sau khi đo bộ nhớ GPU. Báo cáo riêng theo điều kiện sáng. |

Nguồn đối chiếu gồm [bài báo Cabrera và cộng sự](https://arxiv.org/html/2407.10596v1), [code tác giả](https://github.com/juanjo-cabrera/IndoorLocalizationSingleCNN), [COLD-Freiburg](https://www.cas.kth.se/COLD/cold-freiburg.html) và [mô tả phần cứng thu ảnh COLD](https://faculty.cc.gatech.edu/~hic/Georgia-HomePage/Publishing_files/hic-papers/place-rec-icra-2008.pdf).
