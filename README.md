# CLO Easy Export

A CLO 3D plugin that prepares a garment for real-time use and exports it with one click. It exports an FBX mesh and baked PBR textures, plus a topstitch mask.

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

- CLO 3D 2026.1 or newer, with Python plug-in support. The plugin was built and tested on 2026.1.336.
- Windows.

## Installation

1. Download or clone this repository.
2. Close CLO.
3. Open `C:\Users\Public\Documents\CLO\Plugins\pluginSettings.json` and add this entry to the `"plugins"` list. Set `m_SourcePath` to the `plugin` folder of this repository, using forward slashes:

   ```json
   {
     "m_AddingPositionIndex": 1,
     "m_BaseMenuTreeByObjectName": "Plugins",
     "m_PlugInTitle": "Export Pipeline",
     "m_SourcePath": "C:/path/to/clo-easy-export/plugin",
     "m_SourceType": "folder"
   }
   ```

4. Start CLO. The plugin appears under **Plugins → Export Pipeline → export_pipeline**.

## Usage

1. **Arrange the UVs in the UV Editor** (0–1 tile) first.
2. Open **Plugins → Export Pipeline → export_pipeline**.
3. Fill in the window's fields:
   - The output folder.
   - A file name. Leave it empty to use the project name.
   - A particle distance. 10 or higher is recommended.
4. Press **Run**, check the summary and press **Continue**. Wait until the plugin finishes.

> **Note:** Steps 1–3 permanently change the project's mesh type, particle distance and topstitch settings. Save a copy of your project first if you want to keep the original.

## License

MIT - see [LICENSE](LICENSE).
