# CLO Easy Export

A CLO 3D plugin that prepares a garment for real-time use and exports it with one click. It exports an FBX mesh and baked PBR textures, plus a topstitch mask.
It can also export an entire folder of projects with the same settings (batch).

## What it does

1. Sets all patterns' mesh type to **Quad**.
2. Sets the **Particle Distance** of all patterns (default 15).
3. Sets all topstitch styles to **Texture**.
4. Exports an **FBX**: garment only (no avatar), single object, thick, unified UVs, current colorway.
5. Bakes **Diffuse, Normal and Roughness** maps (4096 px).
6. Bakes an opaque **topstitch mask** (white stitches on black). The original colours are restored automatically afterwards.

Optionally, it can also pack the UVs into the 0–1 tile first. See [Auto-UV](#auto-uv).

Output:

```
<output folder>/
├── <name>.fbx
├── <name>_export_log.txt
└── textures/
    ├── <name>_diffuse.png
    ├── <name>_normal.png
    ├── <name>_roughness.png
    └── <name>_topstitch.png
```

## Requirements

- Windows
- CLO 3D with Python plug-in support:
  - **CLO 2026.1.336 or newer:** use `1_single`, or `2_batch` (for a whole folder). Both open a settings window. They need CLO's `gui_api` module, which older builds don't have.
  - **Older CLO builds** (tested on 2026.1.224): use `3_older_single`, or `4_older_batch` (for a whole folder). See [Older CLO versions](#older-clo-versions).

## Installation

1. Download or clone this repository.
2. Close CLO.
3. Open `C:\Users\Public\Documents\CLO\Plugins\pluginSettings.json` and add this entry to the `"plugins"` list. Set `m_SourcePath` to the `plugin` folder of this repository, using forward slashes:

   ```json
   {
     "m_AddingPositionIndex": 1,
     "m_BaseMenuTreeByObjectName": "Plugins",
     "m_PlugInTitle": "Easy Export",
     "m_SourcePath": "C:/path/to/clo-easy-export/plugin",
     "m_SourceType": "folder"
   }
   ```

4. Start CLO. The plugin appears under **Plugins → Easy Export**, with four entries:
   - `1_single` for one project.
   - `2_batch` for a folder of projects.
   - `3_older_single` for one project, on CLO builds older than 2026.1.336.
   - `4_older_batch` for a folder of projects, on CLO builds older than 2026.1.336.

## Single file export

1. **Arrange the UVs in the UV Editor** (0–1 tile) first, or use [Auto-UV](#auto-uv).
2. Open **Plugins → Easy Export → 1_single**.
3. Fill in the window's fields:
   - The output folder.
   - A file name. Leave it empty to use the project name.
   - A particle distance. 10 or higher is recommended.
   - **Auto-UV to 0-1 before exporting**, if you want it. See [Auto-UV](#auto-uv).
4. Press **Run**, check the summary and press **Continue**. Wait until the plugin finishes.

> **Note:** Steps 1–3 permanently change the project's mesh type, particle distance and topstitch settings. Save a copy of your project first if you want to keep the original.

## Batch export

`2_batch` runs the same export on every `.zprj` file in a folder, using one set of settings. Subfolders aren't searched.

1. **Arrange the UVs in the UV Editor** (0–1 tile) in every project and save them, or use [Auto-UV](#auto-uv). The batch can't stop to fix them.
2. Save the project that's open in CLO. The batch will close it without saving.
3. Open **Plugins → Easy Export → 2_batch**.
4. Fill in the window's fields:
   - The input folder with your `.zprj` files.
   - The output folder.
   - A particle distance. 10 or higher is recommended.
   - **Auto-UV to 0-1 before exporting**, if you want it. See [Auto-UV](#auto-uv).
   - **Save auto-UVs**, if you want Auto-UV's result kept in your projects. See [Keeping the new UVs](#keeping-the-new-uvs).
5. Press **Run**, check the summary and press **Continue**. Wait until the batch finishes. It can't be stopped from the window.

Each project is exported to its own subfolder, named after the `.zprj` file:

```
<output folder>/
├── batch_export_log.txt
├── <project>/
│   ├── <project>.fbx
│   ├── <project>_export_log.txt
│   └── textures/
└── <another project>/
```

- **Your project files:** the `.zprj` files aren't saved, so the changes made for the export don't stay in them. The one exception is the optional [Keeping the new UVs](#keeping-the-new-uvs).
- **After the batch:** the last project stays open, with the export changes in it. Don't save it, or those changes go into its `.zprj`. If every project was skipped, the project you had open stays as it was.
- **The project you have open:** the batch always exports the saved `.zprj` files, so unsaved changes aren't included, even if that project is in the input folder.
- **Failed projects:** if a project fails, the batch logs the error and continues with the next one. The final summary lists any failures.
- **Running it again:** projects that are already fully exported are skipped, so a rerun only does what's missing. To export a project again, for example with a new particle distance, delete its subfolder first.

## Auto-UV

`1_single` and `2_batch` have an **Auto-UV to 0-1 before exporting** checkbox. It's off by default, and the window remembers your last choice. In `3_older_single` and `4_older_batch`, set `AUTO_UV = True` instead. See [Older CLO versions](#older-clo-versions).

When it's on, the plugin checks whether every pattern fits inside the 0–1 tile:

- If they all fit, your UVs are left as they are.
- If any pattern is outside, the UVs are reset to the 2D arrangement, then all patterns are packed with CLO's UV packing, using a padding of 0.01 and **Fix Scale Ratio** on. That replaces the whole UV layout, and the export fails if something still doesn't fit.

Good to know:

- **Buttons, zippers and trims:** the check can't see them. If only a button is outside the tile, nothing gets packed, so check those yourself.
- **Overlaps:** the check only looks at the tile's edges. Overlapping patterns inside 0–1 aren't detected.
- **Hand-scaled UVs:** the reset undoes any scaling you did in the UV editor, so every pattern goes back to its true proportions. If you made a pattern bigger on purpose for more texture detail, arrange the UVs yourself and leave Auto-UV off.
- **Your project:** in `1_single` and `3_older_single`, the new UV layout stays in the open project, so it's kept if you save. Saving also keeps the other export changes.

### Keeping the new UVs

`2_batch` also has a **Save auto-UVs** checkbox, which only works with Auto-UV ticked. It's off by default, and the window remembers your last choice. In `4_older_batch`, set `SAVE_AUTO_UVS = True` together with `AUTO_UV = True`.

When it's on, a project that gets packed is saved right after packing, before the mesh and topstitch changes, so its `.zprj` gets the new UVs and nothing else. On the next run everything fits, so the UVs aren't packed again.

- **Can't be undone:** the `.zprj` is overwritten, so the old UV layout is gone, including any scaling you did by hand. Keep a backup if you might need it.
- **Projects that aren't packed:** if a project already fits, or was skipped because it's already exported, its file isn't touched.
- **If the export fails afterwards:** the new UVs stay saved. Run the batch again and the UVs are left as they are.
- **Older CLO builds:** saving can update a project to your CLO version, so an older build may not be able to open it.

This isn't in `1_single` or `3_older_single`, because saving there would also write any unsaved edits in the open project.

## Older CLO versions

CLO builds without the `gui_api` module (such as 2026.1.224) can't open the plugin window. Use `plugin/3_older_single.py` or `plugin/4_older_batch.py` instead. They run the same export steps, but you enter the settings in the file itself.

### Single file export on older versions

1. **Arrange the UVs in the UV Editor** (0–1 tile) first, or use `AUTO_UV`.
2. Drag `plugin/3_older_single.py` into the CLO 3D window. CLO opens it in its own script editor.
3. In CLO's script editor, edit the block at the top:
   - `OUTPUT_DIR`: the output folder, as an absolute path. It is created if it doesn't exist.
   - `FILE_NAME`: leave it empty to use the project name.
   - `PARTICLE_DISTANCE`: 10 or higher is recommended.
   - `AUTO_UV`: `True` to pack the UVs into 0–1 first if any pattern is outside. See [Auto-UV](#auto-uv). Default `False`.
   - `PLUGIN_DIR`: the `plugin` folder of this repository. The default matches the ZIP download unpacked into the CLO `Plugins` folder.
4. Run the script from CLO's script editor.
5. Check `<output folder>/<name>_export_log.txt` for the result. The script doesn't show a message when it finishes.

### Batch export on older versions

> **Note:** `4_older_batch` hasn't been tested on an older CLO build yet.

1. **Arrange the UVs in the UV Editor** (0–1 tile) in every project and save them. The batch can't stop to fix them.
2. Save the project that's open in CLO. The batch will close it without saving, and there is no warning.
3. Drag `plugin/4_older_batch.py` into the CLO 3D window. CLO opens it in its own script editor.
4. In CLO's script editor, edit the block at the top:
   - `INPUT_DIR`: the folder with your `.zprj` files, as an absolute path.
   - `OUTPUT_DIR`: the output folder, as an absolute path. It is created if it doesn't exist.
   - `PARTICLE_DISTANCE`: 10 or higher is recommended.
   - `AUTO_UV`: `True` to pack a project's UVs into 0–1 first if any pattern is outside. With this on, step 1 is optional. See [Auto-UV](#auto-uv). Default `False`.
   - `SAVE_AUTO_UVS`: `True` to save packed UVs over the `.zprj`. Only works with `AUTO_UV = True`. See [Keeping the new UVs](#keeping-the-new-uvs). Default `False`.
   - `PLUGIN_DIR`: the `plugin` folder of this repository. The default matches the ZIP download unpacked into the CLO `Plugins` folder.
5. Run the script from CLO's script editor. It can't be stopped once it has started.
6. Check `<output folder>/batch_export_log.txt` for the result. The script doesn't show a message when it finishes.

The output folders, skipped projects and failure handling work the same as in [Batch export](#batch-export).

### Differences from the windowed versions

- `3_older_single` overwrites existing files in the output folder without asking.
- There is no progress bar or confirmation dialog. Progress is printed to CLO's Python console.
- Every run is also added to `C:\Users\Public\clo_easy_export_run.txt`, which helps when the output folder itself is the problem.

## License

MIT - see [LICENSE](LICENSE).
