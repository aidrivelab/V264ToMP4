@echo off
echo ========================================
echo V264ToMP4 构建脚本
echo ========================================
echo.

:: 设置变量
set VERSION=1.0.0
set BUILD_DIR=build
set DIST_DIR=dist
set PORTABLE_DIR=V264ToMP4_Portable_v%VERSION%
set INSTALLER_DIR=V264ToMP4_Installer_v%VERSION%

:: 清理之前的构建
echo 清理之前的构建文件...
if exist %BUILD_DIR% rmdir /s /q %BUILD_DIR%
if exist %DIST_DIR% rmdir /s /q %DIST_DIR%
if exist %PORTABLE_DIR% rmdir /s /q %PORTABLE_DIR%
if exist %INSTALLER_DIR% rmdir /s /q %INSTALLER_DIR%

:: 创建必要的目录
echo 创建构建目录...
mkdir %BUILD_DIR%
mkdir %DIST_DIR%
mkdir %PORTABLE_DIR%

:: 检查Python环境
echo 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python环境，请先安装Python
    pause
    exit /b 1
)

:: 安装依赖
echo 安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

:: 使用PyInstaller打包
echo 使用PyInstaller打包应用程序...
pyinstaller --name V264ToMP4 ^
            --windowed ^
            --icon=assets/icon.ico ^
            --add-data "assets;assets" ^
            --add-data "config.json;." ^
            --add-data "VERSION.json;." ^
            --add-data "LICENSE;." ^
            --add-data "README.md;." ^
            --add-data "CHANGELOG.md;." ^
            --add-data "INSTALLATION_AND_USAGE.md;." ^
            --add-data "RELEASE_NOTES.md;." ^
            --distpath %DIST_DIR% ^
            --workpath %BUILD_DIR% ^
            --specpath %BUILD_DIR% ^
            main.py

if %errorlevel% neq 0 (
    echo 错误: 打包失败
    pause
    exit /b 1
)

:: 创建便携版
echo 创建便携版...
xcopy %DIST_DIR%\V264ToMP4\* %PORTABLE_DIR%\ /E /I /H /Y
echo @echo off > %PORTABLE_DIR%\start.bat
echo start "" V264ToMP4.exe >> %PORTABLE_DIR%\start.bat

:: 创建便携版压缩包
echo 创建便携版压缩包...
if exist %PORTABLE_DIR%.zip del %PORTABLE_DIR%.zip
powershell -command "Compress-Archive -Path %PORTABLE_DIR% -DestinationPath %PORTABLE_DIR%.zip"

:: 创建安装程序目录结构
echo 创建安装程序目录结构...
mkdir %INSTALLER_DIR%
mkdir %INSTALLER_DIR%\files
xcopy %PORTABLE_DIR%\* %INSTALLER_DIR%\files\ /E /I /H /Y

:: 创建安装脚本
echo 创建安装脚本...
echo @echo off > %INSTALLER_DIR%\install.bat
echo echo 正在安装V264ToMP4... >> %INSTALLER_DIR%\install.bat
echo set INSTALL_DIR=%%PROGRAMFILES%%\V264ToMP4 >> %INSTALLER_DIR%\install.bat
echo if not exist "%%INSTALL_DIR%%" mkdir "%%INSTALL_DIR%%" >> %INSTALLER_DIR%\install.bat
echo xcopy files\* "%%INSTALL_DIR%%\" /E /I /H /Y >> %INSTALLER_DIR%\install.bat
echo echo 创建桌面快捷方式... >> %INSTALLER_DIR%\install.bat
echo powershell -command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%%PUBLIC%%\Desktop\V264ToMP4.lnk'); $Shortcut.TargetPath = '%%INSTALL_DIR%%\V264ToMP4.exe'; $Shortcut.Save()" >> %INSTALLER_DIR%\install.bat
echo echo 创建开始菜单快捷方式... >> %INSTALLER_DIR%\install.bat
echo if not exist "%%PROGRAMDATA%%\Microsoft\Windows\Start Menu\Programs\V264ToMP4" mkdir "%%PROGRAMDATA%%\Microsoft\Windows\Start Menu\Programs\V264ToMP4" >> %INSTALLER_DIR%\install.bat
echo powershell -command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%%PROGRAMDATA%%\Microsoft\Windows\Start Menu\Programs\V264ToMP4\V264ToMP4.lnk'); $Shortcut.TargetPath = '%%INSTALL_DIR%%\V264ToMP4.exe'; $Shortcut.Save()" >> %INSTALLER_DIR%\install.bat
echo echo 安装完成！ >> %INSTALLER_DIR%\install.bat
echo pause >> %INSTALLER_DIR%\install.bat

:: 创建卸载脚本
echo 创建卸载脚本...
echo @echo off > %INSTALLER_DIR%\uninstall.bat
echo echo 正在卸载V264ToMP4... >> %INSTALLER_DIR%\uninstall.bat
echo set INSTALL_DIR=%%PROGRAMFILES%%\V264ToMP4 >> %INSTALLER_DIR%\uninstall.bat
echo if exist "%%INSTALL_DIR%%" rmdir /s /q "%%INSTALL_DIR%%" >> %INSTALLER_DIR%\uninstall.bat
echo if exist "%%PUBLIC%%\Desktop\V264ToMP4.lnk" del "%%PUBLIC%%\Desktop\V264ToMP4.lnk" >> %INSTALLER_DIR%\uninstall.bat
echo if exist "%%PROGRAMDATA%%\Microsoft\Windows\Start Menu\Programs\V264ToMP4" rmdir /s /q "%%PROGRAMDATA%%\Microsoft\Windows\Start Menu\Programs\V264ToMP4" >> %INSTALLER_DIR%\uninstall.bat
echo echo 卸载完成！ >> %INSTALLER_DIR%\uninstall.bat
echo pause >> %INSTALLER_DIR%\uninstall.bat

:: 创建安装程序压缩包
echo 创建安装程序压缩包...
if exist %INSTALLER_DIR%.zip del %INSTALLER_DIR%.zip
powershell -command "Compress-Archive -Path %INSTALLER_DIR% -DestinationPath %INSTALLER_DIR%.zip"

:: 生成版本信息文件
echo 生成版本信息文件...
echo 构建日期: %date% %time% > %DIST_DIR%\build_info.txt
echo 版本: %VERSION% >> %DIST_DIR%\build_info.txt
echo Git提交: >> %DIST_DIR%\build_info.txt
git rev-parse HEAD >> %DIST_DIR%\build_info.txt 2>nul

:: 清理临时文件
echo 清理临时文件...
rmdir /s /q %BUILD_DIR%
rmdir /s /q %PORTABLE_DIR%
rmdir /s /q %INSTALLER_DIR%

echo.
echo ========================================
echo 构建完成！
echo ========================================
echo 便携版: %PORTABLE_DIR%.zip
echo 安装程序: %INSTALLER_DIR%.zip
echo ========================================
echo.
pause