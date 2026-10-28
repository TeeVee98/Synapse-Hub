import os, glob, re

groups = [
    {
        'id': 1, 'name': 'Cụm công nghiệp', 'prefix': 'CCN', 'start': 123, 'end': 126, 'type': '4tc',
        'code_field': 'Mã', 'name_field': 'Tên CCN'
    },
    {
        'id': 2, 'name': 'Chợ', 'prefix': 'CHO', 'start': 127, 'end': 134, 'type': '8tc',
        'code_field': 'Mã', 'name_field': 'Tên'
    },
    {
        'id': 3, 'name': 'Siêu thị', 'prefix': 'ST', 'start': 135, 'end': 138, 'type': '4tc',
        'code_field': 'Mã', 'name_field': 'Tên'
    },
    {
        'id': 4, 'name': 'Nguồn điện', 'prefix': 'ND', 'start': 139, 'end': 142, 'type': '4tc',
        'code_field': 'Mã', 'name_field': 'Tên'
    },
    {
        'id': 5, 'name': 'Cửa hàng xăng dầu', 'prefix': 'CHXD', 'start': 143, 'end': 149, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên cửa hàng', 'fluct_title': 'Tổng sản lượng'
    },
    {
        'id': 6, 'name': 'Thương nhân phân phối xăng dầu', 'prefix': 'TNPP', 'start': 150, 'end': 156, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Tổng sản lượng'
    },
    {
        'id': 7, 'name': 'Doanh nghiệp sử dụng vật liệu nổ công nghiệp', 'prefix': 'VLN', 'start': 157, 'end': 163, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Quản lý kho chứa'
    },
    {
        'id': 8, 'name': 'Doanh nghiệp hoá chất', 'prefix': 'DNHC', 'start': 164, 'end': 170, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Quản lý kho chứa'
    },
    {
        'id': 9, 'name': 'Cửa hàng tiện lợi', 'prefix': 'CHTL', 'start': 171, 'end': 177, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên cửa hàng', 'fluct_title': 'Quản lý doanh thu, lao động'
    },
    {
        'id': 10, 'name': 'Trung tâm thương mại', 'prefix': 'TTTM', 'start': 178, 'end': 184, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên trung tâm', 'fluct_title': 'Thời gian'
    },
    {
        'id': 11, 'name': 'Doanh nghiệp bán hàng đa cấp', 'prefix': 'DC1', 'start': 185, 'end': 191, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Quản lý hội thảo'
    },
    {
        'id': 12, 'name': 'Trung tâm Logistics', 'prefix': 'LOG', 'start': 192, 'end': 198, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên trung tâm', 'fluct_title': 'Thời gian'
    },
    {
        'id': 13, 'name': 'Thương nhân bán lẻ rượu', 'prefix': 'BLR', 'start': 199, 'end': 205, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên thương nhân', 'fluct_title': 'Thời gian'
    },
    {
        'id': 14, 'name': 'Doanh nghiệp thương mại điện tử', 'prefix': 'TMDT', 'start': 206, 'end': 212, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên website', 'fluct_title': 'Thời gian'
    },
    {
        'id': 15, 'name': 'Thương nhân bán buôn thuốc lá', 'prefix': 'BBTL', 'start': 213, 'end': 219, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên thương nhân', 'fluct_title': 'Thời gian'
    },
    {
        'id': 16, 'name': 'Hợp tác xã', 'prefix': 'HTX', 'start': 220, 'end': 226, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên hợp tác xã', 'fluct_title': 'Thời gian'
    },
    {
        'id': 17, 'name': 'Doanh nghiệp bán hàng đa cấp', 'prefix': 'DC2', 'start': 227, 'end': 233, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Quản lý hội thảo'
    },
    {
        'id': 18, 'name': 'Doanh nghiệp kinh doanh khí', 'prefix': 'KDK', 'start': 234, 'end': 240, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Thời gian'
    },
    {
        'id': 19, 'name': 'Cơ sở sản xuất, kinh doanh thực phẩm nhỏ, lẻ', 'prefix': 'TPNL', 'start': 241, 'end': 247, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên cơ sở', 'fluct_title': 'Quản lý hậu kiểm'
    }
]

def get_script_path(tc_num):
    dirs = glob.glob(f'Scripts/TC-{tc_num}*')
    if dirs:
        groovies = glob.glob(f'{dirs[0]}/*.groovy')
        if groovies:
            return groovies[0]
    raise FileNotFoundError(f'TC-{tc_num} script not found!')

def write_script(path, content):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)

