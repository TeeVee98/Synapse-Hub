# Mobile Automation Rules — Appium iOS & Android (Full Standard)

> Nâng cấp hoàn chỉnh từ bản `upcoming_extension` trong Synapse-Hub cho UIAutomator2 (Android) và XCUITest (iOS).

## 1. Screen Object Model (SOM)
* Đóng gói 100% locator và thao tác màn hình vào `screens/` (tối đa 1 `BaseScreen`). Tuyệt đối không viết selector trực tiếp trong `tests/`.
* Tách biệt locator theo nền tảng khi cây UI khác nhau (`locators/ios/` và `locators/android/`).

## 2. Mobile Locator Hierarchy (Strict)
1. **Accessibility ID (Ưu tiên 1 — Đa nền tảng):** `~accessibilityId` (iOS `accessibilityIdentifier` / Android `content-desc`).
2. **iOS Native (Ưu tiên 2 cho iOS):** `-ios predicate string` (vd: `label == "Login" AND visible == 1`) hoặc `-ios class chain`.
3. **Android Native (Ưu tiên 3 cho Android):** `id` / `resource-id` (`new UiSelector().resourceId(...)`).
4. **Cấm tuyệt đối:** XPath chứa chỉ số index (`//XCUIElementTypeCell[3]`, `//android.widget.TextView[2]`) và tọa độ cứng `tap(x, y)`.

## 3. Stability, Alerts & Context Switching
* **Capabilities:** Khai báo rõ `automationName`, `newCommandTimeout`, và chiến lược `noReset`/`fullReset` để đảm bảo test độc lập.
* **System Alerts & Keyboard:** Chủ động xử lý hộp thoại quyền hệ điều hành (Location, Camera, Notification) và gọi `hideKeyboard()` trước khi tương tác phần tử bị che.
* **Smart Scroll & WebView:** Dùng cuộn động có điều kiện dừng khi tìm phần tử ngoài màn hình. Khi thao tác Hybrid/WebView, kiểm tra `getContexts()` và quay lại `NATIVE_APP` ngay sau khi xong.
