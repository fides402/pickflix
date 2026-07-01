#pragma once

#include <juce_audio_processors/juce_audio_processors.h>

// Hosts the effect chain the backend's optimizer found (see
// backend/app/services/container_export.py for the manifest it writes) as
// sub-plugins inside a single VST3, so the whole chain is one preset file
// loadable identically in any VST3-capable DAW.
class ContainerProcessor : public juce::AudioProcessor
{
public:
    ContainerProcessor();
    ~ContainerProcessor() override;

    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return "Audio Matcher Container"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    double getTailLengthSeconds() const override;

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}

    // Bakes the whole chain (bundle paths + parameter values) into the VST3
    // preset, so saving this plugin's state in any host preserves the chain.
    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    // Loads (or reloads) the chain from a manifest produced by the backend:
    // { "chain": [ { "bundle_path": "...", "state_chunk_base64": "..." }, ... ] }
    // state_chunk_base64 is the plugin's raw getStateInformation/save_state
    // blob and is preferred when present; a "parameters" object (values
    // pre-normalized to [0, 1]) is used as a fallback if it's absent -- see
    // README.md.
    void loadChainFromManifest(const juce::var& manifestJson);
    juce::var currentManifestAsVar() const;

    juce::AudioPluginFormatManager formatManager;

private:
    struct ChainEntry
    {
        juce::String bundlePath;
        std::unique_ptr<juce::AudioPluginInstance> instance;
    };

    std::vector<ChainEntry> chain;
    double lastSampleRate = 44100.0;
    int lastBlockSize = 512;

    void instantiateStage(const juce::var& stageVar);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ContainerProcessor)
};
