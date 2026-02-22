#include <pylon/PylonIncludes.h>
#include <iostream>

using namespace Pylon;
using namespace std;

int main()
{
    cout << "========================================" << endl;
    cout << "Pylon SDK Camera Detection Test" << endl;
    cout << "========================================" << endl;

    int exitCode = 0;

    // 自動初始化/終止 Pylon
    PylonAutoInitTerm autoInit;

    try
    {
        // 獲取 Transport Layer Factory
        CTlFactory &factory = CTlFactory::GetInstance();

        // 枚舉設備
        DeviceInfoList_t devices;
        int deviceCount = factory.EnumerateDevices(devices);

        cout << "\nFound " << deviceCount << " camera(s):" << endl;

        if (deviceCount == 0)
        {
            cout << "\n[WARNING] No cameras detected!" << endl;
            cout << "Possible causes:" << endl;
            cout << "  1. Camera power is off or still booting (GigE needs 5-10s)" << endl;
            cout << "  2. Network cable not connected" << endl;
            cout << "  3. Firewall blocking GigE Vision protocol" << endl;
            cout << "  4. Check Windows Firewall settings" << endl;
            return 1;
        }

        for (size_t i = 0; i < devices.size(); i++)
        {
            cout << "\n  Camera " << i << ":" << endl;
            cout << "    Model:    " << devices[i].GetModelName() << endl;
            cout << "    Serial:   " << devices[i].GetSerialNumber() << endl;
            cout << "    Name:     " << devices[i].GetFriendlyName() << endl;
            cout << "    Vendor:   " << devices[i].GetVendorName() << endl;
        }

        // 嘗試連接第一個相機
        cout << "\n[TEST] Attempting to connect to camera 0..." << endl;

        CInstantCamera camera(factory.CreateDevice(devices[0]));
        camera.Open();

        cout << "[OK] Successfully connected to: " << camera.GetDeviceInfo().GetFriendlyName() << endl;

        // 獲取一幀測試
        cout << "[TEST] Attempting to grab a single frame..." << endl;

        camera.StartGrabbing(1, GrabStrategy_LatestImageOnly);
        CGrabResultPtr grabResult;

        if (camera.RetrieveResult(5000, grabResult, TimeoutHandling_ThrowException))
        {
            if (grabResult->GrabSucceeded())
            {
                cout << "[OK] Frame grabbed successfully!" << endl;
                cout << "    Size: " << grabResult->GetWidth() << " x " << grabResult->GetHeight() << endl;
                cout << "    Pixel Type: " << grabResult->GetPixelType() << endl;
            }
            else
            {
                cout << "[ERROR] Grab failed: " << grabResult->GetErrorDescription() << endl;
                exitCode = 1;
            }
        }

        camera.Close();
        cout << "\n[OK] Camera test completed successfully!" << endl;
    }
    catch (const GenericException &e)
    {
        cerr << "\n[ERROR] Pylon exception: " << e.GetDescription() << endl;
        exitCode = 1;
    }
    catch (const exception &e)
    {
        cerr << "\n[ERROR] Exception: " << e.what() << endl;
        exitCode = 1;
    }

    cout << "\n========================================" << endl;
    cout << "Press Enter to exit..." << endl;
    cin.get();

    return exitCode;
}
