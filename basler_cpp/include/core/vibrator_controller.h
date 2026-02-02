#ifndef VIBRATOR_CONTROLLER_H
#define VIBRATOR_CONTROLLER_H

#include <QObject>
#include <QString>
#include <memory>

namespace basler {

/**
 * @brief 震動機速度枚舉（與 detection_controller.h 中的一致）
 */
enum class VibratorSpeed;

/**
 * @brief 震動機控制器基類（抽象接口）
 *
 * 定義震動機控制的統一接口
 * 支持模擬控制器和實際硬體控制器
 */
class VibratorControllerBase : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool isRunning READ isRunning NOTIFY runningStateChanged)
    Q_PROPERTY(int speedPercent READ speedPercent NOTIFY speedChanged)

public:
    explicit VibratorControllerBase(const QString& name = "Vibrator", QObject* parent = nullptr);
    virtual ~VibratorControllerBase() = default;

    // 禁止複製
    VibratorControllerBase(const VibratorControllerBase&) = delete;
    VibratorControllerBase& operator=(const VibratorControllerBase&) = delete;

    // 狀態查詢
    QString name() const { return m_name; }
    bool isRunning() const { return m_isRunning; }
    int speedPercent() const { return m_speedPercent; }

public slots:
    /**
     * @brief 啟動震動機
     */
    virtual void start() = 0;

    /**
     * @brief 停止震動機
     */
    virtual void stop() = 0;

    /**
     * @brief 設置速度（百分比）
     * @param percent 0-100
     */
    virtual void setSpeedPercent(int percent) = 0;

    /**
     * @brief 設置速度（枚舉）
     * @param speed 速度枚舉
     */
    virtual void setSpeed(VibratorSpeed speed);

signals:
    void runningStateChanged(bool isRunning);
    void speedChanged(int speedPercent);
    void error(const QString& message);

protected:
    QString m_name;
    bool m_isRunning = false;
    int m_speedPercent = 0;
};

/**
 * @brief 模擬震動機控制器
 *
 * 用於開發和測試環境，不需要實際硬體
 */
class SimulatedVibratorController : public VibratorControllerBase {
    Q_OBJECT

public:
    explicit SimulatedVibratorController(const QString& name = "SimulatedVibrator", QObject* parent = nullptr);

public slots:
    void start() override;
    void stop() override;
    void setSpeedPercent(int percent) override;
};

/**
 * @brief 雙震動機管理器
 *
 * 管理兩個震動機（震動機A和震動機B）的同步控制
 */
class DualVibratorManager : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool isRunning READ isRunning NOTIFY runningStateChanged)

public:
    explicit DualVibratorManager(
        std::unique_ptr<VibratorControllerBase> vibrator1,
        std::unique_ptr<VibratorControllerBase> vibrator2,
        QObject* parent = nullptr
    );
    ~DualVibratorManager() = default;

    // 禁止複製
    DualVibratorManager(const DualVibratorManager&) = delete;
    DualVibratorManager& operator=(const DualVibratorManager&) = delete;

    // 狀態查詢
    bool isRunning() const { return m_isRunning; }
    VibratorControllerBase* vibrator1() const { return m_vibrator1.get(); }
    VibratorControllerBase* vibrator2() const { return m_vibrator2.get(); }

    struct DualStatus {
        struct {
            bool isRunning;
            int speedPercent;
        } vibrator1, vibrator2;
    };
    DualStatus getStatus() const;

public slots:
    /**
     * @brief 同時啟動兩個震動機
     */
    void start();

    /**
     * @brief 同時停止兩個震動機
     */
    void stop();

    /**
     * @brief 同時設置兩個震動機的速度
     * @param speed 速度枚舉
     */
    void setSpeed(VibratorSpeed speed);

    /**
     * @brief 同時設置兩個震動機的速度百分比
     * @param percent 0-100
     */
    void setSpeedPercent(int percent);

signals:
    void runningStateChanged(bool isRunning);
    void speedChanged(VibratorSpeed speed);

private:
    std::unique_ptr<VibratorControllerBase> m_vibrator1;
    std::unique_ptr<VibratorControllerBase> m_vibrator2;
    bool m_isRunning = false;
};

/**
 * @brief 工廠函數：創建震動機控制器
 * @param type "simulated" 或 "hardware"
 * @param name 控制器名稱
 * @return 控制器指針
 */
std::unique_ptr<VibratorControllerBase> createVibratorController(
    const QString& type = "simulated",
    const QString& name = "Vibrator"
);

/**
 * @brief 工廠函數：創建雙震動機管理器
 * @param controllerType "simulated" 或 "hardware"
 * @param name1 震動機1名稱
 * @param name2 震動機2名稱
 * @return 管理器指針
 */
std::unique_ptr<DualVibratorManager> createDualVibratorManager(
    const QString& controllerType = "simulated",
    const QString& name1 = "震動機A",
    const QString& name2 = "震動機B"
);

} // namespace basler

#endif // VIBRATOR_CONTROLLER_H
