"""Staged black-box parameter search: greedy per-plugin-stage CMA-ES, then a
joint refinement pass over the whole chain. Mirrors the architecture discussed
with the user: black-box optimizer in the hot loop, LLM only at the topology/
strategy level (see llm_orchestrator.py), never inside this loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import cma
import numpy as np

from app.services.audio_features import combined_distance, extract_features, feature_distance_breakdown
from app.services.plugin_defs import bounds, default_params, identity_params, is_real_plugin, param_names, real_plugin_bundle_path
from app.services.plugin_host import ChainStage, PluginHost

IterationCallback = Callable[[str, int, float, dict[str, float]], None]


@dataclass
class StageResult:
    plugin_type: str
    params: dict[str, float]
    distance: float


@dataclass
class MatchResult:
    chain: list[ChainStage]
    final_distance: float
    stage_results: list[StageResult] = field(default_factory=list)
    used_identity_fallback: bool = False


def _vector_to_params(plugin_type: str, x: np.ndarray) -> dict[str, float]:
    names = param_names(plugin_type)
    b = bounds(plugin_type)
    clipped = np.clip(x, [lo for lo, _ in b], [hi for _, hi in b])
    return dict(zip(names, clipped.tolist()))


def _params_to_vector(plugin_type: str, params: dict[str, float]) -> np.ndarray:
    return np.array([params[n] for n in param_names(plugin_type)])


def _make_stage(plugin_type: str, params: dict[str, float]) -> ChainStage:
    """Every ChainStage in this module goes through here so real-plugin
    stages always carry their bundle path -- DawDreamerPluginHost.render()
    requires plugin_ref, and it's easy to forget on one of the several
    ChainStage(...) construction sites otherwise."""
    plugin_ref = real_plugin_bundle_path(plugin_type) if is_real_plugin(plugin_type) else None
    return ChainStage(plugin_type, params, plugin_ref=plugin_ref)


def _evaluate(
    host: PluginHost,
    chain: list[ChainStage],
    input_audio: np.ndarray,
    sr: int,
    ref_audio: np.ndarray,
    ref_features,
) -> float:
    rendered = host.render(chain, input_audio, sr)
    cand_features = extract_features(rendered, sr)
    breakdown = feature_distance_breakdown(ref_features, cand_features, ref_audio, rendered, sr)
    return combined_distance(breakdown)


def _grid_search_1d(evaluate_fn, lo: float, hi: float, steps: int = 41) -> tuple[float, float]:
    """CMA-ES (the `cma` package) refuses to optimize in 1 dimension ("code
    was never tested"), which real single-parameter plugins (or a chain that
    reduces to one) would hit -- a plain grid search is cheap enough at this
    dimensionality and sidesteps the library limitation entirely."""
    best_value, best_distance = lo, float("inf")
    for value in np.linspace(lo, hi, steps):
        dist = evaluate_fn(float(value))
        if dist < best_distance:
            best_distance, best_value = dist, float(value)
    return best_value, best_distance


def optimize_stage(
    host: PluginHost,
    plugin_type: str,
    prefix: list[ChainStage],
    suffix: list[ChainStage],
    input_audio: np.ndarray,
    sr: int,
    ref_audio: np.ndarray,
    max_generations: int = 25,
    popsize: int | None = None,
    on_iteration: IterationCallback | None = None,
) -> StageResult:
    ref_features = extract_features(ref_audio, sr)
    b = bounds(plugin_type)

    if len(b) == 1:
        lo, hi = b[0]

        def evaluate_1d(value: float) -> float:
            params = _vector_to_params(plugin_type, np.array([value]))
            chain = prefix + [_make_stage(plugin_type, params)] + suffix
            return _evaluate(host, chain, input_audio, sr, ref_audio, ref_features)

        best_value, best_distance = _grid_search_1d(evaluate_1d, lo, hi)
        best_params = _vector_to_params(plugin_type, np.array([best_value]))
        if on_iteration:
            on_iteration(plugin_type, 1, best_distance, best_params)
        return StageResult(plugin_type=plugin_type, params=best_params, distance=best_distance)

    x0 = _params_to_vector(plugin_type, default_params(plugin_type))
    sigma0 = 0.25 * np.mean([hi - lo for lo, hi in b])

    es = cma.CMAEvolutionStrategy(
        x0.tolist(),
        sigma0,
        {
            "bounds": [[lo for lo, _ in b], [hi for _, hi in b]],
            "popsize": popsize or (4 + int(3 * np.log(len(b)))),
            "verbose": -9,
            "maxiter": max_generations,
        },
    )

    # seed with the default (identity-ish) params actually evaluated: ask()
    # never evaluates x0 itself, so without this the stage could converge to
    # something worse than doing nothing and still be reported as "best"
    best_params = default_params(plugin_type)
    best_distance = _evaluate(
        host, prefix + [_make_stage(plugin_type, best_params)] + suffix, input_audio, sr, ref_audio, ref_features
    )
    generation = 0
    while not es.stop():
        generation += 1
        candidates = es.ask()
        fitnesses = []
        for x in candidates:
            params = _vector_to_params(plugin_type, np.array(x))
            chain = prefix + [_make_stage(plugin_type, params)] + suffix
            dist = _evaluate(host, chain, input_audio, sr, ref_audio, ref_features)
            fitnesses.append(dist)
            if dist < best_distance:
                best_distance = dist
                best_params = params
        es.tell(candidates, fitnesses)
        if on_iteration:
            on_iteration(plugin_type, generation, best_distance, best_params)

    return StageResult(plugin_type=plugin_type, params=best_params, distance=best_distance)


def optimize_chain_greedy(
    host: PluginHost,
    plugin_types: list[str],
    input_audio: np.ndarray,
    sr: int,
    ref_audio: np.ndarray,
    max_generations_per_stage: int = 25,
    refine_generations: int = 15,
    on_iteration: IterationCallback | None = None,
) -> MatchResult:
    stage_results: list[StageResult] = []
    chain: list[ChainStage] = []

    for i, plugin_type in enumerate(plugin_types):
        suffix = [_make_stage(pt, default_params(pt)) for pt in plugin_types[i + 1 :]]
        result = optimize_stage(
            host, plugin_type, chain, suffix, input_audio, sr, ref_audio,
            max_generations=max_generations_per_stage, on_iteration=on_iteration,
        )
        stage_results.append(result)
        chain.append(_make_stage(plugin_type, result.params))

    refined_chain, refined_distance = _joint_refine(
        host, chain, input_audio, sr, ref_audio, max_generations=refine_generations, on_iteration=on_iteration
    )

    # never hand back a chain that makes things worse than not processing at
    # all -- greedy per-stage search can converge to a locally-stuck combo
    # that undershoots the untouched input, especially when a requested stage
    # (e.g. compressor) isn't actually needed to approach this reference.
    # Two fallbacks are checked, not one: identity_params() is a meaningful
    # bypass for the simulated types (gain=0, mix=0, ratio=1...), but there is
    # no reliable universal "bypass" parameter set for an arbitrary real VST3
    # -- so an empty chain (skip every stage, i.e. exactly the raw input) is
    # also compared, which is always a valid no-op regardless of plugin type.
    ref_features = extract_features(ref_audio, sr)
    identity_chain = [_make_stage(pt, identity_params(pt)) for pt in plugin_types]
    identity_distance = _evaluate(host, identity_chain, input_audio, sr, ref_audio, ref_features)
    empty_distance = _evaluate(host, [], input_audio, sr, ref_audio, ref_features)

    best_fallback_distance = min(identity_distance, empty_distance)
    if best_fallback_distance <= refined_distance:
        if empty_distance <= identity_distance:
            return MatchResult(
                chain=[], final_distance=empty_distance,
                stage_results=stage_results, used_identity_fallback=True,
            )
        return MatchResult(
            chain=identity_chain, final_distance=identity_distance,
            stage_results=stage_results, used_identity_fallback=True,
        )

    return MatchResult(chain=refined_chain, final_distance=refined_distance, stage_results=stage_results)


def _joint_refine(
    host: PluginHost,
    chain: list[ChainStage],
    input_audio: np.ndarray,
    sr: int,
    ref_audio: np.ndarray,
    max_generations: int,
    on_iteration: IterationCallback | None,
) -> tuple[list[ChainStage], float]:
    ref_features = extract_features(ref_audio, sr)
    plugin_types = [stage.plugin_type for stage in chain]
    slices: list[tuple[int, int]] = []
    x0_parts: list[np.ndarray] = []
    lo_parts: list[float] = []
    hi_parts: list[float] = []
    cursor = 0
    for stage in chain:
        vec = _params_to_vector(stage.plugin_type, stage.params)
        slices.append((cursor, cursor + len(vec)))
        x0_parts.append(vec)
        b = bounds(stage.plugin_type)
        lo_parts += [lo for lo, _ in b]
        hi_parts += [hi for _, hi in b]
        cursor += len(vec)

    x0 = np.concatenate(x0_parts)

    if len(x0) == 1:
        lo, hi = lo_parts[0], hi_parts[0]
        stage = chain[0]

        def evaluate_1d(value: float) -> float:
            params = _vector_to_params(stage.plugin_type, np.array([value]))
            return _evaluate(host, [_make_stage(stage.plugin_type, params)], input_audio, sr, ref_audio, ref_features)

        best_value, best_distance = _grid_search_1d(evaluate_1d, lo, hi)
        best_params = _vector_to_params(stage.plugin_type, np.array([best_value]))
        if on_iteration:
            on_iteration("joint_refine", 1, best_distance, best_params)
        return [_make_stage(stage.plugin_type, best_params)], best_distance

    sigma0 = 0.1 * np.mean(np.array(hi_parts) - np.array(lo_parts))
    es = cma.CMAEvolutionStrategy(
        x0.tolist(), sigma0,
        {"bounds": [lo_parts, hi_parts], "popsize": 4 + int(3 * np.log(len(x0))), "verbose": -9, "maxiter": max_generations},
    )

    # seed with the incoming (pre-refine) chain itself: CMA-ES's ask() never
    # evaluates x0 directly, so without this the refine pass could wander to
    # something worse than the greedy result and still be reported as "final"
    best_chain = chain
    best_distance = _evaluate(host, chain, input_audio, sr, ref_audio, ref_features)
    generation = 0
    while not es.stop():
        generation += 1
        candidates = es.ask()
        fitnesses = []
        for x in candidates:
            x = np.array(x)
            candidate_chain = []
            for stage, (start, end) in zip(chain, slices):
                params = _vector_to_params(stage.plugin_type, x[start:end])
                candidate_chain.append(_make_stage(stage.plugin_type, params))
            dist = _evaluate(host, candidate_chain, input_audio, sr, ref_audio, ref_features)
            fitnesses.append(dist)
            if dist < best_distance:
                best_distance = dist
                best_chain = candidate_chain
        es.tell(candidates, fitnesses)
        if on_iteration:
            on_iteration("joint_refine", generation, best_distance, {})

    return best_chain, best_distance
