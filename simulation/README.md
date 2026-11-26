# Mô phỏng định vị TurtleBot 4

## Terminal 1 — Build và khởi chạy

Dùng Ubuntu 22.04 với ROS 2 Humble, Ignition Fortress và `ros-humble-turtlebot4-simulator`. Mở Terminal 1 tại thư mục gốc của repo.

```bash
source /opt/ros/humble/setup.bash

colcon --log-base simulation/build/log build \
  --base-paths simulation/house_localization_sim \
  --build-base simulation/build \
  --install-base simulation/build/install \
  --symlink-install

source simulation/build/install/local_setup.bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch house_localization_sim house.launch.py world:=cloudy
```

Chọn `world:=sunny` hoặc `world:=night` để đổi ánh sáng. Mặc định launch chạy server với Ogre2 headless. Dùng `gui:=true` trên máy có môi trường đồ họa. Khi gọi từ thư mục khác, đặt `map_dir` thành đường dẫn tới thư mục `map/` của repo. Tọa độ spawn mặc định là `x=0`, `y=0` trong hành lang. Các đối số `x`, `y`, `z` dùng mét và `yaw` dùng radian.

Để quan sát robot từ trên cao, dừng phiên cũ bằng `Ctrl+C` rồi chạy trong Terminal 1 đã source thư mục build.

```bash
ros2 launch house_localization_sim house.launch.py world:=cloudy gui:=true show_roof:=false
```

`show_roof:=false` bỏ model mái trong bản world tạm của phiên đó. Dùng thiết lập mặc định `show_roof:=true` khi thu ảnh để giữ điều kiện chiếu sáng đã thiết kế. Trong Gazebo, chọn `turtlebot4` trong **Entity Tree** để tìm robot. Nếu chỉ cần vị trí, lệnh đọc `/ground_truth/pose` ở Terminal 2 dùng được khi chạy headless.

Mỗi lần launch tự tạo một `IGN_PARTITION` nếu biến này chưa được đặt. Điều này tránh việc một server Gazebo cũ nhận nhầm lệnh spawn cho world `house` của phiên mới. Khi chạy nhiều phiên đồng thời, đặt `ROS_DOMAIN_ID` khác nhau cho mỗi phiên và dùng cùng giá trị ở hai terminal của phiên đó.

Robot dùng mô hình TurtleBot 4 Standard và bộ điều khiển vi sai Create 3, spawn trực tiếp trong hành lang. Cầu ROS truyền `/clock`, `/scan` và pose thật của mô hình ở `/ground_truth/pose`. OAK-D đã tắt sensor RGB-D trong mô phỏng, còn thân camera vẫn thuộc mô hình để kiểm tra che khuất ở giai đoạn 3. RPLIDAR giữ cấu hình gốc. Lệnh tiến/lùi được giới hạn ở ±0,30 m/s, gia tốc tuyến tính ở ±0,35 m/s². Bộ điều khiển dùng timeout lệnh mặc định của TurtleBot 4 là 0,5 giây theo thời gian mô phỏng.

## Terminal 2 — Kiểm tra lidar, pose và điều khiển

Giữ Terminal 1 chạy rồi mở terminal mới. Lệnh cuối dùng gói `teleop_twist_keyboard` để điều khiển bằng bàn phím.

```bash
source /opt/ros/humble/setup.bash

ros2 topic echo --once --qos-reliability best_effort /scan --field header
ros2 topic echo --once /ground_truth/pose

ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -r cmd_vel:=/diffdrive_controller/cmd_vel_unstamped
```

Pose ban đầu có `frame_id: house` và `x`, `y` gần 0. Trong terminal điều khiển, nhấn `i` để tiến, `j` hoặc `l` để quay và `k` để dừng. Nhấn `Ctrl+C` ở Terminal 1 để tắt mô phỏng.

## Kiểm tra giai đoạn 2

