@echo off
setlocal

set PPCAP=C:\PcapPlusPlus
set NPCAPSDK=C:\npcapsdk

if not exist "%PPCAP%\include\pcapplusplus\PcapLiveDeviceList.h" (
  echo ERROR: PcapPlusPlus headers not found at %PPCAP%
  exit /b 1
)

if not exist "%NPCAPSDK%\Lib\x64\wpcap.lib" (
  echo ERROR: Npcap SDK libs not found at %NPCAPSDK%
  exit /b 1
)

if not exist "src\main.cpp" (
  echo ERROR: src\main.cpp not found.
  exit /b 1
)

if not exist "bin" mkdir bin

cl /EHsc /MD src\main.cpp ^
 /I"%PPCAP%\include\pcapplusplus" ^
 /Fe:bin\main.exe ^
 /link ^
 /LIBPATH:"%PPCAP%\lib" ^
 /LIBPATH:"%NPCAPSDK%\Lib\x64" ^
 Pcap++.lib Packet++.lib Common++.lib wpcap.lib Packet.lib ws2_32.lib iphlpapi.lib

if errorlevel 1 (
  echo Build FAILED.
  exit /b 1
)

echo Build OK. Output: bin\main.exe
endlocal