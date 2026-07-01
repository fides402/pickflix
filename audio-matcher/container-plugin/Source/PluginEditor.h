#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>
#include "PluginProcessor.h"

// Minimal dev/debug UI: lets a human load a chain_manifest.json manually
// while testing in a DAW. The automated backend workflow bakes the manifest
// directly via setStateInformation and never needs this UI.
class ContainerEditor : public juce::AudioProcessorEditor
{
public:
    explicit ContainerEditor(ContainerProcessor&);

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    ContainerProcessor& processor;
    juce::TextButton loadManifestButton{"Load Chain Manifest..."};
    juce::Label statusLabel;
    std::unique_ptr<juce::FileChooser> fileChooser;

    void loadManifestFromDisk();
    void refreshStatusLabel();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ContainerEditor)
};
