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

print("Helper script ready.")
