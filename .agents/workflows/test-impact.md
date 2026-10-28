---
name: test-impact
description: Phân tích các ca kiểm thử bị ảnh hưởng khi sửa đổi Page Class bằng AST Knowledge Graph
trigger: /test-impact
---

# Workflow: test-impact

Chạy phân tích ảnh hưởng dựa trên thay đổi mã nguồn Git:

```bash
python tools/test_impact.py --git-diff
```

Xuất danh sách test cases bị ảnh hưởng trực tiếp và gián tiếp để chỉ định chạy lại các test cases này thay vì toàn bộ hệ thống.
