#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMIT Canvas Visual Diff & Regression Checker
=============================================
Cung cấp khả năng kiểm thử trực quan (Visual AI Testing) cho các biểu đồ Canvas
trong phân hệ Quản trị Dữ liệu & Canvas Khai Phá (DataMiningPage - TC-123 đến TC-247).

Tính năng:
  1. compare: So sánh ảnh Canvas hiện tại với ảnh chuẩn (Golden Baseline).
     Tính toán tỷ lệ sai khác pixel, tạo ảnh diff làm bằng chứng trực quan.
  2. check-blank: Phát hiện lỗi Canvas bị trắng xóa / không render được dữ liệu.
  3. update-baseline: Cập nhật ảnh chuẩn mới khi nghiệp vụ thay đổi giao diện.

Sử dụng:
  python3 tools/visual_diff_canvas.py compare baseline.png current.png --diff diff.png --threshold 0.02
  python3 tools/visual_diff_canvas.py check-blank current.png
"""

import os
import sys
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:
    print("❌ Lỗi: Thư viện Pillow chưa được cài đặt. Hãy chạy: pip install Pillow")
    sys.exit(1)


def is_canvas_blank(image_path: str, std_dev_threshold: float = 2.0) -> tuple[bool, float]:
    """
    Kiểm tra xem ảnh canvas có bị trắng trơn (hoặc một màu đồng nhất, không có đồ thị) hay không.
    Trả về (is_blank, std_dev).
    """
    with Image.open(image_path) as img:
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        std_dev = stat.stddev[0]
        # Nếu độ lệch chuẩn thấp hơn ngưỡng, ảnh gần như đồng màu (trống trơn)
        return (std_dev < std_dev_threshold, std_dev)


def compare_canvas_images(
    baseline_path: str,
    current_path: str,
    diff_output_path: str | None = None,
    threshold: float = 0.01
) -> tuple[bool, float, int]:
    """
    So sánh 2 ảnh Canvas theo từng pixel.
    Trả về (is_match, diff_ratio, diff_pixels).
    threshold: Tỷ lệ khác biệt cho phép (ví dụ: 0.01 = 1% sai lệch)
    """
    with Image.open(baseline_path) as img_base, Image.open(current_path) as img_curr:
        # Chuẩn hóa về cùng kích thước và RGB
        if img_base.size != img_curr.size:
            img_curr = img_curr.resize(img_base.size, Image.Resampling.LANCZOS)

        base_rgb = img_base.convert("RGB")
        curr_rgb = img_curr.convert("RGB")

        # Tính toán sai khác pixel
        diff = ImageChops.difference(base_rgb, curr_rgb)
        
        # Đếm số pixel khác biệt (ngưỡng delta > 15 để bỏ qua nhiễu anti-aliasing)
        diff_data = diff.getdata()
        diff_count = 0
        total_pixels = img_base.width * img_base.height

        diff_mask = Image.new("RGBA", img_base.size, (0, 0, 0, 0))
        diff_mask_pixels = diff_mask.load()

        for y in range(img_base.height):
            for x in range(img_base.width):
                r, g, b = diff.getpixel((x, y))
                if (r + g + b) > 30:  # Pixel có độ lệch màu đáng kể
                    diff_count += 1
                    diff_mask_pixels[x, y] = (255, 0, 0, 200)  # Tô đỏ điểm sai khác

        diff_ratio = diff_count / total_pixels
        is_match = diff_ratio <= threshold

        if diff_output_path and not is_match:
            os.makedirs(os.path.dirname(os.path.abspath(diff_output_path)), exist_ok=True)
            # Ghép nền ảnh hiện tại và đè layer màu đỏ cảnh báo
            annotated = curr_rgb.convert("RGBA")
            annotated.paste(diff_mask, (0, 0), diff_mask)
            annotated.save(diff_output_path)

        return (is_match, diff_ratio, diff_count)


def main():
    parser = argparse.ArgumentParser(description="DMIT Canvas Visual Diff & Regression Checker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: compare
    compare_p = subparsers.add_parser("compare", help="So sánh ảnh Canvas hiện tại với ảnh chuẩn")
    compare_p.add_argument("baseline", help="Đường dẫn ảnh chuẩn (Golden Baseline)")
    compare_p.add_argument("current", help="Đường dẫn ảnh chụp thực tế lúc chạy test")
    compare_p.add_argument("--diff", default=None, help="Đường dẫn lưu ảnh diff highlight nếu có sai khác")
    compare_p.add_argument("--threshold", type=float, default=0.01, help="Tỷ lệ sai lệch tối đa cho phép (mặc định 0.01 = 1%%)")

    # Command: check-blank
    blank_p = subparsers.add_parser("check-blank", help="Kiểm tra canvas có bị trắng trơn / trống dữ liệu không")
    blank_p.add_argument("current", help="Đường dẫn ảnh chụp Canvas cần kiểm tra")
    blank_p.add_argument("--threshold", type=float, default=2.0, help="Độ lệch chuẩn tối thiểu để coi là có render (mặc định 2.0)")

    args = parser.parse_args()

    if args.command == "compare":
        if not os.path.exists(args.baseline):
            print(f"❌ Không tìm thấy file baseline: {args.baseline}")
            sys.exit(2)
        if not os.path.exists(args.current):
            print(f"❌ Không tìm thấy file current: {args.current}")
            sys.exit(2)

        is_match, diff_ratio, diff_count = compare_canvas_images(
            args.baseline, args.current, args.diff, args.threshold
        )
        pct = diff_ratio * 100
        if is_match:
            print(f"✅ PASS: Canvas trực quan khớp với Baseline (Khác biệt: {pct:.2f}%, {diff_count} px <= {args.threshold*100:.1f}%)")
            sys.exit(0)
        else:
            print(f"❌ FAIL: Canvas có biến đổi trực quan vượt ngưỡng (Khác biệt: {pct:.2f}%, {diff_count} px > {args.threshold*100:.1f}%)")
            if args.diff:
                print(f"   📸 Đã tạo ảnh diff bằng chứng tại: {args.diff}")
            sys.exit(1)

    elif args.command == "check-blank":
        if not os.path.exists(args.current):
            print(f"❌ Không tìm thấy file ảnh: {args.current}")
            sys.exit(2)

        blank, std_dev = is_canvas_blank(args.current, args.threshold)
        if blank:
            print(f"❌ CẢNH BÁO: Canvas bị trắng trơn / không có dữ liệu render (Độ lệch chuẩn: {std_dev:.2f} < {args.threshold})")
            sys.exit(1)
        else:
            print(f"✅ PASS: Canvas hiển thị nội dung hợp lệ (Độ lệch chuẩn: {std_dev:.2f} >= {args.threshold})")
            sys.exit(0)


if __name__ == "__main__":
    main()
