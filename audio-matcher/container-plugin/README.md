# Container VST3

Hosts the effect chain the matching pipeline found (real VST3 sub-plugins,
each with the parameters the optimizer converged to) inside a single VST3.
Save this plugin's preset in any DAW (FL Studio, Ableton, Reaper, ...) and you
get one portable `.vstpreset` that reproduces the whole chain -- no need to
touch FL Studio's undocumented Patcher format or reverse-engineer Ableton's
rack XML (see the earlier discussion: those are DAW-specific and one of them
isn't safely writable; a single VST3 container sidesteps both).

## Why this can't be built or tested in the sandbox that generated it

This code was written in a cloud sandbox with no JUCE, no VST3 SDK, no C++
plugin toolchain vendored, and (network policy permitting) no real VST3
plugins installed to host. It's a structurally complete JUCE `AudioProcessor`
skeleton, not a placeholder -- but it has not been compiled here. Build and
test it on the machine that actually has your plugins installed.

## Build

1. Clone JUCE next to this file (or point `JUCE_DIR` at an existing checkout):
   ```
   git clone --branch 7.0.12 --depth 1 https://github.com/juce-framework/JUCE.git container-plugin/JUCE
   ```
2. Configure and build:
   ```
   cmake -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --config Release
   ```
3. The built `.vst3` will be under `build/AudioMatcherContainer_artefacts/Release/VST3/`.
   Copy it to your system's VST3 folder (e.g. `~/.vst3` on Linux,
   `/Library/Audio/Plug-Ins/VST3` on macOS, `C:\Program Files\Common
   Files\VST3` on Windows).

## How the backend feeds it

`backend/app/services/container_export.py` turns a finished matching job's
chain into `chain_manifest.json`:
```json
{
  "chain": [
    { "bundle_path": "/path/to/SomeEQ.vst3", "state_chunk_base64": "..." },
    { "bundle_path": "/path/to/SomeComp.vst3", "state_chunk_base64": "..." }
  ]
}
```
`state_chunk_base64` is the plugin's raw state -- on the backend it comes from
DawDreamer's `PluginProcessor.save_state()` (verified against the installed
`dawdreamer` package: it writes the same kind of binary blob a DAW's
`getStateInformation` would produce). `ContainerProcessor::setStateInformation`
(or the dev-only "Load Chain Manifest..." button in the editor) decodes it and
calls the real sub-plugin's own `setStateInformation` directly -- which also
restores non-parameter state (e.g. a sampler's loaded sample), not just
`AudioProcessorParameter` values.

A `parameters` object (values pre-normalized to `[0, 1]`, matched by name) is
still accepted as a fallback for manifests built without a state chunk, but
`state_chunk_base64` is preferred whenever present. Chains produced by
`SimulatedPluginHost` (the numpy/scipy DSP stand-ins used to prove the
optimizer works without any VST3 plugins installed) have no `plugin_ref`
bundle path at all -- `container_export.py` reports those stages as
`unresolved_simulated_stages` rather than silently emitting a broken preset.

## Getting a .vstpreset without opening a DAW (experimental)

Once you've built this plugin, add its install folder to `PLUGIN_SCAN_PATHS`
in `backend/.env` so the scanner picks it up (it reads the plugin's own
`moduleinfo.json`, generated automatically by the VST3 SDK, to get its real
class ID). Then:

```
GET /jobs/{id}/vstpreset?container_plugin_id=<its id from GET /plugins>
```

writes a real `.vstpreset` file directly -- `backend/app/services/vstpreset_writer.py`
implements Steinberg's documented binary format (confirmed against
`steinbergmedia/vst3_public_sdk`'s own source, not reconstructed from memory)
combined with this plugin's class ID and the chain manifest as its component
state. This has been round-trip tested against its own reader in
`tests/test_vstpreset_writer.py`, but there was no compiled build of this
plugin nor a real DAW available while writing it to confirm a real host
actually accepts the file. If it doesn't load, fall back to the verified
path: load `/jobs/{id}/container-manifest` via the "Load Chain Manifest..."
button in this plugin's editor, then use the DAW's own "save preset".

## VST2 plugins

The scanner and the matching/optimization step (DawDreamer, Python side)
support VST2 (`.dll` on Windows) exactly like VST3 -- add your VST2 folder
(e.g. `C:\Program Files\Steinberg\VSTPlugins`) to `PLUGIN_SCAN_PATHS` and
they'll show up in the UI the same way, since `make_plugin_processor()`
loads either format transparently.

**This compiled container, however, only registers VST3** via
`formatManager.addDefaultFormats()`. Hosting a VST2 stage as a sub-plugin
*inside* this container additionally requires JUCE's `VSTPluginFormat`,
which needs the VST2 SDK -- Steinberg stopped distributing it to new
licensees around 2018, so it has to be sourced and added to the JUCE build
separately (out of scope here; not something bundled or fetched for you).
Until that's set up, a chain containing a VST2 stage can be matched/optimized
fine, but its `container_export.py` output will list that stage's bundle
path pointing at a `.dll` this container can't actually load -- use the
manual per-plugin preset workflow (or drop VST2 stages from the chain) for
those until VST2 hosting is added to this build.

## Known limitations (v1)

- Only VST3 is registered (`formatManager.addDefaultFormats()` will pick up
  whatever formats JUCE was built with -- add AU explicitly if you need it on
  macOS, or the VST2 SDK for VST2 sub-plugin hosting, see above).
- Plugin instantiation is via the synchronous `createPluginFor` overload,
  which works for VST3 but not for formats that require the async API (e.g.
  AUv3). Swap in the callback-based overload if you add those.
- Channel layouts are assumed compatible (stereo in, stereo out) across the
  whole chain; no bus negotiation between stages.
