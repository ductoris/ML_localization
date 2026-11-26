# Kết quả định vị với bố trí văn phòng mới

Thí nghiệm dùng bộ ảnh `data/sim-seven-office/` với 291 ảnh train cloudy, 291 ảnh validation cloudy và 3.353 ảnh từ ba lượt test độc lập. Bản đồ ảnh tham chiếu gồm 291 ảnh gốc. DA1–DA6 được sinh từ ảnh train cloudy của bố trí mới.

Huấn luyện 30 epoch từ trọng số ImageNet V1, seed 42 và mixed precision. AlexNet và MobileNetV3 Large dùng batch 16 cho bảy biến thể dữ liệu. ConvNeXt Large chạy thêm một lượt noDA với batch 2 để vừa bộ nhớ GPU. Mỗi lượt giữ checkpoint có accuracy validation cao nhất, ưu tiên epoch sớm nhất khi bằng điểm. Sai số vị trí được tính theo khoảng cách Euclid từ `(x_est, y_est)` đến pose Gazebo đồng bộ với ảnh.

## Sai số vị trí trung bình theo cấu hình

Mỗi ô tính trung bình MAE của ba tập test với trọng số bằng nhau, đơn vị mét.

| Dữ liệu train | AlexNet | MobileNetV3 Large |
| --- | ---: | ---: |
| noDA | 0,471 | 0,510 |
| DA1 | 0,473 | 0,483 |
| DA2 | 0,478 | 0,477 |
| DA3 | 0,498 | 0,477 |
| DA4 | 0,472 | 0,462 |
| DA5 | 0,487 | 0,482 |
| DA6 | 0,493 | 0,477 |

ConvNeXt Large noDA đạt MAE trung bình 0,506 m.

## Kết quả MobileNetV3 Large DA4 theo điều kiện sáng

Cấu hình này có MAE trung bình thấp nhất trong 15 lượt đã chạy, 0,462 m. Kết quả được đo với một seed huấn luyện.

| Điều kiện | Accuracy phòng | MAE (m) | RMSE (m) | ms/ảnh | Accuracy riêng văn phòng |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nhiều mây | 100,00% | 0,452 | 0,655 | 3,425 | 109/109 |
| Nắng | 99,91% | 0,468 | 0,671 | 3,334 | 110/110 |
| Ban đêm | 99,91% | 0,465 | 0,641 | 3,069 | 110/110 |

Các kết quả của bố trí ban đầu và bố trí mới được đo trên hai bộ ảnh và tuyến thu khác nhau. Mức chênh lệch giữa hai lần đánh giá phản ánh cả thay đổi bố trí và dữ liệu thu.

Mỗi lượt xuất nhãn phòng, tọa độ robot ước lượng, pose thật và thời gian xử lý cho từng ảnh test trong `results/office/<model>-<variant>/predictions.csv`. Cùng thư mục có lịch sử huấn luyện và ma trận nhầm lẫn. `summary.csv` ghi toàn bộ 45 phép đánh giá, `room-accuracy.csv` ghi kết quả theo phòng và `augmentation-mae.png` so sánh sai số vị trí.

[Lệnh chạy lại và mô tả bộ dữ liệu](README.md#giai-đoạn-6--train-và-đánh-giá-hai-tầng) · [Nhật ký thay đổi bố trí văn phòng](RESULTS.md)