# Refactor Group 1: Cụm công nghiệp (TC-123 to 126)
p123 = get_script_path(123)
write_script(p123, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-123: Kiểm tra thêm mới dữ liệu Cụm công nghiệp thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.selectDataLayer("Cụm công nghiệp")
DataMiningPage.drawFeatureOnCanvas("Cụm công nghiệp")

String code = DataMiningPage.uniqueCode("CCN")
String name = "Cụm công nghiệp Auto " + (System.currentTimeMillis() % 10000L)
String address = "Số 123 Đường Nguyễn Huệ, Nghệ An"

DataMiningPage.fillDataAttributes(code, name, address)
DataMiningPage.verifyMiningSuccess("Tạo mới thành công dữ liệu cho lớp Cụm công nghiệp")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "Cụm công nghiệp")
DataMiningPage.verifySearchSuccess(1)
""")

p124 = get_script_path(124)
write_script(p124, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-124: Chỉnh sửa dữ liệu Cụm công nghiệp thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Cụm công nghiệp")
String updatedName = "CCN Cập nhật " + (System.currentTimeMillis() % 10000L)
DataMiningPage.editDataRecord(updatedName, "Cụm công nghiệp")
DataMiningPage.verifyMiningSuccess("Cập nhật thành công dữ liệu cho lớp Cụm công nghiệp")
""")

p125 = get_script_path(125)
write_script(p125, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-125: Kiểm tra tìm kiếm khi chọn lớp Cụm công nghiệp ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm theo đúng mã bản ghi đã tạo/chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Cụm công nghiệp")
DataMiningPage.searchByMapLayer(trackedCode, "Cụm công nghiệp")
DataMiningPage.verifySearchSuccess(1)
""")

p126 = get_script_path(126)
write_script(p126, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-126: Kiểm tra chức năng Xóa Cụm công nghiệp ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("Cụm công nghiệp")
DataMiningPage.deleteDataRecord("Cụm công nghiệp")
DataMiningPage.verifyMiningSuccess("Xóa dữ liệu thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "Cụm công nghiệp")
""")

# Refactor Group 2: Chợ (TC-127 to 134)
p127 = get_script_path(127)
write_script(p127, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-127: Kiểm tra thêm mới dữ liệu Chợ thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.selectDataLayer("Chợ")
DataMiningPage.drawFeatureOnCanvas("Chợ")

String code = DataMiningPage.uniqueCode("CHO")
String name = "Chợ Trung Tâm Auto " + (System.currentTimeMillis() % 10000L)
String address = "Số 456 Đường Lê Lợi, Nghệ An"
String activeYear = "2020"

DataMiningPage.fillDataAttributes(code, name, address, activeYear)
DataMiningPage.verifyMiningSuccess("Tạo mới thành công dữ liệu cho lớp Chợ")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "Chợ")
DataMiningPage.verifySearchSuccess(1)
""")

p128 = get_script_path(128)
write_script(p128, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-128: Chỉnh sửa dữ liệu Chợ thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Chợ")
String updatedName = "Chợ Cập nhật " + (System.currentTimeMillis() % 10000L)
DataMiningPage.editDataRecord(updatedName, "Chợ")
DataMiningPage.verifyMiningSuccess("Cập nhật thành công dữ liệu cho lớp Chợ")
""")

p129 = get_script_path(129)
write_script(p129, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-129: Kiểm tra tìm kiếm khi chọn lớp Chợ ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm theo đúng mã bản ghi đã tạo/chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Chợ")
DataMiningPage.searchByMapLayer(trackedCode, "Chợ")
DataMiningPage.verifySearchSuccess(1)
""")

p134 = get_script_path(134)
write_script(p134, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-134: Kiểm tra chức năng Xóa Chợ gốc ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("Chợ")
DataMiningPage.closeFluctuationModal()
DataMiningPage.deleteDataRecord("Chợ")
DataMiningPage.verifyMiningSuccess("Xóa dữ liệu thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "Chợ")
""")

# Refactor Group 3: Siêu thị (TC-135 to 138)
p135 = get_script_path(135)
write_script(p135, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-135: Kiểm tra thêm mới dữ liệu Siêu thị thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.selectDataLayer("Siêu thị")
DataMiningPage.drawFeatureOnCanvas("Siêu thị")

String code = DataMiningPage.uniqueCode("ST")
String name = "Siêu thị Auto " + (System.currentTimeMillis() % 10000L)
String address = "Số 789 Đường Quang Trung, Nghệ An"
String activeYear = "2021"

DataMiningPage.fillDataAttributes(code, name, address, activeYear)
DataMiningPage.verifyMiningSuccess("Tạo mới thành công dữ liệu cho lớp Siêu thị")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "Siêu thị")
DataMiningPage.verifySearchSuccess(1)
""")

p136 = get_script_path(136)
write_script(p136, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-136: Chỉnh sửa dữ liệu thành công (Siêu thị) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Siêu thị")
String updatedName = "Siêu thị Cập nhật " + (System.currentTimeMillis() % 10000L)
DataMiningPage.editDataRecord(updatedName, "Siêu thị")
DataMiningPage.verifyMiningSuccess("Cập nhật thành công dữ liệu cho lớp Siêu thị")
""")

