REM for first time user, first unzip the file *development/3rdparty.zip*!
REM potentially remove path to installed SandCastle from environment variable as the build might not success.

MSBuild.exe .\documentation\Cpacs_doc_project.shfbproj
