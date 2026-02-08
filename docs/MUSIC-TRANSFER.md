# Music Transfer Guide (from `stations.yaml`)

This project supports both internet streams and local audio files. Local files must be placed under the MPD music root:

- **Music root:** `/home/radio/audio`
- Any `file:` or `dir:` entry in `stations.yaml` is interpreted relative to that directory.

For example:
- `file: "GTA/FlyLo FM [GTA V].mp3"` means the file must exist at `/home/radio/audio/GTA/FlyLo FM [GTA V].mp3`
- `dir: "shows/BobDylan"` means the directory must exist at `/home/radio/audio/shows/BobDylan`

---

## 1) Understand which station types need local music

In `stations.yaml`:

- `type: stream` uses only `url:` (no local files required)
- `type: mp3_loop_random_start` requires a local `file:`
- `type: mp3_dir_random_start_then_in_order` requires a local `dir:` with audio files inside

---

## 2) Create the expected folder structure on the Raspberry Pi

```bash
sudo -u radio mkdir -p /home/radio/audio/GTA
sudo -u radio mkdir -p /home/radio/audio/shows/{BobDylan,IggyPop,JarvisCocker,JoeStrummer,JohnPeel,MarianMcPartland,PaulMcCartney,HenryRollins,AliceCooper}
sudo -u radio mkdir -p /home/radio/audio/shows/music/Ambient
```

If your `stations.yaml` has different `file:`/`dir:` entries, create matching directories for those entries.

---

## 3) Transfer files into the exact paths referenced by `stations.yaml`

From your computer, use `scp` (or `rsync`) to copy files.

### Example using `scp`

```bash
# Single-file stations (bank 8 examples)
scp "FlyLo FM [GTA V].mp3" radio@<pi-host>:/home/radio/audio/GTA/
scp "Muji BGM 1980-2000.mp3" radio@<pi-host>:/home/radio/audio/shows/music/Ambient/

# Directory-based stations (bank 9 examples)
scp -r ./BobDylan/* radio@<pi-host>:/home/radio/audio/shows/BobDylan/
scp -r ./IggyPop/* radio@<pi-host>:/home/radio/audio/shows/IggyPop/
```

### Example using `rsync` (recommended)

```bash
rsync -av --progress ./GTA/ radio@<pi-host>:/home/radio/audio/GTA/
rsync -av --progress ./shows/ radio@<pi-host>:/home/radio/audio/shows/
```

> Keep filenames and capitalization exactly aligned with `stations.yaml` for `file:` entries.

---

## 4) Fix ownership/permissions (if needed)

```bash
sudo chown -R radio:radio /home/radio/audio
sudo find /home/radio/audio -type d -exec chmod 755 {} \;
sudo find /home/radio/audio -type f -exec chmod 644 {} \;
```

---

## 5) Update MPD database and verify

```bash
mpc update
mpc ls | head
```

Then test a local station (replace with one that uses local files):

```bash
sudo -u radio /usr/local/bin/radio-play 8 0
```

If it plays, your file paths match `stations.yaml`.

---

## 6) Optional: print all local paths referenced by your current `stations.yaml`

Run this on the Pi:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path

cfg = Path('/home/radio/stations.yaml')
base = Path('/home/radio/audio')

data = yaml.safe_load(cfg.read_text())
for b_id, bank in data.get('banks', {}).items():
    for s_id, st in bank.get('stations', {}).items():
        t = st.get('type')
        if t == 'mp3_loop_random_start' and st.get('file'):
            print(f"bank {b_id} station {s_id} FILE {base / st['file']}")
        elif t == 'mp3_dir_random_start_then_in_order' and st.get('dir'):
            print(f"bank {b_id} station {s_id} DIR  {base / st['dir']}")
PY
```

Use this list as your exact copy checklist.
