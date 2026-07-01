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
    { "bundle_path": "/path/to/SomeEQ.vst3", "parameters": { "Gain": 0.7 } },
    { "bundle_path": "/path/to/SomeComp.vst3", "parameters": { "Ratio": 0.4 } }
  ]
}
```
`ContainerProcessor::setStateInformation` (or the dev-only "Load Chain
Manifest..." button in the editor) parses this and instantiates each
sub-plugin via `AudioPluginFormatManager`, matching parameters by name.

**Parameter values are pre-normalized to `[0, 1]`** -- the convention every
`AudioProcessorParameter` uses internally -- so the container plugin can set
them directly with no per-plugin unit conversion. This is the reason
`DawDreamerPluginHost` (see `backend/app/services/plugin_host.py`) is the
intended source of real chains for this exporter: it automates real VST3
parameters directly, so its output is already in the right units. Chains
produced by `SimulatedPluginHost` (the numpy/scipy DSP stand-ins used to prove
the optimizer works without any VST3 plugins installed) have no `plugin_ref`
bundle path at all -- `container_export.py` reports those stages as
`unresolved_simulated_stages` rather than silently emitting a broken preset.

## Known limitations (v1)

- Only VST3 is registered (`formatManager.addDefaultFormats()` will pick up
  whatever formats JUCE was built with -- add AU explicitly if you need it on
  macOS).
- Plugin instantiation is via the synchronous `createPluginFor` overload,
  which works for VST3 but not for formats that require the async API (e.g.
  AUv3). Swap in the callback-based overload if you add those.
- Only `AudioProcessorParameter` values are restored, not opaque internal
  state (e.g. a sampler's loaded sample, a convolution reverb's impulse
  response). Plugins that need more than their exposed parameters to fully
  reproduce their sound aren't fully covered yet.
- Channel layouts are assumed compatible (stereo in, stereo out) across the
  whole chain; no bus negotiation between stages.
