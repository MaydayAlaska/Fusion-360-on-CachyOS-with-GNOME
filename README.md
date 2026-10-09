# Fusion 360 on CachyOS with GNOME

A community guide for running Autodesk Fusion 360 on **CachyOS + GNOME Wayland** with **system-installed Wine** (no separate portable Wine, no virtual desktop).

> **Status:** Work in progress. This is an unofficial configuration, not supported by Autodesk. The tested setup uses an AMD Radeon RX 9070 XT, Wine Staging 11.10, XWayland, and DXVK. Subsequent steps will cover installing Fusion and fixing modal popups.

## Step 1 — Install Wine 11.10 Staging and dependencies

We use **Wine Staging 11.10-1** from the Arch Linux Archive, managed by Pacman. In our tests, Wine 11.19 caused Fusion rendering and window problems that were largely absent with 11.10.

**Important:** Downgrading packages and holding Wine back can introduce compatibility and security risks. Make a system snapshot/backup first. Review all Pacman transactions before confirming; never use `--nodeps`, `-Rdd`, or `--overwrite` to bypass conflicts.

The commands below are compatible with **Fish shell**.

### 1.1 Check existing Wine installations

```fish
wine --version
pacman -Q wine-staging wine-cachyos-opt ntsync-autoload wine-gecko wine-mono winetricks protontricks
```

A “package not found” message simply means that package is not installed. Check whether your system has CachyOS gaming metapackages and/or another Wine build before proceeding.

### 1.2 Install the system prerequisites

On a newly configured system, bring CachyOS up to date **before** pinning Wine:

```fish
sudo pacman -Syu
```

Install the tools needed by Wine, the Fusion installer, and the popup workaround documented in later steps:

```fish
sudo pacman -S --needed \
    downgrade \
    gawk cabextract coreutils curl wget p7zip lsb-release \
    polkit samba libspnav xdg-utils bc xorg-xrandr \
    mokutil desktop-file-utils qt5-tools mesa-demos mesa-utils \
    python libxfixes xorg-xprop xdotool
```

Install Wine Gecko, Wine Mono, Winetricks, and Protontricks **after** Wine 11.10 (section 1.5), so Pacman does not pull the latest repository Wine as a dependency. If any package conflicts with an existing Wine installation, **do not force the transaction**; review the conflict-handling instructions below.

For the tested **AMD / RADV** configuration, also ensure the Vulkan and OpenGL drivers (including the 32-bit variants) are installed:

```fish
sudo pacman -S --needed \
    mesa lib32-mesa vulkan-radeon lib32-vulkan-radeon \
    vulkan-icd-loader lib32-vulkan-icd-loader vulkan-tools
```

The `lib32-*` packages require the `[multilib]` repository to be enabled. Other GPU vendors need their corresponding Vulkan drivers instead.

### 1.3 Handle the CachyOS gaming package conflict (only if necessary)

**Skip this section if you can install Wine 11.10 without conflicts.**

On our CachyOS installation, the newer `wine-staging` depended on `ntsync-autoload`, while the archived Wine 11.10 package also owned `/usr/lib/modules-load.d/10-ntsync.conf`. Removing `ntsync-autoload` alone was blocked by the newer Wine; removing Wine alone was blocked by Gecko, Mono, and Winetricks. The gaming metapackages added further dependencies.

For a machine with **this exact set of packages installed**, preview the removal:

```fish
pacman -R --print \
    cachyos-gaming-applications cachyos-gaming-meta \
    wine-cachyos-opt wine-staging ntsync-autoload \
    wine-gecko wine-mono winetricks protontricks
```

Proceed **only if** that command succeeds and you have reviewed the package list. If any package is missing or another application depends on these packages, stop and adapt the transaction to your system; do not blindly copy a removal list.

```fish
sudo pacman -R \
    cachyos-gaming-applications cachyos-gaming-meta \
    wine-cachyos-opt wine-staging ntsync-autoload \
    wine-gecko wine-mono winetricks protontricks
```

Using `pacman -R` (without `-s` or `-c`) removes only the selected packages, not all their dependencies. However, **removing the CachyOS gaming metapackages means they will no longer maintain the original gaming package selection for you**. Steam and other applications are not automatically removed just because the metapackages are removed; always check Pacman's proposed transaction. Reinstalling these metapackages later may pull in an additional Wine build.

### 1.4 Install Wine 11.10 from the Arch Linux Archive

```fish
sudo pacman -S --needed downgrade
sudo downgrade --ala-only 'wine-staging=~^11[.]10-'
```

