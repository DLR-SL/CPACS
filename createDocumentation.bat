@echo off
REM Make sure that 7z and msbuild are installed and available as commands (e.g., by setting the paths to the corresponding tools in the PATH variable).
REM Alternatively, replace these with the full paths to 7z.exe and MSBuild.exe.  

REM Extract 3rdparty.zip:
7z x -y .\development\3rdparty.zip -odevelopment\

REM Build documentation
msbuild /p:Configuration=Release documentation\Cpacs_doc_project.shfbproj
