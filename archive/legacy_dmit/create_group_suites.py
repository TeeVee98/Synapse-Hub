import os, glob, uuid

groups = [
    {'id': 1, 'slug': 'Group_07_01_CumCongNghiep', 'name': 'Cụm công nghiệp', 'start': 123, 'end': 126},
    {'id': 2, 'slug': 'Group_07_02_Cho', 'name': 'Chợ', 'start': 127, 'end': 134},
    {'id': 3, 'slug': 'Group_07_03_SieuThi', 'name': 'Siêu thị', 'start': 135, 'end': 138},
    {'id': 4, 'slug': 'Group_07_04_NguonDien', 'name': 'Nguồn điện', 'start': 139, 'end': 142},
    {'id': 5, 'slug': 'Group_07_05_CHXD', 'name': 'Cửa hàng xăng dầu', 'start': 143, 'end': 149},
    {'id': 6, 'slug': 'Group_07_06_TNPP', 'name': 'Thương nhân phân phối xăng dầu', 'start': 150, 'end': 156},
    {'id': 7, 'slug': 'Group_07_07_VLN', 'name': 'Doanh nghiệp sử dụng vật liệu nổ công nghiệp', 'start': 157, 'end': 163},
    {'id': 8, 'slug': 'Group_07_08_HoaChat', 'name': 'Doanh nghiệp hoá chất', 'start': 164, 'end': 170},
    {'id': 9, 'slug': 'Group_07_09_CHTL', 'name': 'Cửa hàng tiện lợi', 'start': 171, 'end': 177},
    {'id': 10, 'slug': 'Group_07_10_TTTM', 'name': 'Trung tâm thương mại', 'start': 178, 'end': 184},
    {'id': 11, 'slug': 'Group_07_11_DaCap_1', 'name': 'Doanh nghiệp bán hàng đa cấp Nhóm 1', 'start': 185, 'end': 191},
    {'id': 12, 'slug': 'Group_07_12_Logistics', 'name': 'Trung tâm Logistics', 'start': 192, 'end': 198},
    {'id': 13, 'slug': 'Group_07_13_BanLeRuou', 'name': 'Thương nhân bán lẻ rượu', 'start': 199, 'end': 205},
    {'id': 14, 'slug': 'Group_07_14_TMDT', 'name': 'Doanh nghiệp thương mại điện tử', 'start': 206, 'end': 212},
    {'id': 15, 'slug': 'Group_07_15_ThuocLa', 'name': 'Thương nhân bán buôn thuốc lá', 'start': 213, 'end': 219},
    {'id': 16, 'slug': 'Group_07_16_HTX', 'name': 'Hợp tác xã', 'start': 220, 'end': 226},
    {'id': 17, 'slug': 'Group_07_17_DaCap_2', 'name': 'Doanh nghiệp bán hàng đa cấp Nhóm 2', 'start': 227, 'end': 233},
    {'id': 18, 'slug': 'Group_07_18_KinhDoanhKhi', 'name': 'Doanh nghiệp kinh doanh khí', 'start': 234, 'end': 240},
    {'id': 19, 'slug': 'Group_07_19_ThucPhamNhoLe', 'name': 'Cơ sở sản xuất, kinh doanh thực phẩm nhỏ, lẻ', 'start': 241, 'end': 247}
]

def get_tc_name(tc_num):
    files = glob.glob(f'Test Cases/TC-{tc_num} *.tc')
    if files:
        base = os.path.basename(files[0])
        return base[:-3] # strip .tc
    raise FileNotFoundError(f'TC-{tc_num} not found')

os.makedirs('Test Suites', exist_ok=True)

for g in groups:
    suite_name = g['slug']
    ts_file = f'Test Suites/{suite_name}.ts'
    groovy_file = f'Test Suites/{suite_name}.groovy'
    
    suite_guid = str(uuid.uuid4())
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<TestSuiteEntity>',
        f'   <description>Kiểm thử chuyên biệt bộ {g["name"]} (TC-{g["start"]} đến TC-{g["end"]})</description>',
        f'   <name>{suite_name}</name>',
        '   <tag></tag>',
        '   <isRerun>false</isRerun>',
        '   <mailRecipient></mailRecipient>',
        '   <maxConcurrentInstances>1</maxConcurrentInstances>',
        '   <numberOfRerun>0</numberOfRerun>',
        '   <orchestration>CLASSIC</orchestration>',
        '   <pageLoadTimeout>15</pageLoadTimeout>',
        '   <pageLoadTimeoutDefault>true</pageLoadTimeoutDefault>',
        '   <rerunFailedTestCasesOnly>false</rerunFailedTestCasesOnly>',
        '   <rerunImmediately>false</rerunImmediately>',
        f'   <testSuiteGuid>{suite_guid}</testSuiteGuid>'
    ]
    
    for tc in range(g['start'], g['end'] + 1):
        tc_name = get_tc_name(tc)
        tc_guid = str(uuid.uuid4())
        xml_lines.extend([
            '   <testCaseLink>',
            f'      <guid>{tc_guid}</guid>',
            '      <isReuseDriver>true</isReuseDriver>',
            '      <isRun>true</isRun>',
            f'      <testCaseId>Test Cases/{tc_name}</testCaseId>',
            '      <usingDataBindingAtTestSuiteLevel>false</usingDataBindingAtTestSuiteLevel>',
            '   </testCaseLink>'
        ])
    xml_lines.append('</TestSuiteEntity>\n')
    
    with open(ts_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(xml_lines))
        
    groovy_content = """import com.kms.katalon.core.annotation.SetUp
import com.kms.katalon.core.annotation.SetupTestCase
import com.kms.katalon.core.annotation.TearDown
import com.kms.katalon.core.annotation.TearDownTestCase

@SetUp(skipped = true)
def setUp() {
}

@TearDown(skipped = true)
def tearDown() {
}

@SetupTestCase(skipped = true)
def setupTestCase() {
}

@TearDownTestCase(skipped = true)
def tearDownTestCase() {
}
"""
    with open(groovy_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(groovy_content)

print(f"Created {len(groups)} Test Suites successfully!")
