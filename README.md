# Định vị robot trong nhà bằng panorama 360° và Gazebo

Dự án nhóm mô phỏng TurtleBot 4 trong nhà bảy phòng. Từ mỗi ảnh panorama, mô hình dự đoán phòng rồi tìm ảnh tham chiếu gần nhất trong phòng đó để ước lượng tọa độ robot `(x, y)` theo mét trong hệ `house`.

## Dữ liệu và kết quả của nhóm

- [Bộ dữ liệu Gazebo](data/sim-seven-office/) gồm **3.935 ảnh RGB 512 × 128**. Có 291 ảnh train, 291 ảnh validation và 3.353 ảnh test dưới ba điều kiện sáng. [Metadata và pose Gazebo](data/sim-seven-office/metadata.csv) · [Sơ đồ vị trí thu](data/sim-seven-office/coverage.png)
- [Báo cáo huấn luyện](simulation/RESULTS-OFFICE.md) ghi kết quả 15 cấu hình. MobileNetV3 Large + DA4 có MAE trung bình **0,462 m** qua ba tập test. [Bảng CSV](results/office/summary.csv) · [Biểu đồ MAE](results/office/augmentation-mae.png) · [Trọng số DA4](results/office/models/mobilenet_v3_large-DA4.pt)
- [Log thu dữ liệu](results/office/capture.log) · [Nhật ký thay đổi bố trí văn phòng](simulation/RESULTS.md)

## Chạy thử từ thư mục gốc

Dùng môi trường Python có PyTorch, torchvision, NumPy, Pillow và PyYAML. Ví dụ dưới đây sử dụng CPU và checkpoint đã huấn luyện.

```bash
office_image=$(find data/sim-seven-office/TestNight/office -name '*.png' -print -quit)
python -m eval.predict_sim --device cpu "$office_image" \
  results/office/models/mobilenet_v3_large-DA4.pt
```

Xem [hướng dẫn chạy Gazebo, thu ảnh, sinh augmentation và huấn luyện lại](simulation/README.md). Các lần huấn luyện lại ghi vào `data/sim-results-office/`. Kết quả và checkpoint đi kèm nằm ở `results/office/`.

Phương pháp định vị tham khảo bài báo của Cabrera và cộng sự. Các model nội thất từ Gazebo Fuel nằm trong `map/models/` cùng thông tin tác giả trong các file `model.config`. Tập ảnh trong repo này được nhóm thu bằng Gazebo. [Bài báo tham khảo](https://arxiv.org/abs/2407.10596) · [Bản đồ và nội thất](map/README.md)
