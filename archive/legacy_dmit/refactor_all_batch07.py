import os, glob

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
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Khối lượng VLNCN'
    },
    {
        'id': 8, 'name': 'Doanh nghiệp hoá chất', 'prefix': 'DNHC', 'start': 164, 'end': 170, 'type': '7tc',
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Thời gian'
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
        'code_field': 'Mã', 'name_field': 'Tên doanh nghiệp', 'fluct_title': 'Tổng sản lượng theo năm'
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
        f.write(content.strip() + '\n')

count = 0

for g in groups:
    gid = g['id']
    name = g['name']
    prefix = g['prefix']
    start = g['start']
    end = g['end']
    gtype = g['type']
    code_field = g['code_field']
    name_field = g['name_field']

    if gtype == '4tc':
        # 1. Create (start)
        p1 = get_script_path(start)
        write_script(p1, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start}: Kiểm tra thêm mới dữ liệu {name} thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.selectDataLayer("{name}")
DataMiningPage.drawFeatureOnCanvas("{name}")

String code = DataMiningPage.uniqueCode("{prefix}")
String recordName = "{name} Auto " + (System.currentTimeMillis() % 10000L)
String address = "Số 123 Đường Nguyễn Huệ, Nghệ An"

DataMiningPage.fillDataAttributes(code, recordName, address)
DataMiningPage.verifyMiningSuccess("Tạo mới thành công dữ liệu cho lớp {name}")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "{name}")
DataMiningPage.verifySearchSuccess(1)
""")
        count += 1

        # 2. Edit (start + 1)
        p2 = get_script_path(start + 1)
        write_script(p2, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 1}: Chỉnh sửa dữ liệu {name} thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
String updatedName = "{name} Cập nhật " + (System.currentTimeMillis() % 10000L)
DataMiningPage.editDataRecord(updatedName, "{name}")
DataMiningPage.verifyMiningSuccess("Cập nhật thành công dữ liệu cho lớp {name}")
""")
        count += 1

        # 3. Search (start + 2)
        p3 = get_script_path(start + 2)
        write_script(p3, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 2}: Kiểm tra tìm kiếm khi chọn lớp {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Tìm kiếm theo đúng mã bản ghi đã tạo/chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.searchByMapLayer(trackedCode, "{name}")
DataMiningPage.verifySearchSuccess(1)
""")
        count += 1

        # 4. Delete (start + 3)
        p4 = get_script_path(start + 3)
        write_script(p4, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 3}: Kiểm tra chức năng Xóa {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.deleteDataRecord("{name}")
DataMiningPage.verifyMiningSuccess("Xóa dữ liệu thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "{name}")
""")
        count += 1

    elif gtype == '8tc':
        # Group 2: Chợ (TC-127..134)
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
        count += 1

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
        count += 1

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
        count += 1

        p130 = get_script_path(130)
        write_script(p130, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-130: Kiểm tra thêm mới dữ liệu biến động Chợ hợp lệ ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.openFluctuationModal("Chợ")
DataMiningPage.addFluctuationData("150000000", "2024")
DataMiningPage.verifyMiningSuccess("Tạo mới thành công")
""")
        count += 1

        p131 = get_script_path(131)
        write_script(p131, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-131: Kiểm tra cập nhập dữ liệu biến động Chợ ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.openFluctuationModal("Chợ")
DataMiningPage.editFluctuationData("180000000")
DataMiningPage.verifyMiningSuccess("Chỉnh sửa thành công")
""")
        count += 1

        p132 = get_script_path(132)
        write_script(p132, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-132: Kiểm tra tìm kiếm dữ liệu biến động Chợ ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.openFluctuationModal("Chợ")
DataMiningPage.searchFluctuationData("2024")
DataMiningPage.verifyFluctuationSearchSuccess(1)
""")
        count += 1

        p133 = get_script_path(133)
        write_script(p133, """import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-133: Kiểm tra chức năng Xóa dữ liệu biến động Chợ ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.openFluctuationModal("Chợ")
DataMiningPage.deleteFluctuationData()
DataMiningPage.verifyMiningSuccess("Xóa thành công")
""")
        count += 1

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
        count += 1

    elif gtype == '7tc':
        # Group 5 to 19 (7 TCs each)
        fluct_title = g['fluct_title']

        # 1. Create (start)
        p_create = get_script_path(start)
        if gid == 5: # CHXD
            write_script(p_create, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start}: Thêm mới {name} thành công ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()
DataMiningPage.selectDataLayer("{name}")
DataMiningPage.drawFeatureOnCanvas("{name}")

String code = DataMiningPage.uniqueCode("{prefix}")
String recordName = "{name} Auto " + (System.currentTimeMillis() % 10000L)
String address = "Số 202 Đường Lê Duẩn, Nghệ An"

DataMiningPage.fillDataAttributes(code, recordName, address)
DataMiningPage.verifyMiningSuccess("Tạo mới thành công dữ liệu cho lớp {name}")

// Tìm kiếm mã sau khi tạo để xác nhận dữ liệu đã lưu vào hệ thống
DataMiningPage.searchByMapLayer(code, "{name}")
DataMiningPage.verifySearchSuccess(1)
""")
        else:
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
        count += 1

        # 2. Edit (start + 1)
        p_edit = get_script_path(start + 1)
        if gid == 5:
            write_script(p_edit, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 1}: Chỉnh sửa dữ liệu thành công ({name}) ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo ở TC trước để chỉnh sửa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