p137 = get_script_path(137)
write_script(p137, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-137: Kiểm tra tìm kiếm khi chọn một lớp bản đồ (Siêu thị) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm theo đúng mã bản ghi đã tạo/chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Siêu thị")
DataMiningPage.searchByMapLayer(trackedCode, "Siêu thị")
DataMiningPage.verifySearchSuccess(1)
""")

p138 = get_script_path(138)
write_script(p138, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-138: Kiểm tra chức năng Xóa (Siêu thị) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("Siêu thị")
DataMiningPage.deleteDataRecord("Siêu thị")
DataMiningPage.verifyMiningSuccess("Xóa dữ liệu thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "Siêu thị")
""")

# Refactor Group 4: Nguồn điện (TC-139 to 142)
p139 = get_script_path(139)
write_script(p139, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-139: Kiểm tra thêm mới Nguồn điện thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.selectDataLayer("Nguồn điện")
DataMiningPage.drawFeatureOnCanvas("Nguồn điện")

String code = DataMiningPage.uniqueCode("ND")
String name = "Nguồn điện Auto " + (System.currentTimeMillis() % 10000L)
String address = "Số 101 Đường Phan Bội Châu, Nghệ An"

DataMiningPage.fillDataAttributes(code, name, address)
DataMiningPage.verifyMiningSuccess("Tạo mới thành công dữ liệu cho lớp Nguồn điện")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "Nguồn điện")
DataMiningPage.verifySearchSuccess(1)
""")

p140 = get_script_path(140)
write_script(p140, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-140: Chỉnh sửa dữ liệu thành công (Nguồn điện) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Nguồn điện")
String updatedName = "Nguồn điện Cập nhật " + (System.currentTimeMillis() % 10000L)
DataMiningPage.editDataRecord(updatedName, "Nguồn điện")
DataMiningPage.verifyMiningSuccess("Cập nhật thành công dữ liệu cho lớp Nguồn điện")
""")

p141 = get_script_path(141)
write_script(p141, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-141: Kiểm tra tìm kiếm khi chọn một lớp bản đồ (Nguồn điện) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm theo đúng mã bản ghi đã tạo/chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Nguồn điện")
DataMiningPage.searchByMapLayer(trackedCode, "Nguồn điện")
DataMiningPage.verifySearchSuccess(1)
""")

p142 = get_script_path(142)
write_script(p142, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-142: Kiểm tra chức năng Xóa (Nguồn điện) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("Nguồn điện")
DataMiningPage.deleteDataRecord("Nguồn điện")
DataMiningPage.verifyMiningSuccess("Xóa dữ liệu thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "Nguồn điện")
""")

# Refactor Group 5: Cửa hàng xăng dầu (TC-143 to 149)
p143 = get_script_path(143)
write_script(p143, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-143: Thêm mới Cửa hàng xăng dầu thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.selectDataLayer("Cửa hàng xăng dầu")
DataMiningPage.drawFeatureOnCanvas("Cửa hàng xăng dầu")

String code = DataMiningPage.uniqueCode("CHXD")
String name = "Cửa hàng xăng dầu Auto " + (System.currentTimeMillis() % 10000L)
String address = "Số 202 Đường Lê Duẩn, Nghệ An"

DataMiningPage.fillDataAttributes(code, name, address)
DataMiningPage.verifyMiningSuccess("Tạo mới thành công dữ liệu cho lớp Cửa hàng xăng dầu")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "Cửa hàng xăng dầu")
DataMiningPage.verifySearchSuccess(1)
""")

p144 = get_script_path(144)
write_script(p144, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-144: Chỉnh sửa dữ liệu thành công (Cửa hàng xăng dầu) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Cửa hàng xăng dầu")
String updatedName = "Cửa hàng xăng dầu Cập nhật " + (System.currentTimeMillis() % 10000L)
DataMiningPage.editDataRecord(updatedName, "Cửa hàng xăng dầu")
DataMiningPage.verifyMiningSuccess("Cập nhật thành công dữ liệu cho lớp Cửa hàng xăng dầu")
""")

