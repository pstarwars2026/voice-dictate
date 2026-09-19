#!/usr/bin/env python3
"""Exercise real inference on supplied synthetic 16 kHz mono PCM WAV fixtures.

Reports nonempty output and silence handling, not transcription accuracy.
Does not save or print transcripts. Use HF_HUB_OFFLINE=1 for cached-only checks.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dictation_core import DEFAULT_MODEL, MODES, prompt_for
from voice_dictate import MLXBackend


def check(fixtures):
    import numpy as np

    backend = MLXBackend(DEFAULT_MODEL)
    started = time.monotonic()
    backend.load()
    results = {"model": DEFAULT_MODEL, "load_seconds": round(time.monotonic() - started, 2), "cases": []}
    for fixture in fixtures:
        with wave.open(str(fixture)) as audio:
            if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (16000, 1, 2):
                raise ValueError("Fixtures must be 16 kHz mono, 16-bit PCM")
            if not 0 < audio.getnframes() <= 30 * 16000:
                raise ValueError("Fixtures must contain 0-30 seconds of audio")
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        for mode in MODES:
            started = time.monotonic()
            transcript = backend.transcribe([samples], prompt_for(mode))
            results["cases"].append({"fixture": fixture.name, "mode": mode,
                                     "nonempty": bool(transcript.strip()),
                                     "seconds": round(time.monotonic() - started, 2)})
    results["silence_empty"] = not backend.transcribe([np.zeros(16000)], prompt_for("verbatim"))
    print(json.dumps(results, indent=2))
    return results["silence_empty"] and all(case["nonempty"] for case in results["cases"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", nargs="+", type=Path)
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=1) as worker:
        raise SystemExit(0 if worker.submit(check, args.fixtures).result() else 1)
