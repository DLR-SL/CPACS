# Building the Documentation (Windows)

The following sections describe how to build the CPACS schema documentation and tool-specific schema documentation using **MSBuild** on Windows.

## Build documentation for `cpacs_schema.xsd`
### 1. Extract Third-Party Dependencies

Unpack the bundled third-party dependencies into the `development` directory (e.g., via `7z`):

```cmd
7z x -y .\development\3rdparty.zip -odevelopment\
```

This will populate the required external libraries expected by the documentation build.

---

### 2. Install MSBuild (Visual Studio Build Tools)

Ensure that MSBuild is available. If it is not already installed, install the Visual Studio 2022 Build Tools:

```cmd
winget install -e --id Microsoft.VisualStudio.2022.BuildTools
```

After installation, verify that `msbuild` is accessible from the command line (you may need to open a new shell).

---

### 3. Install Microsoft HTML Help Compiler

The documentation build requires the Microsoft HTML Help Compiler (`hhc.exe`).

- The official Microsoft download page currently links to a non-functional installer.
    
- A working installer is available here:  
    [https://www.helpandmanual.com/downloads_mscomp.html](https://www.helpandmanual.com/downloads_mscomp.html)
    

During installation, you may see a warning indicating that a newer version than 1.3 is already installed. This warning can be safely ignored; the installer will still deploy the required components, and the build will succeed.

---

### 4. Build the Documentation

Run MSBuild with the Release configuration:

```cmd
msbuild /p:Configuration=Release documentation\Cpacs_doc_project.shfbproj
```

If `msbuild` is not fond in your command promt, add the path to `msbuild.exe` your environment variable `PATH` or call the executable explicitly. 

> **Info**  
> As an alternative to running the individual commands manually, you can use the
> preconfigured batch script `createDocumentation.bat`.
>
> The script encapsulates the required build steps and invokes MSBuild with the
> appropriate configuration for the CPACS documentation.
>
> Make sure to have `7z` and `msbuild` in your `PATH` environment variable or replace with the explicit link.

## Build toolspecific schema documentation

### 1. Prepare the build environment

Ensure that all prerequisite steps have been completed:
- Third-party dependencies extracted (Step 1)
- MSBuild installed (Step 2)
- HTML Help Compiler installed (Step 3)
### 2. Build the toolspecific documentation

```cmd
"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe" /p:Configuration=Release documentation\Toolspecific_doc_project.shfbproj
```
### 3. Adopt the configuration file to your tool

If the above steps are working, the build system is working. You may adopt the `documentation/Toolspecific_doc_project.shfbproj` to your tool.