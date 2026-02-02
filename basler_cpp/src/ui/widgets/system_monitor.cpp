#include "ui/widgets/system_monitor.h"
#include <QVBoxLayout>
#include <QProcess>

#ifdef Q_OS_MAC
#include <mach/mach.h>
#include <mach/processor_info.h>
#include <mach/mach_host.h>
#endif

#ifdef Q_OS_LINUX
#include <fstream>
#include <string>
#endif

namespace basler {

SystemMonitorWidget::SystemMonitorWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();

    m_updateTimer = new QTimer(this);
    connect(m_updateTimer, &QTimer::timeout, this, &SystemMonitorWidget::updateStats);
}

void SystemMonitorWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    m_groupBox = new QGroupBox(tr("📊 系統監控"));
    QVBoxLayout* groupLayout = new QVBoxLayout();

    // CPU 使用率
    QHBoxLayout* cpuLayout = new QHBoxLayout();
    cpuLayout->addWidget(new QLabel(tr("CPU:")));
    m_cpuLabel = new QLabel("0%");
    m_cpuLabel->setMinimumWidth(40);
    cpuLayout->addWidget(m_cpuLabel);

    m_cpuBar = new QProgressBar();
    m_cpuBar->setRange(0, 100);
    m_cpuBar->setValue(0);
    m_cpuBar->setTextVisible(false);
    m_cpuBar->setMaximumHeight(15);
    cpuLayout->addWidget(m_cpuBar);
    groupLayout->addLayout(cpuLayout);

    // 記憶體使用率
    QHBoxLayout* memLayout = new QHBoxLayout();
    memLayout->addWidget(new QLabel(tr("RAM:")));
    m_memLabel = new QLabel("0%");
    m_memLabel->setMinimumWidth(40);
    memLayout->addWidget(m_memLabel);

    m_memBar = new QProgressBar();
    m_memBar->setRange(0, 100);
    m_memBar->setValue(0);
    m_memBar->setTextVisible(false);
    m_memBar->setMaximumHeight(15);
    memLayout->addWidget(m_memBar);
    groupLayout->addLayout(memLayout);

    m_groupBox->setLayout(groupLayout);
    mainLayout->addWidget(m_groupBox);
    mainLayout->addStretch();
}

void SystemMonitorWidget::setUpdateInterval(int ms)
{
    m_updateInterval = ms;
    if (m_updateTimer->isActive()) {
        m_updateTimer->setInterval(ms);
    }
}

void SystemMonitorWidget::startMonitoring()
{
    m_updateTimer->start(m_updateInterval);
    updateStats();
}

void SystemMonitorWidget::stopMonitoring()
{
    m_updateTimer->stop();
}

void SystemMonitorWidget::updateStats()
{
    double cpu = getCpuUsage();
    double mem = getMemoryUsage();

    m_cpuLabel->setText(QString("%1%").arg(static_cast<int>(cpu)));
    m_cpuBar->setValue(static_cast<int>(cpu));

    m_memLabel->setText(QString("%1%").arg(static_cast<int>(mem)));
    m_memBar->setValue(static_cast<int>(mem));

    // 根據使用率改變顏色
    QString cpuStyle = (cpu > 80) ? "QProgressBar::chunk { background-color: #ff4444; }" :
                       (cpu > 50) ? "QProgressBar::chunk { background-color: #ffaa00; }" :
                                    "QProgressBar::chunk { background-color: #00aa00; }";
    m_cpuBar->setStyleSheet(cpuStyle);

    QString memStyle = (mem > 80) ? "QProgressBar::chunk { background-color: #ff4444; }" :
                       (mem > 50) ? "QProgressBar::chunk { background-color: #ffaa00; }" :
                                    "QProgressBar::chunk { background-color: #00aa00; }";
    m_memBar->setStyleSheet(memStyle);
}

double SystemMonitorWidget::getCpuUsage()
{
#ifdef Q_OS_MAC
    // macOS 實現
    host_cpu_load_info_data_t cpuInfo;
    mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;

    if (host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO,
                        (host_info_t)&cpuInfo, &count) == KERN_SUCCESS) {
        qint64 user = cpuInfo.cpu_ticks[CPU_STATE_USER];
        qint64 sys = cpuInfo.cpu_ticks[CPU_STATE_SYSTEM];
        qint64 idle = cpuInfo.cpu_ticks[CPU_STATE_IDLE];
        qint64 nice = cpuInfo.cpu_ticks[CPU_STATE_NICE];

        qint64 total = user + sys + idle + nice;
        qint64 used = user + sys + nice;

        if (m_lastCpuTime > 0) {
            qint64 totalDiff = total - m_lastCpuTime;
            qint64 idleDiff = idle - m_lastIdleTime;

            if (totalDiff > 0) {
                double usage = 100.0 * (1.0 - static_cast<double>(idleDiff) / totalDiff);
                m_lastCpuTime = total;
                m_lastIdleTime = idle;
                return usage;
            }
        }

        m_lastCpuTime = total;
        m_lastIdleTime = idle;
    }
    return 0.0;

#elif defined(Q_OS_LINUX)
    // Linux 實現
    std::ifstream statFile("/proc/stat");
    std::string line;
    if (std::getline(statFile, line)) {
        // 解析 CPU 行
        // cpu  user nice system idle iowait irq softirq
        // ... 簡化實現
    }
    return 0.0;

#else
    return 0.0;
#endif
}

double SystemMonitorWidget::getMemoryUsage()
{
#ifdef Q_OS_MAC
    // macOS 實現
    vm_size_t pageSize;
    vm_statistics64_data_t vmStats;
    mach_msg_type_number_t count = sizeof(vmStats) / sizeof(natural_t);

    host_page_size(mach_host_self(), &pageSize);

    if (host_statistics64(mach_host_self(), HOST_VM_INFO64,
                          (host_info64_t)&vmStats, &count) == KERN_SUCCESS) {
        qint64 free = vmStats.free_count * pageSize;
        qint64 active = vmStats.active_count * pageSize;
        qint64 inactive = vmStats.inactive_count * pageSize;
        qint64 wired = vmStats.wire_count * pageSize;

        qint64 total = free + active + inactive + wired;
        qint64 used = active + wired;

        if (total > 0) {
            return 100.0 * static_cast<double>(used) / total;
        }
    }
    return 0.0;

#elif defined(Q_OS_LINUX)
    // Linux 實現
    std::ifstream memFile("/proc/meminfo");
    // ... 解析 MemTotal, MemFree, etc.
    return 0.0;

#else
    return 0.0;
#endif
}

} // namespace basler
