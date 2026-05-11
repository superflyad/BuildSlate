# Local AI Runtime Modeling

BuildSlate's local AI runtime models add a first-pass feasibility layer beyond parameter-storage estimates. They are conservative screening tools for local LLM and multimodal residency pressure; they are not performance predictors and must not be used as proof of device readiness.

## Why model parameters are not enough

A model's parameter count and quantization level estimate only the storage required for weights. Local runtime feasibility also depends on memory reserved for runtime metadata, allocator fragmentation, activations, KV cache, operating-system headroom, multimodal components, storage staging, and safety reserve. A model that appears to fit by parameter size alone can still fail once context length and resident support models are included.

## Quantization limits

Quantization reduces weight size by lowering the number of bits used per stored parameter. It does not eliminate all runtime costs. KV cache elements, runtime buffers, attention implementation details, scheduler state, OS memory use, multimodal components, and storage-load behavior remain separate constraints. Aggressive quantization can also introduce model-quality and kernel-availability risks that are outside these first-pass scripts.

## KV cache and context scaling

KV cache memory scales linearly with:

- layer count,
- hidden size,
- context length,
- batch size,
- bytes per KV element.

The first-pass formula is:

```text
kv_bytes = 2 * layers * hidden_size * context_tokens * batch_size * kv_bytes_per_element
kv_gb = kv_bytes / 1e9
```

The factor of 2 represents keys and values. The result is architecture-dependent: grouped-query attention, multi-query attention, cache compression, paged attention, and runtime-specific layouts can reduce or reshape the realized memory requirement. Long context is memory-expensive because every increase in context length linearly increases the resident cache.

## Model load time

Cold model load time depends on local storage bandwidth, the amount of model data that must be read, decompression or dequantization staging, and runtime initialization overhead. The current model treats storage bandwidth as a theoretical input, not a guaranteed sustained value. Filesystem behavior, thermal state, concurrent I/O, storage controller limits, and runtime allocation can all increase real load latency.

## Multimodal resident overhead

A local assistant may need more than the base LLM. Vision encoders, speech models, embedding models, vector indexes, tool runtimes, and staging buffers can all add resident memory pressure. The first-pass multimodal model treats these as additive placeholders until concrete model selections, precision formats, and runtime implementation choices exist.

## Runtime budget interpretation

The combined runtime memory budget adds model residency, KV cache, multimodal overhead, OS reserve, and safety reserve. Passing the budget means only that the conservative arithmetic does not exceed the configured memory capacity. It does not prove sustained performance, thermal viability, battery acceptability, software support, or product feasibility.

## Explicit non-goals

These models do not predict real tokens/sec. Real throughput depends on memory bandwidth, compute kernels, NPU/GPU support, scheduling, thermal throttling, runtime implementation, batching strategy, cache layout, memory latency, and model architecture. BuildSlate should continue to treat throughput as unresolved until measured on target silicon and a target runtime.