Choose **`wine-staging 11.10-1`** when prompted. If `downgrade` asks **“add wine-staging to IgnorePkg? [y/N]”**, answer **`y`** to prevent an immediate upgrade back to a newer version.

If you receive an `ntsync-autoload` file conflict, **stop** and return to section 1.3. Do not overwrite the file manually.

### 1.5 Restore Wine companion packages

If they were removed during conflict resolution, reinstall them now:

```fish
sudo pacman -S --needed wine-gecko wine-mono winetricks protontricks
```

- **Wine Gecko**: HTML rendering in Wine.
- **Wine Mono**: Wine's .NET compatibility layer.
- **Winetricks**: installs Windows runtime components used by the Fusion installer.
- **Protontricks**: optional for Fusion, useful for Steam/Proton setups; included in our tested system.

Pacman will install the dependencies of these packages automatically. **Review the transaction** to ensure it does not replace Wine Staging 11.10.

### 1.6 Verify the final installation

```fish
wine --version
pacman -Q wine-staging wine-gecko wine-mono winetricks protontricks
command -s wine
```

Expected Wine-related output:

```text
wine-11.10 (Staging)
wine-staging 11.10-1
/usr/bin/wine
```

To confirm no additional CachyOS Wine build or separate NTSync autoload package remains:

```fish
pacman -Q wine-cachyos-opt ntsync-autoload
```

“Package not found” is expected for these two packages in this configuration.

Optionally verify Vulkan detects the AMD GPU:

```fish
vulkaninfo --summary
```

Check the pin in `/etc/pacman.conf`:

```fish
grep -n '^IgnorePkg' /etc/pacman.conf
```

The line should include `wine-staging`. **Revisit this pin periodically**: Wine 11.10 will not receive newer Wine fixes or security updates while held back. Also keep in mind that an old Wine package on an otherwise updated rolling-release system is not guaranteed to remain compatible forever.

---

## Step 2 — Install Autodesk Fusion 360

This step follows the **Cryinkfly Autodesk Fusion 360 on Linux** installer, using the **system Wine Staging 11.10** prepared in Step 1. The tested result uses **one Wine installation**, **one Fusion Wine prefix**, **XWayland**, and **no Wine virtual desktop**.

