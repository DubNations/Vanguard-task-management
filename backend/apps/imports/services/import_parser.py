"""
导入文件解析器 — 支持 xlsx/csv/wps。
"""
import csv
import io
import os
from openpyxl import load_workbook


# 标准列名 → 字段映射
DEFAULT_COLUMN_MAPPING = {
    '标题': 'title',
    '任务标题': 'title',
    'task': 'title',
    'title': 'title',
    '负责人': 'assignee_name',
    '执行人': 'assignee_name',
    'assignee': 'assignee_name',
    '截止日期': 'deadline',
    '到期日': 'deadline',
    'deadline': 'deadline',
    '状态': 'status',
    'status': 'status',
    '优先级': 'priority',
    'priority': 'priority',
    '进度': 'progress',
    'progress': 'progress',
    '备注': 'description',
    '描述': 'description',
    'description': 'description',
}


def parse_import_file(session):
    """解析导入文件，返回预览数据。"""
    file_path = session.file.path
    ext = session.file_format

    if ext in ('xlsx', 'xls', 'wps'):
        return _parse_xlsx(file_path, ext)
    elif ext == 'csv':
        return _parse_csv(file_path)
    else:
        raise ValueError(f'不支持的文件格式: {ext}')


def _parse_xlsx(file_path, ext='xlsx'):
    """解析 Excel / WPS 文件。WPS 先尝试直接读取（新版兼容），失败则走 libreoffice 转换。"""
    # 先尝试直接用 openpyxl 打开（xlsx 和新版 wps 兼容）
    try:
        wb = load_workbook(file_path, read_only=True, data_only=True)
    except Exception:
        if ext == 'wps':
            # 旧版 .wps 格式，需要 libreoffice 转换
            return _parse_wps_via_libreoffice(file_path)
        raise

    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return _empty_result()

    # 第一行是表头
    headers = [str(h).strip() if h else '' for h in rows[0]]
    mapping = _build_mapping(headers)

    data_rows = rows[1:]
    preview = []
    errors = []
    valid = 0

    for idx, row in enumerate(data_rows, start=2):
        record = {}
        for col_idx, header in enumerate(headers):
            if col_idx < len(row) and header in mapping:
                record[mapping[header]] = str(row[col_idx]) if row[col_idx] is not None else ''

        # 验证
        row_errors = _validate_row(idx, record)
        if row_errors:
            errors.extend(row_errors)
        else:
            valid += 1

        preview.append({
            'row': idx,
            'data': record,
            'valid': len(row_errors) == 0,
        })

    wb.close()

    return {
        'total_rows': len(data_rows),
        'valid_rows': valid,
        'error_rows': len(data_rows) - valid,
        'preview_data': preview,
        'column_mapping': mapping,
        'errors': errors,
    }


def _parse_csv(file_path):
    """解析 CSV 文件。"""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return _empty_result()

    headers = [h.strip() for h in rows[0]]
    mapping = _build_mapping(headers)

    data_rows = rows[1:]
    preview = []
    errors = []
    valid = 0

    for idx, row in enumerate(data_rows, start=2):
        record = {}
        for col_idx, header in enumerate(headers):
            if col_idx < len(row) and header in mapping:
                record[mapping[header]] = row[col_idx].strip()

        row_errors = _validate_row(idx, record)
        if row_errors:
            errors.extend(row_errors)
        else:
            valid += 1

        preview.append({
            'row': idx,
            'data': record,
            'valid': len(row_errors) == 0,
        })

    return {
        'total_rows': len(data_rows),
        'valid_rows': valid,
        'error_rows': len(data_rows) - valid,
        'preview_data': preview,
        'column_mapping': mapping,
        'errors': errors,
    }


def _parse_wps_via_libreoffice(file_path):
    """旧版 .wps 格式 — 通过 libreoffice 转 xlsx 后解析。"""
    import subprocess
    import tempfile
    import shutil

    tmp_dir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'xlsx', '--outdir', tmp_dir, file_path],
            capture_output=True, timeout=60,
        )
        if result.returncode != 0:
            raise ValueError(
                'WPS 文件无法直接解析，且 libreoffice 未安装或转换失败。'
                '建议将 .wps 文件另存为 .xlsx 格式后重新上传。'
            )
        converted = os.path.join(tmp_dir, os.path.splitext(os.path.basename(file_path))[0] + '.xlsx')
        if not os.path.exists(converted):
            raise ValueError(
                'WPS 文件转换失败。建议将 .wps 文件另存为 .xlsx 格式后重新上传。'
            )
        return _parse_xlsx(converted)
    except FileNotFoundError:
        raise ValueError(
            'WPS 文件无法直接解析，且未安装 libreoffice。'
            '建议将 .wps 文件在 WPS Office 中另存为 .xlsx 格式后重新上传。'
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _build_mapping(headers):
    """自动匹配列名到字段。"""
    mapping = {}
    for header in headers:
        normalized = header.lower().strip()
        if normalized in DEFAULT_COLUMN_MAPPING:
            mapping[header] = DEFAULT_COLUMN_MAPPING[normalized]
        elif header in DEFAULT_COLUMN_MAPPING:
            mapping[header] = DEFAULT_COLUMN_MAPPING[header]
    return mapping


def _validate_row(row_num, record):
    """验证单行数据。"""
    errors = []
    title = record.get('title', '').strip()
    if not title:
        errors.append({'row': row_num, 'field': 'title', 'message': '标题不能为空'})

    priority = record.get('priority', '')
    if priority and priority not in ('LOW', 'MEDIUM', 'HIGH', 'URGENT', '低', '中', '高', '紧急'):
        errors.append({'row': row_num, 'field': 'priority', 'message': f'无效的优先级: {priority}'})

    return errors


def _empty_result():
    return {
        'total_rows': 0,
        'valid_rows': 0,
        'error_rows': 0,
        'preview_data': [],
        'column_mapping': {},
        'errors': [{'row': 0, 'message': '文件为空'}],
    }
