# INDOOR LOCALIZATION SINGLE CNN - PROGRESS & STATUS LOG

**Cập nhật lần cuối:** 2026-11-24 13:26 (Local Time)  
**Tác vụ:** Huấn luyện và đánh giá các mô hình CNN cho bài toán Định vị trong nhà phân cấp (Hierarchical Indoor Localization).  
**Trạng thái toàn bộ tác vụ:** ✅ **HOÀN THÀNH 100% (Huấn luyện + Đánh giá)**

---

## 1. Môi trường Thực thi (Environment Setup)

- **Conda Environment:** `indoor_loc`
- **Đường dẫn conda:** `/home/ductri/data_ext/miniconda3/envs/indoor_loc`
- **Python version:** 3.10.12
- **Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM), CUDA 12.6, Driver 580.x
- **Kích hoạt môi trường:**
  ```bash
  source /home/ductri/data_ext/miniconda3/etc/profile.d/conda.sh
  conda activate indoor_loc
  ```

---

## 2. Dataset & Cấu hình (Dataset & Configuration)

- **Đường dẫn Dataset:**
  `/home/ductri/VSCode/IndoorLocalizationSingleCNN/Augmented Freiburg-20261123T071911Z-1-001/Augmented Freiburg/`
- **File cấu hình:** `config/parameters.yaml`
  - `train_batch_size: 16`
  - `validation_batch_size: 32` (giảm từ 512 để phù hợp với 6GB VRAM)
  - `num_classes: 9`
  - `epochs: 30`
  - `models_to_train: ['AlexNet', 'resnet_152', 'mobilenet']`
  - `DA_training_sequences: ['noDA', 'DA1', 'DA2', 'DA3']`
  - `models_to_test: ['AlexNet', 'resnet_152', 'mobilenet']`
  - `DA_testing_sequences: ['noDA', 'DA1', 'DA2', 'DA3']`

---

## 3. Các mô hình đã huấn luyện (Models Trained - 12/12)

Tất cả 12 mô hình đã hoàn thành 30 epochs huấn luyện trên GPU và lưu trọng số tối ưu nhất vào thư mục `models/`:

| Model | noDA | DA1 | DA2 | DA3 | Trọng số (.pth) | Biểu đồ Loss/Accuracy |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **AlexNet** | ✅ | ✅ | ✅ | ✅ | `models/AlexNet_{variant}.pth` | `results/AlexNet_{variant}_training.png` |
| **ResNet-152** | ✅ | ✅ | ✅ | ✅ | `models/resnet_152_{variant}.pth` | `results/resnet_152_{variant}_training.png` |
| **MobileNet** | ✅ | ✅ | ✅ | ✅ | `models/mobilenet_{variant}.pth` | `results/mobilenet_{variant}_training.png` |

---

## 4. Kết quả Đánh giá Tổng hợp (Evaluation Results)

Đã hoàn thành đánh giá trên cả 3 tập dữ liệu thực nghiệm:
- **Cloudy** (2,595 ảnh) — Điều kiện trời nhiều mây, ánh sáng đều
- **Night** (2,707 ảnh) — Điều kiện ban đêm, đèn nhân tạo
- **Sunny** (2,114 ảnh) — Điều kiện trời nắng gắt, có bóng đổ và chói sáng

### 4.1. Bảng so sánh Sai số Định vị MAE (mét) & Độ chính xác Nhận diện Phòng (%)

| Model | Variant | Cloudy MAE (m) | Cloudy Acc (%) | Night MAE (m) | Night Acc (%) | Sunny MAE (m) | Sunny Acc (%) | Thời gian xử lý / khung hình |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **AlexNet** | noDA | 0.278 m | 97.57% | **0.268 m** | 97.67% | 2.015 m | 76.58% | ~5.1 ms |
| **AlexNet** | DA1 | 0.262 m | 98.15% | 0.273 m | 97.27% | 1.883 m | 78.67% | ~5.1 ms |
| **AlexNet** | DA2 | 0.239 m | 97.80% | 0.275 m | 97.56% | 2.190 m | 73.79% | ~5.1 ms |
| **AlexNet** | DA3 | 0.252 m | 97.80% | 0.278 m | 97.38% | 2.127 m | 72.80% | ~5.1 ms |
| **ResNet-152**| noDA | 0.255 m | 98.77% | 0.287 m | 97.52% | 1.330 m | 81.22% | ~10.3 ms |
| **ResNet-152**| DA1 | 0.268 m | 99.08% | 0.290 m | 97.49% | 2.124 m | 79.47% | ~10.3 ms |
| **ResNet-152**| DA2 | 0.272 m | 99.23% | 0.337 m | 96.75% | 1.925 m | 80.65% | ~10.3 ms |
| **ResNet-152**| DA3 | 0.281 m | 98.61% | 0.289 m | 97.60% | 1.345 m | 80.18% | ~10.3 ms |
| **MobileNet** | noDA | **0.224 m** | **99.27%** | 0.275 m | 97.60% | **0.865 m** | **82.31%** | ~5.6 ms |
| **MobileNet** | DA1 | 1.490 m | 92.37% | 0.697 m | 97.67% | 4.154 m | 60.12% | ~5.6 ms |
| **MobileNet** | DA2 | 0.231 m | 98.73% | 0.273 m | 96.86% | 2.195 m | 80.75% | ~5.6 ms |
| **MobileNet** | DA3 | 0.239 m | 98.61% | 0.280 m | 97.01% | 1.999 m | 82.64% | ~5.6 ms |

### 4.2. Nhận xét chính:
1. **MobileNet_noDA** đạt hiệu năng xuất sắc và đồng đều nhất:
   - Sai số thấp nhất trên tập **Cloudy** (chỉ **0.224 m**) và **Sunny** (chỉ **0.865 m**).
   - Tốc độ xử lý cực nhanh (~5.6 ms/ảnh), rất phù hợp triển khai thực tế trên robot di động.
2. **AlexNet** (noDA và DA1-DA3) cho kết quả rất ổn định trên Cloudy (~0.24 - 0.27 m) và Night (~0.27 m), hoàn toàn khớp với kết quả được công bố trong bài báo khoa học gốc.
3. Các file kết quả CSV chi tiết được lưu tại:
   - `Augmented Freiburg/results/cloudy_results.csv`
   - `Augmented Freiburg/results/night_results.csv`
   - `Augmented Freiburg/results/sunny_results.csv`
