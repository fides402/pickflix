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
    // { "chain": [ { "bundle_path": "...", "parameters": { "Name": 0.0-1.0, ... } }, ... ] }
    // Parameter values are expected pre-normalized to [0, 1] -- see README.md
    // for why that's the contract instead of native-unit values.
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

    void instantiateStage(const juce::String& bundlePath, const juce::var& parameters);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ContainerProcessor)
};