String updatedName = "{name} Cập nhật " + (System.currentTimeMillis() % 10000L)
DataMiningPage.editDataRecord(updatedName, "{name}")
DataMiningPage.verifyMiningSuccess("Cập nhật thành công dữ liệu cho lớp {name}")
""")
        else:
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
        count += 1

        # 3. Search (start + 2) - BẮT BUỘC DÙNG searchByMapLayer VÀ verifySearchSuccess(1)
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
DataMiningPage.searchByMapLayer(trackedCode, "{name}")
DataMiningPage.verifySearchSuccess(1)
""")
        count += 1

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
Map<String, String> fData = [
    'Năm': year,
    'Kỳ': period,
    'Sản lượng': '5000',
    'Doanh thu': '100000000'
]
DataMiningPage.fillFluctuationForm(fData)
DataMiningPage.confirmFluctuationAdd()
DataMiningPage.verifyMiningSuccess("thành công")
""")
        count += 1

        # 5. Fluctuation Edit (start + 4)
        p_fedit = get_script_path(start + 4)
        write_script(p_fedit, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 4}: Kiểm tra cập nhập dữ liệu biến động {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Mở đúng bản ghi theo mã
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.openRecordFromSearch("{name}", trackedCode)

DataMiningPage.openFluctuationByTitle("{fluct_title}")
DataMiningPage.openEditFluctuationRow()

Map<String, String> editData = [
    'Sản lượng': '8000',
    'Ghi chú': 'Cập nhật tự động'
]
DataMiningPage.fillFluctuationForm(editData)
DataMiningPage.confirmFluctuationAdd()
DataMiningPage.verifyMiningSuccess("thành công")
""")
        count += 1

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
        count += 1

        # 7. Delete Root (start + 6)
        p_delete = get_script_path(start + 6)
        if gid == 5:
            write_script(p_delete, f"""import dmit.pages.LoginPage
import dmit.pages.DataMiningPage
import internal.GlobalVariable as GlobalVariable
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.comment("=== TC-{start + 6}: Kiểm tra chức năng Xóa {name} ===")
LoginPage.login(GlobalVariable.USERNAME, GlobalVariable.PASSWORD)
DataMiningPage.goToDataMining()

// Lấy đúng mã bản ghi đã tạo để chọn xóa
String trackedCode = DataMiningPage.getTrackedCode("{name}")
DataMiningPage.closeFluctuationModal()
DataMiningPage.deleteDataRecord("{name}")
DataMiningPage.verifyMiningSuccess("Xóa dữ liệu thành công")

// Tìm kiếm lại dữ liệu đã xóa để xác nhận đã biến mất khỏi hệ thống
DataMiningPage.verifyDeletedRecordNotFound(trackedCode, "{name}")
""")
        else:
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
        count += 1

print(f"Successfully generated and standardized {count} test scripts across 19 groups!")
