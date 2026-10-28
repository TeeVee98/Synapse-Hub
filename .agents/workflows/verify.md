---
name: verify
description: Chạy cổng thẩm định 7 Gates kiểm tra chất lượng mã nguồn toàn diện trước khi bàn giao
trigger: /verify
---

# Workflow: verify

Chạy cổng kiểm định 7 Gates (UTF-8 No BOM, No Inline XPath, UniqueCode Idempotent, Meta Infer, Clean POM, AST Linter):

```bash
python tools/verify_all.py
```

Nếu phát hiện bất kỳ cổng nào FAIL, dừng lại và yêu cầu khắc phục triệt để trước khi tiếp tục.
