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

**Next:** Step 2 — Install Autodesk Fusion 360 using the system Wine 11.10 without downloading or building another Wine/Proton.
