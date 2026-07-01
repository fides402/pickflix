# Requires JUCE cloned/vendored at container-plugin/JUCE (e.g. `git clone
# --branch 7.0.12 https://github.com/juce-framework/JUCE.git`), or point
# JUCE_DIR at an existing JUCE checkout. This project cannot be built inside
# the sandbox that generated it (no JUCE/VST3 SDK, no plugin binaries) -- it
# is meant to be compiled on the machine that will actually host real VST3
# plugins. See README.md for the full build walkthrough.
cmake_minimum_required(VERSION 3.22)
project(AudioMatcherContainer VERSION 0.1.0)

if(DEFINED JUCE_DIR)
    add_subdirectory(${JUCE_DIR} JUCE)
else()
    add_subdirectory(JUCE)
endif()

juce_add_plugin(AudioMatcherContainer
    COMPANY_NAME "AudioMatcher"
    PLUGIN_MANUFACTURER_CODE Amch
    PLUGIN_CODE Amc1
    FORMATS VST3
    PRODUCT_NAME "Audio Matcher Container"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
)

target_sources(AudioMatcherContainer
    PRIVATE
        Source/PluginProcessor.cpp
        Source/PluginEditor.cpp
)

target_compile_definitions(AudioMatcherContainer
    PUBLIC
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_VST3_CAN_REPLACE_VST2=0
)

target_link_libraries(AudioMatcherContainer
    PRIVATE
        juce::juce_audio_utils
        juce::juce_audio_processors
        juce::juce_gui_basics
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags
)