Bản thử chạy headless với Mesa software rendering (`LIBGL_ALWAYS_SOFTWARE=1`). Trên cả ba world, robot spawn gần `(0,0)`, có pose thật trong hệ `house` và RPLIDAR phát scan 640 tia. Trong world cloudy, gửi lệnh 0,80 m/s và đo vận tốc đoạn ổn định từ pose thật được 0,300 m/s. Robot đi khoảng 0,72 m, sau đó kiểm tra riêng lệnh quay tại chỗ và xác nhận robot ngừng quay sau khi ngừng gửi lệnh. Camera 360° và cột camera thuộc giai đoạn 3.

## Giai đoạn 3 — Chạy và xem ảnh panorama

Build lại package bằng lệnh ở Terminal 1 để cài hai node Python. Chạy lại launch với camera, giữ mái để xem ánh sáng đúng với world. Dùng `LP_NUM_THREADS=4` để giới hạn luồng render Mesa khi chạy trên CPU.

```bash
LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=4 ros2 launch house_localization_sim house.launch.py \
  world:=cloudy panorama:=true
```

Ở Terminal 2, chạy từ thư mục gốc repo.

```bash
source /opt/ros/humble/setup.bash
source simulation/build/install/local_setup.bash
ros2 run house_localization_sim save_panorama.py /tmp/panorama.png
```

Thêm `calibration_markers:=true` vào lệnh launch để đặt bốn mốc quanh điểm spawn. Ở yaw 0, mốc xanh lá ở biên trái/phải, đỏ ở cột 128, tím ở cột 256 và xanh dương ở cột 384. Khi yaw tăng 90° theo hệ tọa độ Gazebo, nội dung dịch vòng sang phải 128 pixel.

Tham số nằm trong [camera.yaml](house_localization_sim/config/camera.yaml). Có thể dùng `camera_config:=` với một bản YAML hiệu chỉnh hoặc `camera_height:=` để thử chiều cao danh định khác. Node phát ảnh `rgb8` 512 × 128 trên `/panorama/image_raw` và giữ timestamp chung của cả bốn ảnh nguồn. Tần số 5 Hz tính theo đồng hồ mô phỏng.

