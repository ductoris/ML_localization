# Định vị robot trong nhà bằng panorama 360° và Gazebo

Dự án nhóm mô phỏng TurtleBot 4 trong nhà bảy phòng. Từ mỗi ảnh panorama, mô hình dự đoán phòng rồi tìm ảnh tham chiếu gần nhất trong phòng đó để ước lượng tọa độ robot `(x, y)` theo mét trong hệ `house`.

## Dữ liệu và kết quả của nhóm

- [Bộ dữ liệu Gazebo](https://github.com/ductoris/ML_localization/tree/experiment-data/data/sim-seven-office) gồm **3.935 ảnh RGB 512 × 128**. Có 291 ảnh train, 291 ảnh validation và 3.353 ảnh test dưới ba điều kiện sáng. [Metadata và pose Gazebo](https://github.com/ductoris/ML_localization/blob/experiment-data/data/sim-seven-office/metadata.csv) · [Sơ đồ vị trí thu](https://github.com/ductoris/ML_localization/blob/experiment-data/data/sim-seven-office/coverage.png)
- [Báo cáo huấn luyện](simulation/RESULTS-OFFICE.md) ghi kết quả 15 cấu hình. MobileNetV3 Large + DA4 có MAE trung bình **0,462 m** qua ba tập test. [Bảng CSV](results/office/summary.csv) · [Biểu đồ MAE](results/office/augmentation-mae.png) · [Trọng số DA4](https://github.com/ductoris/ML_localization/blob/experiment-data/results/office/models/mobilenet_v3_large-DA4.pt)
- [Log thu dữ liệu](results/office/capture.log) · [Nhật ký thay đổi bố trí văn phòng](simulation/RESULTS.md)

## Lấy dữ liệu và chạy thử từ thư mục gốc

Khi clone mới, dùng `--single-branch` để chỉ lấy nhánh mã nguồn. `--depth 1` lấy phiên bản mới nhất và `--filter=blob:none` cho phép tải chọn lọc các tệp dữ liệu khi cần.

```bash
git clone --branch main --single-branch --depth 1 --filter=blob:none \
  https://github.com/ductoris/ML_localization.git
cd ML_localization
```

Từ thư mục gốc của bản clone, lấy bộ ảnh và checkpoint DA4 vào thư mục làm việc trên `main`.

```bash
git fetch --depth 1 --filter=blob:none origin experiment-data
git restore --source=FETCH_HEAD --worktree -- \
  data/sim-seven-office results/office/models/mobilenet_v3_large-DA4.pt
```

Lệnh trên lấy cả DA1–DA6 để train lại. Nếu chỉ muốn thử suy luận, thay `data/sim-seven-office` trong lệnh bằng hai đường dẫn `data/sim-seven-office/TrainingBaseline` và `data/sim-seven-office/TestNight` cùng `data/sim-seven-office/metadata.csv`. Các checkpoint khác và lượt thu gốc nằm trên [nhánh experiment-data](https://github.com/ductoris/ML_localization/tree/experiment-data).

Dùng môi trường Python có PyTorch, torchvision, NumPy, Pillow và PyYAML. Ví dụ dưới đây sử dụng CPU và checkpoint đã huấn luyện.

```bash
office_image=$(find data/sim-seven-office/TestNight/office -name '*.png' -print -quit)
python -m eval.predict_sim --device cpu "$office_image" \
  results/office/models/mobilenet_v3_large-DA4.pt
```

Xem [hướng dẫn chạy Gazebo, thu ảnh, sinh augmentation và huấn luyện lại](simulation/README.md). Các lần huấn luyện lại ghi vào `data/sim-results-office/`. Kết quả đã công bố nằm ở `results/office/`.

Phương pháp định vị tham khảo bài báo của Cabrera và cộng sự. Các model nội thất từ Gazebo Fuel nằm trong `map/models/` cùng thông tin tác giả trong các file `model.config`. Tập ảnh trong repo này được nhóm thu bằng Gazebo. [Bài báo tham khảo](https://arxiv.org/abs/2407.10596) · [Bản đồ và nội thất](map/README.md)