**Upstream project:** [cryinkfly/Autodesk-Fusion-360-on-Linux on Codeberg](https://codeberg.org/cryinkfly/Autodesk-Fusion-360-on-Linux). The older [GitHub mirror](https://github.com/cryinkfly/Autodesk-Fusion-360-for-Linux) is archived; prefer the Codeberg source for current scripts.

> **Before starting:** This guide is for a **fresh Fusion installation**. Do **not** delete or overwrite an existing `~/.autodesk_fusion` directory: it may contain Fusion data, configuration, and a usable Wine prefix. Back up an existing installation before considering a reinstall.

### 2.1 Verify Wine and the GNOME session

Open a **Fish** terminal and verify the Wine version:

```fish
wine --version
command -s wine
pacman -Q wine-staging
echo $XDG_SESSION_TYPE
```

The tested configuration is:

```text
wine-11.10 (Staging)
/usr/bin/wine
wine-staging 11.10-1
wayland
```

The GNOME desktop may run on **Wayland**, but we want Fusion's Wine windows to use **XWayland**. For this reason, we will remove `WAYLAND_DISPLAY` only from the installer's environment; there is **no need to change the whole desktop session to X11**.

The installer is a third-party shell script that downloads and configures Windows components. Review it before executing it, and **run it as your normal user, not with `sudo`**. It can request administrator privileges for missing system dependencies.

### 2.2 Download the Codeberg installer

Create a dedicated directory and download the upstream installer:

```fish
mkdir -p "$HOME/fusion-installer"
cd "$HOME/fusion-installer"

curl -fL --retry 3 \
    "https://codeberg.org/cryinkfly/Autodesk-Fusion-360-on-Linux/raw/branch/main/files/setup/autodesk_fusion_installer_x86-64.sh" \
    -o install-fusion-codeberg.sh
```

Confirm the download is a shell script before running it:

```fish
head -n 5 install-fusion-codeberg.sh
bash -n install-fusion-codeberg.sh
```

`bash -n` checks shell syntax only; it is **not** a security audit. The upstream `main` branch can change, so review the downloaded script and its dependencies whenever you repeat this procedure.

### 2.3 Install Fusion with the existing system Wine

Run the same command used for the working CachyOS setup:

```fish
env -u WAYLAND_DISPLAY bash ./install-fusion-codeberg.sh --install --default
```

**What the flags and environment mean:**

- `--install`: start the installation.
- `--default`: use the default directory, `$HOME/.autodesk_fusion`.
- `env -u WAYLAND_DISPLAY`: make Wine use X11/XWayland rather than its native Wayland path for this process.
- `bash`: the downloaded installer is a Bash script, even though your interactive terminal uses Fish.

The installer downloads Autodesk Fusion, configures the Wine prefix, installs Windows runtime components with Winetricks, configures the selected graphics backend, and creates application launchers. An internet connection and a valid Autodesk account/license are required.

On the tested **AMD Radeon RX 9070 XT** system, the installer selected **DXVK**. DXVK translates Direct3D calls to Vulkan; it works with the Mesa RADV driver installed in Step 1.

**Important:** The upstream installer can try to install or upgrade Wine **if it decides the installed version is missing or too old**. For the upstream script version inspected while writing this guide, Wine 11.10 passes its version check, so it should use the existing `/usr/bin/wine`. If the installer proposes removing or replacing Wine 11.10, **cancel the transaction** and investigate rather than accepting it.

The installation may take a while. Avoid interrupting its Windows runtime downloads and setup stages just because a window temporarily stops responding.

### 2.4 Verify the installation paths

The expected layout is:

```text
~/.autodesk_fusion/
├── bin/
│   └── autodesk_fusion_launcher.sh
├── downloads/
├── logs/
└── wineprefixes/
    └── default/
        └── drive_c/
```

Check that the launcher and the prefix were created:

```fish
test -f "$HOME/.autodesk_fusion/bin/autodesk_fusion_launcher.sh"; and echo "Fusion launcher found"
test -d "$HOME/.autodesk_fusion/wineprefixes/default/drive_c"; and echo "Fusion prefix found"

wine --version
command -s wine
```

**Keep the default prefix:** `$HOME/.autodesk_fusion/wineprefixes/default`. Do not create a second `~/.wine` or `~/.fusion360` prefix for Fusion, and do not install a separate portable Wine/Proton build for this guide.

### 2.5 Configure Wine window integration

Open Wine configuration for **Fusion's own prefix**:

```fish
env -u WAYLAND_DISPLAY \
    WINEPREFIX="$HOME/.autodesk_fusion/wineprefixes/default" \
    winecfg
```

Under **Graphics**, use these settings:

| Wine setting | Value |
| --- | --- |
| Allow the window manager to decorate the windows | **Enabled** |
| Allow the window manager to control the windows | **Enabled** |
| Emulate a virtual desktop | **Disabled** |

**Do not disable window-manager control to work around unclickable modal dialogs.** Although that can make some dialogs clickable, it also caused the main Fusion window to stay above other applications in our tests. The modal-dialog workaround is documented separately in Step 3.

### 2.6 First launch and Fusion graphics settings

The installer normally offers to start Fusion when it finishes. For a later manual launch, use the original launcher:

```fish
env -u WAYLAND_DISPLAY \
    "$HOME/.autodesk_fusion/bin/autodesk_fusion_launcher.sh"
```

Sign in with your Autodesk account if prompted. Browser-based login and Fusion's initial startup may take some time.

For the tested graphics configuration, we used **DX11/DXVK** for rendering with the **Qt API set to OpenGL** and the Chromium graphics option set to **Desktop GL / Automatic**, where those options are available in your Fusion build. Do not assume the preference labels are identical across Fusion versions; verify rendering in a simple design before changing additional graphics settings.

The installer may also create one or more `.desktop` entries. You can locate them with:

```fish
find "$HOME/.local/share/applications" \
    -type f -iname '*fusion*.desktop' \
    -print -exec grep -E '^(Name|Exec)=' {} \; 2>/dev/null
```

Avoid adding multiple manual launchers at this stage. We will adjust the **existing** GNOME launcher when integrating the popup fix.

### 2.7 Known issue: dark or unclickable popup dialogs

On the tested CachyOS/GNOME Wayland setup, Fusion's main UI and 3D viewport worked well, but some modal dialogs (such as **Open** or **Export**) were darkened or intercepted mouse clicks. This is **not** a reason to reinstall Fusion, switch Wine versions, enable a virtual desktop, or disable window-manager control.

We resolved the popup behavior by targeting a specific XWayland overlay: **first** make it click-through using **XFixes ShapeInput**, **then** set its `_NET_WM_WINDOW_OPACITY` to `0`. **The order matters.**

---

**Next:** Step 3 — Automate the Fusion popup fix and integrate it with the existing GNOME application launcher.
