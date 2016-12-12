C:\Windows\System32\cmd.exe /E:ON /V:ON /T:0E /K "C:\Program Files\Microsoft SDKs\Windows\v7.0\Bin\SetEnv.cmd"
cd C:\Program Files\Microsoft SDKs\Windows\v7.0\
set DISTUTILS_USE_SDK=1
setenv /x64 /release
cd C:\Users\Pedro\.qgis2\python\plugins\AequilibraE\algorithms
c:\Python27\python setup_Assignment.py build_ext --inplace
ping 192.168.1.1
