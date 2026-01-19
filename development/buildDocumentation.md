# Building the Documentation (Windows)

The following sections describe how to build the CPACS schema documentation and tool-specific schema documentation on Windows using **MSBuild**.

> **Note**  
> The instructions below describe the manual steps required to generate documentation from XSD files.  
> Alternatively, you may use the preconfigured batch scripts `createDocumentation.bat` and `createToolspecificDocumentation.bat`, which automate the process.
>
> Ensure that both `7z` and `msbuild` are available in your `PATH` environment variable, or adjust the scripts and commands to use explicit executable paths.

---

## Build Documentation for `cpacs_schema.xsd`

### Step 1: Extract Third-Party Dependencies

Extract the bundled third-party dependencies into the `development` directory (for example, using `7z`):

```cmd
7z x -y .\development\3rdparty.zip -odevelopment\
```

This command populates the external libraries required by the documentation build process.

---

### Step 2: Install MSBuild (Visual Studio Build Tools)

The documentation build requires **MSBuild**, which is provided by either the *Visual Studio Build Tools* or a full *Visual Studio* installation (see [Visual Studio Documentation](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=visualstudio#use-winget-to-install-or-modify-visual-studio) for further details.). For example:

```cmd
winget install -e --id Microsoft.VisualStudio.2022.BuildTools
```

After installation, open a new command prompt and verify that `msbuild` is available:

```cmd
msbuild -version
```

---

### Step 3: Install Microsoft HTML Help Compiler

The documentation build requires the Microsoft HTML Help Compiler (`hhc.exe`).

- The official Microsoft download page currently links to a non-functional installer.
    
- A working installer is available at:  
    [https://www.helpandmanual.com/downloads_mscomp.html](https://www.helpandmanual.com/downloads_mscomp.html)
    

During installation, you may receive a warning indicating that a newer version than 1.3 is already installed. This warning can be safely ignored; the required components will still be installed and the build will succeed.

---

### Step 4: Build the Documentation

Invoke MSBuild using the _Release_ configuration:

```cmd
msbuild /p:Configuration=Release documentation\Cpacs_doc_project.shfbproj
```    


## Build Tool-Specific Schema Documentation

### Step 1: Prepare the Build Environment

Verify that all prerequisites have been completed:

- Third-party dependencies extracted
    
- MSBuild installed
    
- Microsoft HTML Help Compiler installed
    

---

### Step 2: Build the Tool-Specific Documentation

Run MSBuild for the tool-specific documentation project (example path shown below):

```cmd
"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" /p:Configuration=Release documentation\Toolspecific_doc_project.shfbproj
```

Adjust the MSBuild path as necessary to match your local Visual Studio installation.

---

### Step 3: Adapt the Configuration File for Your Tool

Once the build completes successfully, the documentation build system is correctly configured.

To generate documentation for your own tool, adapt the project file:

```
documentation/Toolspecific_doc_project.shfbproj
```

Modify the configuration parameters as required to reference your tool-specific schema and metadata.

---

## Optional Next-Level Improvements

If you want to take this further, consider adding:

- A **Prerequisites** section at the top (Windows version, required tools).
    
- A **Troubleshooting** section (e.g., missing `hhc.exe`, MSBuild path issues).
    
- A **Directory layout overview** for new contributors.
    

If you would like, I can also:

- Convert this into Markdown or reStructuredText
    
- Align it with a corporate documentation style guide
    
- Add troubleshooting diagnostics or CI build instructions