Trong bài thử A trên Fortress 6.18.0 và Ogre2, SDF chứa camera hướng lên 640 × 480 cùng lens tùy biến. Camera pinhole đối chứng nhận được ảnh, còn world báo loại cảm biến góc rộng chưa được hỗ trợ và không phát topic ảnh của A. Bản triển khai vì vậy dùng bốn ảnh pinhole 320 × 320 cùng tâm quang học, cách nhau 90°, HFOV mỗi mắt 110°. OpenCV chiếu các tia trực tiếp lên panorama và nội suy theo góc trong vùng chồng. Nguồn ảnh mô phỏng ở cách B gồm bốn ảnh pinhole. [Bảng hỗ trợ cảm biến của Fortress](https://gazebosim.org/docs/fortress/comparison/)


### Kết quả kiểm tra để duyệt ảnh

- Đã điều chỉnh dải góc dọc từ +17°/−43° thành **+19°/−41°**, đặt đường chân trời danh định gần hàng 40. Đã chụp thử ở hai độ cao 0,80 m và 0,86 m. Giữ 0,80 m làm giá trị ban đầu vì tỉ lệ sàn và trần còn phụ thuộc bề rộng phòng, nội thất và phép chiếu gốc. Các góc và chiều cao này là tham số mô phỏng.
- Bộ remap hiện phủ toàn bộ 360° với vùng trộn 3° mỗi phía của bốn đường nối. Phép thử kiểm tra các tia lấy mẫu nằm trong ảnh nguồn, ảnh không có cột trống và mốc xanh lá nối qua biên trái/phải. Ảnh có thể còn vệt bóng mảnh quanh đường nối. Bốn tâm mốc dịch **127,66–128,17 pixel** khi yaw tăng 90°, và so khớp vòng theo số pixel nguyên cho kết quả **+128 pixel**. [Ảnh bốn mốc tại yaw 0° và 90°](samples/panorama-yaw-check.png)
- Đã đo 12 panorama liên tiếp sau khởi động, cách nhau đúng 200 ms theo đồng hồ Gazebo. Từng panorama chỉ được ghép khi bốn ảnh có cùng timestamp. Lệnh `save_panorama.py` đã lưu được PNG RGB 512 × 128.
- Khi gắn cột, xe đạt khoảng 0,300 m/s trong đoạn thử hành lang, quay được tại chỗ và dừng khi ngừng gửi lệnh. Độ nghiêng lớn nhất của thân xe trong lượt thử khoảng 5,3°. Cột gắn với khung bằng khớp cố định. Những ảnh trên được chụp khi xe đứng yên.

## Giai đoạn 4 — Ánh sáng và lượt thu thử


World sunny dùng nắng trực tiếp mạnh hơn từ đông bắc để tạo vệt sáng trên sàn và bóng đổ. World cloudy dùng ánh sáng đều hơn. Trong cặp ảnh thử ở cùng pose văn phòng trước khi dời bàn ghế, khoảng 6,2% điểm ảnh chênh hơn 25 mức sáng trên thang 8-bit. Màu sàn, tường và vài điểm nhấn ở tầm camera đã được chỉnh để phân biệt phòng. Cửa và biên bảy phòng được dùng chung cho ba world.

Build lại theo mục Terminal 1. Trong Terminal 1, từ gốc repo và sau khi source bản build, chạy camera ở điểm đầu hành lang.

```bash
LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=3 ros2 launch house_localization_sim house.launch.py \
  world:=cloudy panorama:=true x:=-6
```

Trong Terminal 2, từ gốc repo, chọn một thư mục đầu ra mới bên dưới `data/`.

```bash
source /opt/ros/humble/setup.bash
source simulation/build/install/local_setup.bash
ros2 run house_localization_sim collect_pilot.py --output data/sim-pilot-new
ros2 run house_localization_sim check_sim_dataset.py data/sim-pilot-new --expected-rooms hallway
```

Để kiểm tra bằng torchvision, chạy từ môi trường Python có PyTorch và torchvision.

```bash
python simulation/house_localization_sim/scripts/check_sim_dataset.py \
  data/sim-pilot-new --expected-rooms hallway --imagefolder
```

Pilot chạy theo [hai waypoint trong hành lang](house_localization_sim/config/hallway_pilot.yaml), lấy ảnh sau mỗi mốc khoảng 0,20 m và ghi PNG RGB 512 × 128 cùng `metadata.csv`. Tên file dùng timestamp mô phỏng theo nano giây, x và y theo mét, yaw theo radian. CSV ghi cả hai timestamp pose Gazebo bao quanh ảnh để kiểm tra phép nội suy. Bộ kiểm tra chừa 15 cm quanh biên phòng và từ chối đường dẫn chứa `_x`, `_y`, `_a` ở phần thư mục vì bộ đọc cũ tách tọa độ từ đường dẫn đầy đủ. Thư mục gốc của bộ train sau này cần dấu `/` cuối khi đưa vào cấu hình cũ.

Lượt đã kiểm tra tạo **15 ảnh hallway** trong `data/sim-pilot/`. Khoảng cách dọc quỹ đạo min/trung vị/max là **0,156/0,208/0,208 m**, còn khoảng giữa hai pose bao quanh từng ảnh là 10 ms. Cả 15 ảnh đọc được qua `ImageFolder` và `ToTensor()`. Toàn bộ cấu hình train và các tập dữ liệu bảy phòng thuộc các giai đoạn sau.

## Giai đoạn 5 — Thu đủ bảy phòng

Hai [tuyến waypoint](house_localization_sim/config/routes.yaml) đều đi xuyên qua các ngưỡng cửa của nhà. Trong văn phòng, cụm bàn gần cửa được dịch sâu vào phòng và cả hai ghế được đẩy một phần vào dưới mặt bàn. Robot đi thẳng qua cửa trước khi rẽ sang phía tây ở lượt train và phía đông ở ba lượt test. Lượt `training` chạy trong world cloudy và chia các mốc lấy mẫu cách khoảng 10 cm thành train và validation xen kẽ. Mỗi tập vì vậy cách khoảng 20 cm dọc tuyến. Ba lượt test khởi động Gazebo riêng và dùng chung tuyến test để đối chiếu ánh sáng. Tập test lấy các ảnh khi robot dịch chuyển, từ camera phát 5 Hz. Lượt thu giữ mái và lidar chính, giảm tần số lidar chính xuống 10 Hz và tắt các lidar phụ để giảm tải render. Mỗi ảnh lưu pose thật trong hệ `house` và hai timestamp pose bao quanh timestamp ảnh.

Từ gốc repo, build và source theo mục Terminal 1. Có thể đặt `LIBGL_ALWAYS_SOFTWARE=1` nếu cần render bằng CPU.

```bash
python3 map/generate_house.py
LP_NUM_THREADS=3 ros2 run house_localization_sim capture_sim_runs.py --output data/sim-runs-office
ros2 run house_localization_sim assemble_sim_dataset.py data/sim-runs-office data/sim-seven-office
ros2 run house_localization_sim check_sim_dataset.py data/sim-seven-office --full
```

Dùng `--run training`, `--run TestCloudy`, `--run TestSunny` hoặc `--run TestNight` để thu một lượt. Các lượt đã hoàn tất được đánh dấu trong thư mục staging. Bộ ghép từ chối lượt thiếu dấu hoàn tất và chỉ xuất bộ cuối khi cả năm tập đều đủ bảy lớp. Bộ ghép bỏ ảnh test có nội dung PNG trùng hoặc pose cách ảnh train/validation dưới 7,5 cm và lệch yaw dưới 0,15 rad. `collection-report.json` ghi số ảnh theo tập, theo phòng và số ảnh bị lọc. Thêm `--imagefolder` khi chạy trình kiểm tra bằng môi trường Python có torchvision.

### Bộ dữ liệu theo bố trí văn phòng

Bản bố trí này dùng các lượt thu trong `data/sim-runs-office/` và bộ dữ liệu `data/sim-seven-office/`. Log thu đã công bố nằm ở `results/office/capture.log`. Trong bộ dữ liệu mới, `coverage.png` hiển thị tọa độ ảnh trên sơ đồ bảy phòng và `collection-report.json` ghi số ảnh sau lọc.

| Phòng | TrainingBaseline | Validation | TestCloudy | TestSunny | TestNight |
| --- | ---: | ---: | ---: | ---: | ---: |
| bathroom | 28 | 28 | 105 | 105 | 105 |
| bedroom1 | 14 | 14 | 54 | 55 | 55 |
| bedroom2 | 15 | 14 | 71 | 71 | 71 |
| hallway | 139 | 139 | 518 | 517 | 518 |
| kitchen | 45 | 46 | 185 | 184 | 184 |
| living | 20 | 20 | 76 | 74 | 76 |
| office | 30 | 30 | 109 | 110 | 110 |
| **Tổng** | **291** | **291** | **1.118** | **1.116** | **1.119** |

Cả 3.935 ảnh là PNG RGB 512 × 128 và đọc được qua `ImageFolder`. Khoảng giữa hai pose thật bao quanh timestamp ảnh tối đa 10 ms. Kiểm tra xác nhận robot đi qua cửa văn phòng theo cả hai hướng trong mỗi lượt. Ảnh train, validation và test đã được đối chiếu bằng SHA-256, đồng thời pose test được kiểm tra theo ngưỡng chống trùng với train và validation.

## Thiết kế đánh giá trên bảy phòng

Các nhãn lấy từ [`map/rooms.yaml`](../map/rooms.yaml). Thứ tự của `ImageFolder` là `bathroom`, `bedroom1`, `bedroom2`, `hallway`, `kitchen`, `living`, `office`. Mỗi tập có đủ bảy thư mục này. Ground truth là pose Gazebo ghép theo timestamp mô phỏng của ảnh. Gán phòng theo `(x,y)` của robot, loại pose không có nhãn duy nhất và ảnh trong dải 15 cm tính từ mặt phẳng cửa khi đi qua ngưỡng. Đây là ngưỡng đề xuất cho nhà mô phỏng.

| Tập | Dữ liệu |
| --- | --- |
| `TrainingBaseline` | Lượt cloudy qua cả bảy phòng. Lấy một ảnh theo mỗi khoảng 0,20 m dọc quỹ đạo. Dùng tập này làm visual map cho mọi model. |
| `Validation` | Cùng lượt cloudy, lấy các điểm ở giữa hai điểm baseline liên tiếp theo độ dài quỹ đạo. Mỗi tập có khoảng cách mẫu khoảng 0,20 m. Dùng validation để chọn checkpoint. |
| `TestCloudy`, `TestNight`, `TestSunny` | Ba lượt chạy độc lập, phát lại cùng bộ waypoint test qua bảy phòng để đối chiếu tác động của ánh sáng. Bộ waypoint test lệch khỏi tuyến baseline. Ghi ảnh ở 5 Hz và bỏ các khung liên tiếp có pose lặp khi robot đứng yên. |

Kiểm tra dữ liệu trước khi train bằng số ảnh từng phòng, kích thước RGB 512 × 128, sai lệch thời gian ghép pose, khoảng cách lấy mẫu và ảnh trùng giữa train với test. So cả nội dung ảnh và pose gần trùng giữa các lượt, nhất là ở cửa và điểm giao quỹ đạo. Ghi số ảnh sau lọc theo tập. Số ảnh phụ thuộc chiều dài quỹ đạo trong nhà.

- Train MobileNetV3 và AlexNet với ImageNet pretrained, đầu ra bảy lớp, cross-entropy, SGD với learning rate 0,001 và momentum 0,9. Dùng 30 epoch và batch 16 làm mốc. Chọn checkpoint theo validation accuracy. Ghi seed, kích thước batch, mixed precision nếu dùng và thiết bị đo.
- Chạy `noDA` làm mốc, sau đó DA1–DA6 trên ảnh train. DA6 dịch vòng panorama theo góc quay. Mọi biến thể dùng cùng tập validation, tập test và visual map từ `TrainingBaseline`.
- Với mỗi khung hình hiện tại, đầu vào suy luận là ảnh panorama. Tầng 1 trả về `room_pred` trong bảy phòng. Tầng 2 lấy descriptor từ average pooling, tìm ảnh gần nhất theo khoảng cách Euclid trong visual map của phòng dự đoán và trả về `(x_est, y_est)` theo mét trong hệ tọa độ `house`. Hai tọa độ ước lượng đến từ pose đã lưu của ảnh tham chiếu thuộc `TrainingBaseline`. Pose Gazebo ở timestamp hiện tại cung cấp `room_gt` và `(x_gt, y_gt)` để đánh giá, kể cả khi CNN dự đoán nhầm phòng. Lưu yaw trong metadata để theo dõi hướng khi thu ảnh. Đầu ra vị trí của paper gồm hai tọa độ. [Phương pháp hai tầng của paper](https://arxiv.org/html/2407.10596v1#S3.SS1)
- Cho mỗi model, biến thể và điều kiện sáng, báo cáo số ảnh test, độ chính xác phòng, MAE của khoảng cách phẳng `hypot(x_pred - x, y_pred - y)` theo mét, phương sai của khoảng cách theo m², RMSE theo mét và độ trễ mỗi ảnh theo mili giây. Đo độ trễ với batch 1 sau warm-up, tính từ forward đến khi tìm xong láng giềng, đồng bộ CUDA nếu dùng GPU. Kèm độ chính xác theo từng phòng và ma trận nhầm lẫn 7 × 7.

Ảnh, cấu hình bảy lớp, trọng số và kết quả thí nghiệm sẽ dùng đường dẫn dành cho mô phỏng. Nhà bảy phòng, TurtleBot 4 và pose thật từ Gazebo là các khác biệt so với thí nghiệm COLD-Freiburg. Báo cáo so sánh các model và điều kiện sáng trong nhà mô phỏng. [Bài báo gốc](https://arxiv.org/html/2407.10596v1)

## Giai đoạn 6 — Train và đánh giá hai tầng

Dùng môi trường Python có PyTorch, torchvision, NumPy, Pillow và PyYAML. Chạy từ gốc repo. Cấu hình của thí nghiệm mô phỏng nằm trong [config/simulation.yaml](../config/simulation.yaml). Tạo DA một lần sau khi ghép tập dữ liệu mới.

```bash
python -m train.augment_sim --dataset data/sim-seven-office
```

Khi đã có đủ `TrainingDA/DA1` đến `TrainingDA/DA6`, chạy huấn luyện và tổng hợp kết quả.

```bash
python -m train.sim_experiment --variants noDA --best-only
python -m train.sim_experiment --variants DA1 DA2 DA3 DA4 DA5 DA6 --best-only
```

Cấu hình thử ConvNeXt Large `noDA` trên GPU 6 GiB dùng batch 2 và chỉ lưu trọng số tốt nhất để giảm dung lượng checkpoint.

```bash
python -m train.sim_experiment --models convnext_large --variants noDA --batch-size 2 --best-only
python -m train.report_sim
```

Có thể tạo ảnh DA và lưu checkpoint trên phân vùng khác để tiết kiệm phân vùng gốc. `train.augment_sim --output` nhận một thư mục mới hoặc chỉ chứa các DA khác. Nếu dùng vị trí đó, tạo symlink `data/sim-seven-office/TrainingDA` trỏ tới thư mục sinh ảnh trước khi chạy train. Dùng `--checkpoints` để chọn thư mục lưu trọng số và dùng lại cùng đường dẫn cho từng cấu hình khi chạy lại lệnh. Các lượt hoàn tất có `metrics.json`. `--best-only` lưu trọng số tốt nhất. Nếu cần phục hồi một lượt đang chạy dở, bỏ cờ này ngay từ lúc khởi động lượt đó để ghi thêm trạng thái huấn luyện ở epoch đầu và mỗi năm epoch.

Mỗi biến thể giữ toàn bộ ảnh gốc và thêm ảnh biến đổi thuộc cùng tập cloudy. DA1/DA2 thêm đốm sáng/bóng tròn. DA3 chỉnh sáng và tối. DA4 dùng pivot 64 trong công thức tương phản. DA5 chỉnh kênh saturation trong HSV. DA6 dịch vòng panorama theo góc từ 10° đến 350°, bước 10°. Các mức chỉnh và cách bố trí đốm chưa được paper mô tả đầy đủ được ghi trong [mã sinh DA](../train/augment_sim.py).

MobileNetV3 Large và AlexNet bắt đầu từ checkpoint ImageNet V1. Mỗi lượt chạy 30 epoch, batch 16, SGD với learning rate 0,001, momentum 0,9 và cross-entropy. Train dùng mixed precision trên CUDA. Đánh giá dùng FP32, batch 1 và lấy descriptor ở đầu ra `avgpool`. Độ trễ tính từ lúc forward model đến khi chọn được ảnh tham chiếu, sau warm-up và khi tensor đầu vào đã ở trên GPU. Cả ba tập test luôn dùng cùng bộ ảnh đã thu ở giai đoạn 5. [Bài báo, mục 3 và 4](https://arxiv.org/html/2407.10596v1#S3)

Kết quả khi chạy lại được ghi vào `data/sim-results-office/`. Mỗi lượt có `history.json`, `metrics.json` (gồm ma trận nhầm lẫn 7 × 7) và `predictions.csv` (gồm phòng dự đoán, tọa độ dự đoán và ground truth theo từng ảnh). `summary.csv` và `summary.md` tổng hợp các lượt đã hoàn tất. `room-accuracy.csv` ghi số ảnh và accuracy theo từng phòng. Lệnh sau trả về phòng và tọa độ ước lượng từ một ảnh RGB panorama.

```bash
python -m eval.predict_sim /path/to/panorama.png \
  results/office/models/mobilenet_v3_large-DA4.pt
```

[Báo cáo kết quả với bố trí văn phòng mới](RESULTS-OFFICE.md) · [Nhật ký thay đổi bố trí văn phòng](RESULTS.md)
