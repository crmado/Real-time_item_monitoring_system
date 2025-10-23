# 🐧 Linux 安裝指南

## 📦 安裝方式

### 方式 1：從 tar.gz 安裝（當前可用）

如果您下載的是 `BaslerVision_*.tar.gz` 文件：

```bash
# 1. 解壓縮文件
tar -xzf BaslerVision_*.tar.gz
cd usr/bin  # 進入解壓後的目錄

# 2. 添加執行權限
chmod +x BaslerVisionSystem

# 3. 安裝系統依賴（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install -y \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    libglib2.0-0

# 4. 運行應用程式
./BaslerVisionSystem
```

### 方式 2：創建系統快捷方式（可選）

```bash
# 1. 移動到系統目錄
sudo mkdir -p /opt/BaslerVision
sudo cp -R * /opt/BaslerVision/

# 2. 創建桌面快捷方式
cat > ~/.local/share/applications/baslervision.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Basler Vision System
Comment=工業視覺檢測系統
Exec=/opt/BaslerVision/BaslerVisionSystem
Icon=/opt/BaslerVision/icon.png
Categories=Utility;Development;
Terminal=false
EOF

# 3. 更新桌面資料庫
update-desktop-database ~/.local/share/applications/

# 現在可以從應用程式選單啟動
```

### 方式 3：創建命令行別名（可選）

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'alias baslervision="/opt/BaslerVision/BaslerVisionSystem"' >> ~/.bashrc
source ~/.bashrc

# 現在可以在任何地方執行
baslervision
```

## 🔧 系統要求

### 必需依賴

- **操作系統**: Ubuntu 20.04+ / Debian 11+ / 其他主流 Linux 發行版
- **架構**: x86_64 (64-bit)
- **Python**: 已包含在打包中（無需安裝）

### Qt/GUI 依賴

```bash
# Ubuntu/Debian
sudo apt-get install -y \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libgl1-mesa-glx

# Fedora/RHEL
sudo dnf install -y \
    xcb-util-wm \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    mesa-libGL

# Arch Linux
sudo pacman -S \
    libxcb \
    xcb-util-wm \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    mesa
```

## 🐛 故障排除

### 問題 1：權限被拒絕

```bash
# 確保文件有執行權限
chmod +x BaslerVisionSystem
```

### 問題 2：缺少共享庫

```bash
# 檢查缺少哪些庫
ldd BaslerVisionSystem | grep "not found"

# 安裝缺失的庫（以 Ubuntu 為例）
sudo apt-get install -y $(ldd BaslerVisionSystem | grep "not found" | awk '{print $1}' | xargs)
```

### 問題 3：顯示問題

```bash
# 設置 Qt 平台插件環境變數
export QT_QPA_PLATFORM=xcb
./BaslerVisionSystem

# 如果仍有問題，嘗試 wayland
export QT_QPA_PLATFORM=wayland
./BaslerVisionSystem
```

### 問題 4：無法連接到顯示器

```bash
# 確保 DISPLAY 環境變數已設置
echo $DISPLAY

# 如果為空，設置它
export DISPLAY=:0
```

## 📋 完整安裝腳本

創建並運行此腳本以自動安裝：

```bash
#!/bin/bash
# install_baslervision.sh

set -e  # 遇到錯誤立即退出

echo "🚀 開始安裝 Basler Vision System..."

# 檢查是否為 root
if [ "$EUID" -eq 0 ]; then
   echo "⚠️  請不要以 root 身份運行此腳本"
   exit 1
fi

# 檢測發行版
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    echo "❌ 無法檢測 Linux 發行版"
    exit 1
fi

# 安裝依賴
echo "📦 安裝系統依賴..."
case $DISTRO in
    ubuntu|debian)
        sudo apt-get update
        sudo apt-get install -y \
            libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 \
            libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
            libgl1-mesa-glx libglib2.0-0
        ;;
    fedora|rhel|centos)
        sudo dnf install -y \
            xcb-util-wm xcb-util-image xcb-util-keysyms \
            mesa-libGL glib2
        ;;
    arch|manjaro)
        sudo pacman -S --noconfirm \
            libxcb xcb-util-wm xcb-util-image \
            xcb-util-keysyms mesa glib2
        ;;
    *)
        echo "⚠️  未識別的發行版: $DISTRO"
        echo "請手動安裝 Qt5/Qt6 依賴"
        ;;
esac

# 解壓應用程式
echo "📂 解壓應用程式..."
TAR_FILE=$(ls BaslerVision_*.tar.gz 2>/dev/null | head -1)
if [ -z "$TAR_FILE" ]; then
    echo "❌ 找不到 BaslerVision_*.tar.gz 文件"
    echo "請確保您在下載目錄中運行此腳本"
    exit 1
fi

tar -xzf "$TAR_FILE"

# 安裝到系統
echo "📥 安裝到 /opt/BaslerVision..."
sudo mkdir -p /opt/BaslerVision
sudo cp -R usr/bin/* /opt/BaslerVision/
sudo chmod +x /opt/BaslerVision/BaslerVisionSystem

# 創建桌面快捷方式
echo "🖥️  創建桌面快捷方式..."
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/baslervision.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Basler Vision System
Comment=工業視覺檢測系統
Exec=/opt/BaslerVision/BaslerVisionSystem
Terminal=false
Categories=Utility;Development;
EOF

# 更新桌面資料庫
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database ~/.local/share/applications/
fi

# 創建命令行別名
echo "⚡ 創建命令行別名..."
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "alias baslervision=" "$SHELL_RC"; then
        echo "alias baslervision='/opt/BaslerVision/BaslerVisionSystem'" >> "$SHELL_RC"
    fi
fi

echo ""
echo "✅ 安裝完成！"
echo ""
echo "啟動方式："
echo "  1. 從應用程式選單中搜尋 'Basler Vision System'"
echo "  2. 在終端中執行: /opt/BaslerVision/BaslerVisionSystem"
echo "  3. 在終端中執行: baslervision (重新啟動終端後生效)"
echo ""
```

使用方式：

```bash
# 1. 下載並解壓 tar.gz 文件
tar -xzf BaslerVision_*.tar.gz

# 2. 創建安裝腳本
nano install_baslervision.sh
# (複製上面的腳本內容)

# 3. 添加執行權限
chmod +x install_baslervision.sh

# 4. 運行安裝
./install_baslervision.sh
```

## 🔄 卸載

```bash
# 刪除應用程式
sudo rm -rf /opt/BaslerVision

# 刪除桌面快捷方式
rm ~/.local/share/applications/baslervision.desktop

# 刪除命令行別名（手動編輯）
nano ~/.bashrc  # 或 ~/.zshrc
# 移除包含 'baslervision' 的行
```

## 📚 相關資源

- [主 README](README.md)
- [發布說明](RELEASE.md)
- [GitHub Issues](https://github.com/你的用戶名/專案名/issues)
