#!/usr/bin/env python3
"""
更新服務器 API
提供版本檢查和應用更新下載服務
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify, send_file, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # 允許跨域請求

# 配置
UPLOAD_FOLDER = Path(__file__).parent / 'releases'
METADATA_FILE = Path(__file__).parent / 'releases_metadata.json'
ALLOWED_EXTENSIONS = {'zip'}

UPLOAD_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB 最大上傳大小


class ReleaseManager:
    """發布版本管理器"""

    def __init__(self, metadata_file: Path):
        self.metadata_file = metadata_file
        self.releases = self.load_metadata()

    def load_metadata(self) -> dict:
        """載入版本元數據"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'releases': []}

    def save_metadata(self):
        """保存版本元數據"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.releases, f, indent=2, ensure_ascii=False)

    def add_release(self, version: str, filename: str, file_size: int,
                   md5: str, build_type: str = 'release',
                   release_notes: str = "") -> dict:
        """
        添加新發布版本

        Args:
            version: 版本號
            filename: 文件名
            file_size: 文件大小
            md5: MD5 雜湊值
            build_type: 構建類型
            release_notes: 發布說明

        Returns:
            發布信息字典
        """
        release_info = {
            'version': version,
            'filename': filename,
            'file_size': file_size,
            'md5': md5,
            'build_type': build_type,
            'release_notes': release_notes,
            'publish_date': datetime.now().isoformat(),
        }

        # 檢查是否已存在相同版本
        existing_index = None
        for i, release in enumerate(self.releases['releases']):
            if release['version'] == version:
                existing_index = i
                break

        if existing_index is not None:
            # 更新現有版本
            self.releases['releases'][existing_index] = release_info
        else:
            # 添加新版本
            self.releases['releases'].append(release_info)

        # 按版本號排序（最新的在前面）
        self.releases['releases'].sort(
            key=lambda x: tuple(map(int, x['version'].split('.'))),
            reverse=True
        )

        self.save_metadata()
        return release_info

    def get_latest_release(self, build_type: Optional[str] = None) -> Optional[dict]:
        """
        獲取最新發布版本

        Args:
            build_type: 構建類型過濾（可選）

        Returns:
            最新版本信息或 None
        """
        if not self.releases['releases']:
            return None

        releases = self.releases['releases']
        if build_type:
            releases = [r for r in releases if r['build_type'] == build_type]

        return releases[0] if releases else None

    def get_release_by_version(self, version: str) -> Optional[dict]:
        """根據版本號獲取發布信息"""
        for release in self.releases['releases']:
            if release['version'] == version:
                return release
        return None


# 創建發布管理器實例
release_manager = ReleaseManager(METADATA_FILE)


def allowed_file(filename: str) -> bool:
    """檢查文件擴展名是否允許"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_md5(file_path: Path) -> str:
    """計算文件的 MD5 雜湊值"""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


# ============================================================================
# API 端點
# ============================================================================

@app.route('/api/updates/latest', methods=['GET'])
def get_latest_update():
    """
    獲取最新版本信息

    Query 參數:
        build_type: 構建類型（可選，如: release, beta, alpha）

    返回:
        {
            "version": "2.1.0",
            "download_url": "http://.../download/...",
            "file_size": 123456789,
            "md5": "abc123...",
            "release_notes": "更新說明",
            "publish_date": "2025-01-01T12:00:00"
        }
    """
    build_type = request.args.get('build_type', 'release')

    latest = release_manager.get_latest_release(build_type)
    if not latest:
        return jsonify({'error': 'No releases available'}), 404

    # 生成下載 URL
    download_url = url_for('download_release',
                          filename=latest['filename'],
                          _external=True)

    response = {
        'version': latest['version'],
        'download_url': download_url,
        'file_size': latest['file_size'],
        'md5': latest['md5'],
        'release_notes': latest['release_notes'],
        'publish_date': latest['publish_date'],
        'build_type': latest['build_type']
    }

    return jsonify(response)


@app.route('/api/updates/download/<filename>', methods=['GET'])
def download_release(filename: str):
    """
    下載發布包

    路徑參數:
        filename: 文件名

    返回:
        文件下載
    """
    filename = secure_filename(filename)
    file_path = UPLOAD_FOLDER / filename

    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404

    return send_file(file_path, as_attachment=True)


@app.route('/api/updates/upload', methods=['POST'])
def upload_release():
    """
    上傳新的發布包

    Form 數據:
        file: ZIP 文件（必需）
        version: 版本號（必需）
        build_type: 構建類型（可選，默認: release）
        md5: MD5 雜湊值（可選，服務器會自動計算）
        release_notes: 發布說明（可選）

    返回:
        {
            "success": true,
            "version": "2.1.0",
            "download_url": "http://.../download/..."
        }
    """
    # 檢查文件
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type, only ZIP allowed'}), 400

    # 獲取表單數據
    version = request.form.get('version')
    if not version:
        return jsonify({'error': 'Version is required'}), 400

    build_type = request.form.get('build_type', 'release')
    release_notes = request.form.get('release_notes', '')
    provided_md5 = request.form.get('md5', '')

    # 保存文件
    filename = secure_filename(file.filename)
    # 添加版本號到文件名
    name_parts = filename.rsplit('.', 1)
    filename = f"{name_parts[0]}_v{version}.{name_parts[1]}"

    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    # 計算 MD5
    calculated_md5 = calculate_md5(file_path)

    # 驗證 MD5（如果提供）
    if provided_md5 and provided_md5 != calculated_md5:
        os.remove(file_path)
        return jsonify({'error': 'MD5 checksum mismatch'}), 400

    # 獲取文件大小
    file_size = file_path.stat().st_size

    # 添加到發布管理器
    release_info = release_manager.add_release(
        version=version,
        filename=filename,
        file_size=file_size,
        md5=calculated_md5,
        build_type=build_type,
        release_notes=release_notes
    )

    # 生成下載 URL
    download_url = url_for('download_release',
                          filename=filename,
                          _external=True)

    return jsonify({
        'success': True,
        'version': version,
        'download_url': download_url,
        'file_size': file_size,
        'md5': calculated_md5
    })


@app.route('/api/updates/list', methods=['GET'])
def list_releases():
    """
    列出所有發布版本

    Query 參數:
        build_type: 構建類型過濾（可選）

    返回:
        {
            "releases": [...]
        }
    """
    build_type = request.args.get('build_type')

    releases = release_manager.releases['releases']
    if build_type:
        releases = [r for r in releases if r['build_type'] == build_type]

    return jsonify({'releases': releases})


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'healthy',
        'service': 'Basler Vision Update Server',
        'version': '1.0.0'
    })


@app.route('/', methods=['GET'])
def index():
    """首頁"""
    return '''
    <html>
    <head><title>Basler Vision Update Server</title></head>
    <body>
        <h1>Basler Vision System - Update Server</h1>
        <h2>API 端點</h2>
        <ul>
            <li>GET /api/updates/latest - 獲取最新版本</li>
            <li>GET /api/updates/list - 列出所有版本</li>
            <li>GET /api/updates/download/&lt;filename&gt; - 下載文件</li>
            <li>POST /api/updates/upload - 上傳新版本</li>
            <li>GET /api/health - 健康檢查</li>
        </ul>
    </body>
    </html>
    '''


if __name__ == '__main__':
    # 開發模式運行
    app.run(host='0.0.0.0', port=5000, debug=True)
