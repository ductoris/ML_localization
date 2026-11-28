# Dữ liệu và trọng số mô phỏng Gazebo

Mã nguồn, map và hướng dẫn chạy nằm trên nhánh [main](https://github.com/ductoris/ML_localization/tree/main).

| Đường dẫn | Nội dung |
| --- | --- |
| `data/sim-seven-office/` | 3.935 ảnh đã chia train, validation và ba tập test, kèm pose Gazebo |
| `data/sim-seven-office/TrainingDA/` | Sáu biến thể augmentation, gồm 19.497 ảnh và manifest nguồn |
| `data/sim-runs-office/` | Bốn lượt thu gốc, metadata và log |
| `results/office/` | Kết quả theo ảnh, lịch sử, bảng tổng hợp và checkpoint của 15 cấu hình |

## Khôi phục checkpoint lớn

Các tệp `.pt` nhỏ nằm tại `results/office/models/`. Các checkpoint lớn được lưu thành các phần 64 MiB và có SHA-256 trong manifest. Ví dụ dưới đây khôi phục ConvNeXt Large và kiểm tra tổng kiểm trước khi xuất file.

```bash
python3 restore_weights.py results/office/models/parts/convnext_large-noDA.pt.json
```
