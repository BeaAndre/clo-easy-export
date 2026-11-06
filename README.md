# CLO Easy Export

A CLO 3D plugin that prepares a garment for real-time use and exports it with one click. It exports an FBX mesh and baked PBR textures, plus a topstitch mask. It can also export a whole folder of projects with the same settings.

## What it does

1. Sets all patterns to the **Quad** mesh type.
2. Sets the **particle distance** of all patterns (default 15).
3. Sets all topstitch styles to **Texture**.
4. Exports an **FBX**: garment only (no avatar), single object, thick, unified UVs, current colorway.
5. Bakes **Diffuse, Normal and Roughness** maps (4096 px).
6. Bakes an opaque **topstitch mask** (white stitches on black). The original colours are restored automatically afterwards.

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

- Windows.
- CLO 3D with Python plug-in support:
  - **CLO 2026.1.336 or newer:** use `single`, or `batch` for a whole folder. Both open a window for the settings. They need CLO's `gui_api` module, which older builds don't have.
  - **Older CLO builds** (tested on 2026.1.224): use `single_older`. See [Older CLO versions](#older-clo-versions). Batch export isn't available for these builds.

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

4. Start CLO. The plugin appears under **Plugins → Easy Export**, with three entries:
   - `single` for one project, on CLO 2026.1.336 or newer.
   - `batch` for a folder of projects, on CLO 2026.1.336 or newer.
   - `single_older` for older CLO builds.

## Usage

1. **Arrange the UVs in the UV Editor** (0–1 tile) first.
2. Open **Plugins → Easy Export → single**.
3. Fill in the window's fields:
   - The output folder.
   - A file name. Leave it empty to use the project name.
   - A particle distance. 10 or higher is recommended.
4. Press **Run**, check the summary and press **Continue**. Wait until the plugin finishes.

> **Note:** Steps 1–3 permanently change the project's mesh type, particle distance and topstitch settings. Save a copy of your project first if you want to keep the original.

## Batch export

`batch` runs the same export on every `.zprj` file in a folder, using one set of settings. Subfolders aren't searched.

1. **Arrange the UVs in the UV Editor** (0–1 tile) in every project and save them. The batch can't stop to fix them.
2. Save the project that's open in CLO. The batch closes it without saving.
3. Open **Plugins → Easy Export → batch**.
4. Fill in the window's fields:
   - The folder with your `.zprj` files.
   - The output folder.
   - A particle distance. 10 or higher is recommended.
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

- **Your project files:** the `.zprj` files are never saved, so the changes made for the export don't stay in them.
- **After the batch:** CLO is left with a new, empty project.
- **Failed projects:** if a project fails, the batch logs the error and continues with the next one. The final summary lists any failures.
- **Running it again:** projects that are already fully exported are skipped, so a rerun only does what's missing. To export a project again, for example with a new particle distance, delete its subfolder first.

## Older CLO versions

CLO builds without the `gui_api` module (such as 2026.1.224) can't open the plugin window. Use `plugin/single_older.py` instead. It runs the same export steps, but you enter the settings in the file itself.

1. **Arrange the UVs in the UV Editor** (0–1 tile) first.
2. Drag `plugin/single_older.py` into the CLO 3D window. CLO opens it in its own script editor.
3. In CLO's script editor, edit the block at the top:
   - `OUTPUT_DIR`: the output folder, as an absolute path. It is created if it doesn't exist.
   - `FILE_NAME`: leave it empty to use the project name.
   - `PARTICLE_DISTANCE`: 10 or higher is recommended.
   - `PLUGIN_DIR`: the `plugin` folder of this repository. The default matches the ZIP download unpacked into the CLO `Plugins` folder.
4. Run the script from CLO's script editor.
5. Check `<output folder>/<name>_export_log.txt` for the result. The script doesn't show a message when it finishes.

Differences from the windowed version:

- Existing files in the output folder are overwritten without asking.
- There is no progress bar or confirmation dialog. Progress is printed to CLO's Python console.
- Every run is also added to `C:\Users\Public\clo_easy_export_run.txt`, which helps when the output folder itself is the problem.

## License

MIT - see [LICENSE](LICENSE).
