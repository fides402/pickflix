#include "PluginEditor.h"

ContainerEditor::ContainerEditor(ContainerProcessor& p)
    : juce::AudioProcessorEditor(&p), processor(p)
{
    addAndMakeVisible(loadManifestButton);
    loadManifestButton.onClick = [this] { loadManifestFromDisk(); };

    addAndMakeVisible(statusLabel);
    statusLabel.setJustificationType(juce::Justification::centred);
    refreshStatusLabel();

    setSize(420, 160);
}

void ContainerEditor::paint(juce::Graphics& g)
{
    g.fillAll(getLookAndFeel().findColour(juce::ResizableWindow::backgroundColourId));
}

void ContainerEditor::resized()
{
    auto area = getLocalBounds().reduced(16);
    loadManifestButton.setBounds(area.removeFromTop(32));
    area.removeFromTop(12);
    statusLabel.setBounds(area);
}

void ContainerEditor::loadManifestFromDisk()
{
    fileChooser = std::make_unique<juce::FileChooser>(
        "Select chain_manifest.json", juce::File(), "*.json");

    const auto flags = juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles;
    fileChooser->launchAsync(flags, [this](const juce::FileChooser& fc)
    {
        const auto file = fc.getResult();
        if (!file.existsAsFile())
            return;

        const auto parsed = juce::JSON::parse(file);
        processor.loadChainFromManifest(parsed);
        refreshStatusLabel();
    });
}

void ContainerEditor::refreshStatusLabel()
{
    const auto manifest = processor.currentManifestAsVar();
    const auto chainArray = manifest.getProperty("chain", juce::var()).getArray();
    const auto count = chainArray != nullptr ? chainArray->size() : 0;
    statusLabel.setText(juce::String(count) + " plugin(s) loaded in chain", juce::dontSendNotification);
}