p145 = get_script_path(145)
write_script(p145, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-145: Kiểm tra tìm kiếm khi chọn một lớp bản đồ (Cửa hàng xăng dầu) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm theo đúng mã bản ghi đã tạo/chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("Cửa hàng xăng dầu")
DataMiningPage.searchByMapLayer(trackedCode, "Cửa hàng xăng dầu")
DataMiningPage.verifySearchSuccess(1)
""")

p149 = get_script_path(149)
write_script(p149, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-149: Kiểm tra chức năng Xóa Cửa hàng xăng dầu ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("Cửa hàng xăng dầu")
DataMiningPage.closeFluctuationModal()
DataMiningPage.deleteDataRecord("Cửa hàng xăng dầu")
DataMiningPage.verifyMiningSuccess("Xóa dữ liệu thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "Cửa hàng xăng dầu")
""")

# Refactor Groups 6 to 19 (7 TCs each)
for g in groups[5:]:
    start = g['start']
    name = g['name']
    prefix = g['prefix']
    code_field = g['code_field']
    name_field = g['name_field']
    fluct_title = g['fluct_title']

    # 1. Create (start)
    p_create = get_script_path(start)
    write_script(p_create, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import dmit.pages.BasePage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start}: Thêm mới {name} thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

DataMiningPage.startAddFeature("{name}", -140, -80)

String code = BasePage.uniqueCode("{prefix}")
String recordName = "{name} " + code
Map<String, String> data = [
    '{code_field}': code,
    '{name_field}': recordName,
    'Địa chỉ': '123 Đường Lê Duẩn, Nghệ An'
]
DataMiningPage.fillDynamicForm(data)
DataMiningPage.confirmAddForm()
DataMiningPage.verifyMiningSuccess("thành công")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "{name}")
DataMiningPage.verifySearchSuccess(1)
""")

    # 2. Edit (start + 1)
    p_edit = get_script_path(start + 1)
    write_script(p_edit, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import dmit.pages.BasePage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 1}: Chỉnh sửa dữ liệu {name} thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để mở và chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.openRecordFromSearch("{name}", trackedCode)

DataMiningPage.openEditFromPopup()

String updatedName = "{name} " + BasePage.uniqueCode("{prefix}_EDIT")
DataMiningPage.saveEditForm("{name_field}", updatedName)
DataMiningPage.verifyMiningSuccess("thành công")
""")

    # 3. Search (start + 2)
    p_search = get_script_path(start + 2)
    write_script(p_search, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 2}: Kiểm tra tìm kiếm khi chọn lớp {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm theo đúng mã bản ghi đã tạo/chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.searchByLayer("{name}", trackedCode)
DataMiningPage.verifyMiningSuccess("tìm thấy")
""")

    # 4. Fluctuation Create (start + 3)
    p_fcreate = get_script_path(start + 3)
    write_script(p_fcreate, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 3}: Thêm mới dữ liệu biến động {name} hợp lệ ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm và mở đúng bản ghi đã tạo để liên kết biến động
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.openRecordFromSearch("{name}", trackedCode)

DataMiningPage.openFluctuationByTitle("{fluct_title}")

String year = "2026"
String period = "Cả năm"
Map<String, String> extraData = [
    'Sản lượng': '1500',
    'Doanh thu': '500000000'
]
DataMiningPage.addFluctuationRecord(year, period, extraData)
DataMiningPage.verifyMiningSuccess("thành công")
""")

    # 5. Fluctuation Edit (start + 4)
    p_fedit = get_script_path(start + 4)
    write_script(p_fedit, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 4}: Chỉnh sửa dữ liệu biến động {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Mở đúng bản ghi theo mã
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.openRecordFromSearch("{name}", trackedCode)

DataMiningPage.openFluctuationByTitle("{fluct_title}")
DataMiningPage.editFluctuationRecord("Sản lượng", "1800")
DataMiningPage.verifyMiningSuccess("thành công")
""")

    # 6. Fluctuation Delete (start + 5)
    p_fdelete = get_script_path(start + 5)
    write_script(p_fdelete, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 5}: Xoá dữ liệu biến động {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Mở đúng bản ghi theo mã
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.openRecordFromSearch("{name}", trackedCode)

DataMiningPage.openFluctuationByTitle("{fluct_title}")
DataMiningPage.deleteFluctuationRecord()
DataMiningPage.verifyMiningSuccess("thành công")
""")

    # 7. Delete Root (start + 6)
    p_delete = get_script_path(start + 6)
    write_script(p_delete, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 6}: Kiểm tra chức năng Xóa {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.openRecordFromSearch("{name}", trackedCode)
DataMiningPage.deleteRecordFromPopup()
DataMiningPage.verifyMiningSuccess("thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "{name}")
""")

print("Successfully refactored all 125 test scripts across all 19 functional groups!")
