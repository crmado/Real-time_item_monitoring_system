#include <QApplication>
#include <QStyleFactory>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QStandardPaths>
#include <QDateTime>
#include <QMutex>
#include "ui/main_window.h"
#include "config/settings.h"

// ============================================================================
// 全域 Log 機制：攔截所有 qDebug / qWarning / qCritical 寫入檔案
// ============================================================================
namespace {

QFile   g_logFile;
QMutex  g_logMutex;

void messageHandler(QtMsgType type, const QMessageLogContext& /*ctx*/, const QString& msg)
{
    const char* prefix = "";
    switch (type) {
        case QtDebugMsg:    prefix = "[D]"; break;
        case QtInfoMsg:     prefix = "[I]"; break;
        case QtWarningMsg:  prefix = "[W]"; break;
        case QtCriticalMsg: prefix = "[C]"; break;
        case QtFatalMsg:    prefix = "[F]"; break;
    }

    const QString line = QString("%1 %2 %3\n")
        .arg(QDateTime::currentDateTime().toString("HH:mm:ss.zzz"))
        .arg(prefix)
        .arg(msg);

    // 寫入終端機（原有行為）
    fprintf(stderr, "%s", line.toLocal8Bit().constData());

    // 寫入 log 檔（thread-safe）
    QMutexLocker locker(&g_logMutex);
    if (g_logFile.isOpen()) {
        g_logFile.write(line.toUtf8());
        g_logFile.flush();
    }
}

} // namespace

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

    // ── Log 檔初始化 ──────────────────────────────────────────────
    // macOS app bundle: applicationDirPath() = .../build/BaslerVisionSystem.app/Contents/MacOS
    // 向上三層到 build/，再進 logs/  →  basler_cpp/build/logs/
    {
        QString exeDir = QCoreApplication::applicationDirPath();
#ifdef Q_OS_MAC
        // .app bundle: Contents/MacOS → 上三層到 build 目錄
        QDir logsDir(exeDir + "/../../../logs");
#else
        QDir logsDir(exeDir + "/logs");
#endif
        logsDir.mkpath(".");
        const QString logPath = logsDir.absolutePath() + "/debug_"
                                + QDate::currentDate().toString("yyyyMMdd") + ".log";
        g_logFile.setFileName(logPath);
        g_logFile.open(QIODevice::Append | QIODevice::Text);
        if (g_logFile.isOpen()) {
            g_logFile.write(QString("\n===== 啟動 %1 =====\n")
                .arg(QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss"))
                .toUtf8());
        }
    }
    qInstallMessageHandler(messageHandler);

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

    // 載入使用者配置（必須在 MainWindow 建立前執行，讓 VibratorControlWidget 讀到正確的設備列表）
    basler::AppConfig::instance().load();

    // 創建主視窗
    basler::MainWindow window;
    window.show();

    return app.exec();
}
