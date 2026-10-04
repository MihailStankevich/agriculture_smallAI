"""Generate reviewed, bundled Kiswahili audio once; never call ElevenLabs from the PWA."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "audio"
# A standard multilingual ElevenLabs voice. Replace only after a local-language
# reviewer approves a different voice and the generated clips.
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
PROMPTS = {
    "coffee-rust-sw.mp3": "Tahadhari ya CropSignal. Picha hii ina ishara inayofanana na roya ya kahawa. Weka alama kwenye mmea huu. Kagua upande wa chini wa majani na mimea iliyo karibu leo. Usinyunyize dawa kwa msingi wa matokeo haya pekee. Wasiliana na afisa wa ugani kuthibitisha.",
    "uncertain-sw.mp3": "Matokeo hayana uhakika. Kagua majani matano ya mmea huu na mimea iliyo karibu. Angalia kama alama zinaenea. Piga picha ya jani moja kwenye mwanga mzuri. Usinyunyize dawa wala kutuma ripoti ya jamii kutokana na matokeo haya pekee.",
    "report-saved-sw.mp3": "Ripoti imehifadhiwa kwenye simu hii. Picha yako haijatumwa. Itasubiri muunganisho wa intaneti ili kushiriki ishara ya eneo kwa njia isiyojulikana.",
}


def main() -> None:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY is not available to this process.")
    OUTPUT.mkdir(exist_ok=True)
    for filename, text in PROMPTS.items():
        target = OUTPUT / filename
        payload = ('{"text":' + __import__("json").dumps(text, ensure_ascii=False) + ',"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.55,"similarity_boost":0.75}}').encode("utf-8")
        request = Request(API.format(voice_id=VOICE_ID), data=payload, method="POST", headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        with urlopen(request, timeout=90) as response:
            target.write_bytes(response.read())
        print(f"Wrote {target.name}")


if __name__ == "__main__":
    main()
