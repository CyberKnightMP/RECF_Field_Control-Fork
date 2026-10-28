# Repository migration — October 28, 2026

The active project is now **Offbrand-Window/RECF_Field_Control**, formerly **Offbrand-Window/RECF_Control_State**. It contains the PROS kernel adaptation and Python practice tester, including the disconnect watchdog. Commit history, tags, release assets and the develop-pros-4 default branch are retained.

The former **Offbrand-Window/RECF_Field_Control** Electron application has been renamed **Offbrand-Window/RECF_Field_Control_Legacy**, marked discontinued and archived. Its history and release downloads remain available there.

## Existing installations

Use the new canonical depot URL:

```sh
pros c add-depot recf-control-state "https://raw.githubusercontent.com/Offbrand-Window/RECF_Field_Control/develop-pros-4/depot.json"
```

The depot name, kernel package `kernel@4.2.2-recf.2`, wire protocol and `recf_control_*` C APIs remain unchanged. Repository renaming does not require rebuilding a project that already contains this kernel. Installing or upgrading the kernel still requires rebuilding and uploading the actual robot program.

Existing Control State GitHub links redirect to the active repository. Old links to the former app's repository name now reach this active project; use RECF_Field_Control_Legacy to find the discontinued app's source or old releases.
