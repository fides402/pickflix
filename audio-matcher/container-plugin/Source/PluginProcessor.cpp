#include "PluginProcessor.h"
#include "PluginEditor.h"

ContainerProcessor::ContainerProcessor()
    : AudioProcessor(BusesProperties()
                          .withInput("Input", juce::AudioChannelSet::stereo(), true)
                          .withOutput("Output", juce::AudioChannelSet::stereo(), true))
{
    formatManager.addDefaultFormats(); // registers VST3 (and any other formats built into this binary)
}

ContainerProcessor::~ContainerProcessor() = default;

void ContainerProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    lastSampleRate = sampleRate;
    lastBlockSize = samplesPerBlock;
    for (auto& entry : chain)
        if (entry.instance != nullptr)
            entry.instance->prepareToPlay(sampleRate, samplesPerBlock);
}

void ContainerProcessor::releaseResources()
{
    for (auto& entry : chain)
        if (entry.instance != nullptr)
            entry.instance->releaseResources();
}

void ContainerProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    for (auto& entry : chain)
        if (entry.instance != nullptr)
            entry.instance->processBlock(buffer, midiMessages);
}

double ContainerProcessor::getTailLengthSeconds() const
{
    double maxTail = 0.0;
    for (auto& entry : chain)
        if (entry.instance != nullptr)
            maxTail = juce::jmax(maxTail, entry.instance->getTailLengthSeconds());
    return maxTail;
}

juce::AudioProcessorEditor* ContainerProcessor::createEditor()
{
    return new ContainerEditor(*this);
}

void ContainerProcessor::instantiateStage(const juce::String& bundlePath, const juce::var& parameters)
{
    juce::OwnedArray<juce::PluginDescription> descriptions;
    for (auto* format : formatManager.getFormats())
        format->findAllTypesForFile(descriptions, bundlePath);

    if (descriptions.isEmpty())
    {
        DBG("ContainerProcessor: no plugin descriptions found for " << bundlePath);
        return;
    }

    juce::String errorMessage;
    // Synchronous instantiation: fine for VST3. AU/AUv3 on newer JUCE need the
    // async createPluginFor(desc, sr, blockSize, callback) overload instead.
    auto instance = formatManager.createPluginFor(*descriptions.getFirst(), lastSampleRate, lastBlockSize, errorMessage);
    if (instance == nullptr)
    {
        DBG("ContainerProcessor: failed to instantiate " << bundlePath << ": " << errorMessage);
        return;
    }

    instance->prepareToPlay(lastSampleRate, lastBlockSize);

    // Parameter values in the manifest are pre-normalized to [0, 1] (the
    // convention every AudioProcessorParameter uses internally) so this stays
    // a plain name match -- no per-plugin unit conversion here.
    if (auto* obj = parameters.getDynamicObject())
    {
        for (auto& prop : obj->getProperties())
        {
            const auto paramName = prop.name.toString();
            const auto value = static_cast<float>(static_cast<double>(prop.value));
            for (auto* param : instance->getParameters())
            {
                if (param->getName(128) == paramName)
                {
                    param->setValueNotifyingHost(juce::jlimit(0.0f, 1.0f, value));
                    break;
                }
            }
        }
    }

    chain.push_back({ bundlePath, std::move(instance) });
}

void ContainerProcessor::loadChainFromManifest(const juce::var& manifestJson)
{
    chain.clear();
    auto chainVar = manifestJson.getProperty("chain", juce::var());
    if (auto* arr = chainVar.getArray())
    {
        for (auto& stage : *arr)
        {
            auto bundlePath = stage.getProperty("bundle_path", juce::var()).toString();
            auto parameters = stage.getProperty("parameters", juce::var());
            if (bundlePath.isNotEmpty())
                instantiateStage(bundlePath, parameters);
        }
    }
}

juce::var ContainerProcessor::currentManifestAsVar() const
{
    juce::Array<juce::var> chainArray;
    for (auto& entry : chain)
    {
        auto stageObj = std::make_unique<juce::DynamicObject>();
        stageObj->setProperty("bundle_path", entry.bundlePath);

        auto paramsObj = std::make_unique<juce::DynamicObject>();
        if (entry.instance != nullptr)
            for (auto* param : entry.instance->getParameters())
                paramsObj->setProperty(param->getName(128), param->getValue());
        stageObj->setProperty("parameters", juce::var(paramsObj.release()));

        chainArray.add(juce::var(stageObj.release()));
    }

    auto root = std::make_unique<juce::DynamicObject>();
    root->setProperty("chain", chainArray);
    return juce::var(root.release());
}

void ContainerProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    const auto jsonString = juce::JSON::toString(currentManifestAsVar());
    destData.setSize(0);
    juce::MemoryOutputStream stream(destData, false);
    stream.writeString(jsonString);
}

void ContainerProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    juce::MemoryInputStream stream(data, static_cast<size_t>(sizeInBytes), false);
    const auto jsonString = stream.readString();
    const auto parsed = juce::JSON::parse(jsonString);
    loadChainFromManifest(parsed);
}

// VST3 (and other juce_audio_plugin_client wrapper) entry point.
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new ContainerProcessor();
}
