Ti do la procedura completa per installare **Autodesk Fusion 360 da zero su CachyOS GNOME**, utilizzando la configurazione che abbiamo già fatto funzionare e gli script pubblicati nella nostra repository.

L'obiettivo è avere:

- **Wine 11.10 Staging** come unico Wine di sistema.
- **Fusion 360** installato in `~/.autodesk_fusion`.
- **DXVK e XWayland**, senza desktop virtuale Wine.
- **Fix automatico dei popup**, avviato direttamente dall'icona di Fusion nella dock GNOME.

I comandi sono compatibili con **Fish Shell**.

## 1. Aggiorna CachyOS e installa le dipendenze

Prima aggiorna il sistema:

```fish
sudo pacman -Syu
```

Se l'aggiornamento richiede un riavvio, fallo prima di proseguire.

Installa le dipendenze:

```fish
sudo pacman -S --needed \
    git downgrade \
    gawk cabextract coreutils curl wget 7zip lsb-release \
    polkit samba libspnav xdg-utils bc xorg-xrandr \
    mokutil desktop-file-utils qt5-tools mesa-demos mesa-utils \
    python libxfixes xorg-xprop xdotool
```

Uso `7zip` invece del vecchio `p7zip`, perché sulle versioni recenti di Arch/CachyOS il pacchetto `7zip` lo sostituisce.

### Controlla la scheda video

```fish
lspci | grep -Ei 'vga|3d|display'
```

Se il nuovo PC ha una **GPU AMD**, installa:

```fish
sudo pacman -S --needed \
    mesa lib32-mesa \
    vulkan-radeon lib32-vulkan-radeon \
    vulkan-icd-loader lib32-vulkan-icd-loader \
    vulkan-tools
```

Se invece ha una GPU **NVIDIA o Intel**, non installare alla cieca i driver AMD: serviranno i driver Vulkan appropriati.

---

## 2. Installa Wine 11.10 Staging

Controlla prima quali pacchetti Wine sono già presenti:

```fish
pacman -Q wine wine-staging wine-cachyos-opt \
    ntsync-autoload cachyos-gaming-meta \
    cachyos-gaming-applications 2>/dev/null
```

Se non trovi pacchetti che possono creare conflitti, procedi:

```fish
sudo downgrade --ala-only 'wine-staging=~^11[.]10-'
```

Se viene richiesta la versione, seleziona **`wine-staging 11.10-1`**. È presente nell'Arch Linux Archive.

Quando ti chiede di aggiungere Wine a `IgnorePkg`, rispondi **`y`** per impedirne l'aggiornamento automatico.

**Attenzione:** se Pacman segnala un conflitto con `ntsync-autoload`, `wine-cachyos-opt` o i metapacchetti gaming, fermati e mandami l'errore. Su CachyOS la rimozione corretta dipende dai pacchetti installati; non forzare la transazione con `--nodeps` o `--overwrite`.

Installa poi i componenti Wine:

```fish
sudo pacman -S --needed wine-gecko wine-mono winetricks
```

Verifica:

```fish
wine --version
pacman -Q wine-staging
command -s wine
```

Il risultato atteso è:

```text
wine-11.10 (Staging)
wine-staging 11.10-1
/usr/bin/wine
```

---

## 3. Scarica e installa Autodesk Fusion 360

Creiamo la cartella temporanea per l'installer:

```fish
mkdir -p "$HOME/fusion-installer"
cd "$HOME/fusion-installer"
```

Scarichiamo lo script di Cryinkfly da Codeberg:

```fish
curl -fL --retry 3 \
    "https://codeberg.org/cryinkfly/Autodesk-Fusion-360-on-Linux/raw/branch/main/files/setup/autodesk_fusion_installer_x86-64.sh" \
    -o install-fusion-codeberg.sh
```

Controlliamo lo script:

```fish
bash -n install-fusion-codeberg.sh
```

E avviamo l'installazione:

```fish
env -u WAYLAND_DISPLAY \
    bash ./install-fusion-codeberg.sh --install --default
```

**Non usare `sudo` per avviare questo installer.**

Aspetta che completi la configurazione del prefix, l'installazione delle dipendenze Windows e l'installazione di Fusion. L'operazione può richiedere parecchio tempo.

Al termine, verifica:

```fish
test -f "$HOME/.autodesk_fusion/bin/autodesk_fusion_launcher.sh"; and echo "Launcher OK"

test -d "$HOME/.autodesk_fusion/wineprefixes/default/drive_c"; and echo "Wine prefix OK"
```

---

## 4. Configura Wine

Apri `winecfg` usando esclusivamente il prefix di Fusion:

```fish
env -u WAYLAND_DISPLAY \
    WINEPREFIX="$HOME/.autodesk_fusion/wineprefixes/default" \
    winecfg
```

Nella scheda **Graphics / Grafica** configura:

| Opzione | Impostazione |
|---|---|
| Allow the window manager to decorate the windows | ✅ Attiva |
| Allow the window manager to control the windows | ✅ Attiva |
| Emulate a virtual desktop | ❌ Disattiva |

Conferma con **Apply** e **OK**.

---

## 5. Installa il fix automatico delle finestre popup

Ora utilizziamo direttamente gli script che abbiamo caricato nella nostra repository.

Scarica il repository:

```fish
git clone \
    https://github.com/MaydayAlaska/Fusion-360-on-CachyOS-with-GNOME.git \
    "$HOME/fusion-360-cachyos-guide"
```

Entra nella cartella:

```fish
cd "$HOME/fusion-360-cachyos-guide"
```

Installa il fix:

```fish
python3 scripts/install-fusion-popup-fix.py
```

Questo script installa il correttore e configura il launcher GNOME affinché il fix parta automaticamente con Fusion.

Le due operazioni sui popup sono eseguite nell'ordine corretto: **prima rende l'overlay trasparente ai clic tramite XFixes, poi elimina l'oscuramento tramite XProp**.

### Avvia Fusion

Dal terminale puoi provare direttamente il nuovo collegamento:

```fish
gio launch "$HOME/.local/share/applications/autodesk-fusion.desktop"
```

Oppure utilizza l'icona **Autodesk Fusion** nella dock.

Apri **Esporta** o **Apri** per verificare che la finestra sia cliccabile e non oscurata.

Per controllare il fix:

```fish
pgrep -af 'fusion-popup-fix[.]py|fusion-launch-with-fix[.]py'

tail -n 30 "$HOME/.cache/fusion-popup-fix.log"
```

---

## 6. Pulizia finale (facoltativa)

Solo quando Fusion funziona correttamente, puoi spostare nel Cestino le cartelle degli installer:

```fish
for dir in \
    "$HOME/fusion-installer" \
    "$HOME/fusion-360-cachyos-guide"

    if test -d "$dir"
        gio trash "$dir"
    end
end
```

**Non eliminare mai `~/.autodesk_fusion`**: contiene il programma e il suo prefix Wine.

---

La guida completa è disponibile qui: [Fusion 360 on CachyOS with GNOME](https://github.com/MaydayAlaska/Fusion-360-on-CachyOS-with-GNOME).

**Ti consiglio di procedere nell'ordine indicato e verificare Wine 11.10 prima di installare Fusion.** La configurazione è stata verificata sul precedente PC AMD, mentre su questo nuovo PC potrebbero esserci differenze nei driver o nei pacchetti CachyOS.
