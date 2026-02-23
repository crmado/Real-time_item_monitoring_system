#include <QApplication>
#include <QStyleFactory>
#include <QDebug>
#include "ui/main_window.h"

/**
 * Basler 工業視覺系統 - C++ 版本
 *
 * 相比 Python 版本的核心改進：
 * 1. 無 GIL 限制的真正多線程
 * 2. RAII 自動資源管理
 * 3. 狀態機驅動的相機控制
 * 4. 編譯時類型檢查
 */
int main(int argc, char *argv[])
{
    // 高 DPI 支援
    QApplication::setHighDpiScaleFactorRoundingPolicy(
        Qt::HighDpiScaleFactorRoundingPolicy::PassThrough
    );

    QApplication app(argc, argv);

    // 應用程式資訊
    app.setApplicationName("Basler Vision System");
    app.setApplicationVersion("2.0.0");
    app.setOrganizationName("Industrial Vision");

    // 設置 Fusion 風格（跨平台一致性）
    app.setStyle(QStyleFactory::create("Fusion"));

    // 深色主題
    QPalette darkPalette;
    darkPalette.setColor(QPalette::Window, QColor(45, 45, 45));
    darkPalette.setColor(QPalette::WindowText, Qt::white);
    darkPalette.setColor(QPalette::Base, QColor(35, 35, 35));
    darkPalette.setColor(QPalette::AlternateBase, QColor(45, 45, 45));
    darkPalette.setColor(QPalette::ToolTipBase, Qt::white);
    darkPalette.setColor(QPalette::ToolTipText, Qt::white);
    darkPalette.setColor(QPalette::Text, Qt::white);
    darkPalette.setColor(QPalette::Button, QColor(45, 45, 45));
    darkPalette.setColor(QPalette::ButtonText, Qt::white);
    darkPalette.setColor(QPalette::BrightText, Qt::red);
    darkPalette.setColor(QPalette::Link, QColor(42, 130, 218));
    darkPalette.setColor(QPalette::Highlight, QColor(42, 130, 218));
    darkPalette.setColor(QPalette::HighlightedText, Qt::black);
    app.setPalette(darkPalette);

    qDebug() << "========================================";
    qDebug() << "Basler Vision System v2.0.0 (C++)";
    qDebug() << "========================================";

    // 創建主視窗
    basler::MainWindow window;
    window.show();

    return app.exec();
}
