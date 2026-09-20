# Compatible model catalog

`catalog.json` lists tested data-only model revisions for the packaged Voice
Dictate app. It is not an arbitrary model search feed. Free and Pro use the
same catalog; model updates are not a paid feature.

The native app bundles a fallback catalog, validates runtime compatibility,
pins downloads to immutable revisions, verifies SHA-256 and sizes, and loads a
model before switching the active revision. Automatic updates are opt-in.
An incompatible architecture requires an app/runtime update, not remote code.

Before changing this file, verify all hashes against actual downloaded files,
run English/Hindi and long-recording tests in the packaged sandboxed app, and
check rollback. Preserve known-working releases locally until activation succeeds.

Gemma 4 E4B is provided by Google, with this MLX quantization from mlx-community.
See the [model card](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit)
and Google's [Gemma 4 Apache-2.0 license](https://ai.google.dev/gemma/apache_2).
