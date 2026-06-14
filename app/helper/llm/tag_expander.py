import os
import re

import requests


class TagExpander:
    PROMPT_TEMPLATE = """You expand event tags into specific related keywords for semantic search.

    Output exactly one line of space-separated one word keywords. No punctuation, no sentences, no explanations.
    Use SPECIFIC words related to the tag's meaning. Avoid generic words like: konzert, festival, live, event, kultur, veranstaltung, musik, show, aufführung.

    Context: public events, concerts, festivals, nightlife, culture.

    Examples:
    barrierefrei → rollstuhl accessible barrier-free wheelchairaccess inklusion eingangshilfe rampe
    musik → rock pop jazz techno classical blues soul vocals gitarre schlagzeug
    kinder → kids children familienfreundlich family-friendly nachwuchs jugend spielen lernend
    biergarten → bier beergarden terrasse outdoor sommer freiluft sundown entspannen
    comedy → humor standup kabarett witze lachen funny satirisch improv bühnenkomik
    nightlife → nachtleben club party feiern tanzen bar drinks ausgehen dancing rave
    art → kunst ausstellung galerie gallery kreativ installation modern zeitgenössisch malerei
    kulinarik → essen food streetfood kochen cuisine genuss tasty markt zutaten
    confirmation → konfirmation kirchlich religious ceremony glaube feier kirche jugendweihe
    planned → geplant scheduled bevorstehend upcoming terminiert vorgemerkt organisiert
    free → kostenlos gratis eintritt frei umsonst kostenfrei
    bebop → bop hardbop swing improvisation uptempo charlie-parker dizzy-gillespie brass saxophone
    hardrock → metal gitarre electric liveband heavymetal riffs distortion grunge punk
    techno → electronic beats dancefloor edm synth bass underground rave detroit minimal
    märchen → fairytale fable erzählung fantasy magic wonder sagenhaft kinderstück abenteuer
    theater → schauspiel drama stage bühne acting play ensemble regie monolog dialog
    klassik → classical orchestra symphonie philharmonie chamber baroque oper dirigent partitur
    sport → fitness running marathon bewegung aktiv exercise turnen wettkampf athletik
    food → essen streetfood markt cuisine tastings genuss kochen drinks snacks
    exhibition → ausstellung galerie museum installation modern zeitgenössisch objekte werke künstler
    atmospheric → stimmungsvoll ambiance immersive magisch einzigartig besonders intim erlebnisreich zaubernd
    film → film kino movie cinema drehbuch regie schauspieler dokumentar thriller western filmvorführung
    {tag_name} →"""


    def __init__(self):
        self.ollama = "http://ollama:11434/api/generate"
        if os.environ.get("FLASK_ENV") == "setup":
            self.ollama = "http://localhost:11434/api/generate"

    def expand_tag_slow(self, tag_name: str) -> str:
        try:
            response = requests.post(
                self.ollama,
                json={
                    "model": "gemma2:9b",
                    "prompt": self.PROMPT_TEMPLATE.format(tag_name=tag_name),
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "top_p": 1.0,
                        "num_predict": 48,
                        "stop": ["\n", "\n\n"],
                        "repeat_penalty": 1.1,
                    }
                },
                timeout=60
            )
            return self._clean(tag_name, response.json().get("response", ""))
        except Exception as e:
            print(f"[expand] failed for '{tag_name}': {e}")
            return tag_name

        except Exception as e:
            print(f"[expand] LLM expansion failed for '{tag_name}': {e}")
            return tag_name


    def expand_tag_fast(self, tag_name: str) -> str:
        try:
            response = requests.post(
                self.ollama,
                json={
                    "model": "qwen2.5:1.5b",
                    "prompt": self.PROMPT_TEMPLATE.format(tag_name=tag_name),
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "top_p": 1.0,
                        "num_predict": 24,
                        "stop": ["\n", "\n\n"],
                        "repeat_penalty": 1.1,
                    }
                },
                timeout=3
            )
            return self._clean(tag_name, response.json().get("response", ""))
        except Exception:
            return tag_name


    @staticmethod
    def _clean(tag_name: str, content: str) -> str:
        content = content.strip().lower().lstrip("→>:-").strip()
        tokens = content.split()

        PROMPT_BLEED = {
            "public", "events", "concerts", "festivals", "culture",
            "nightlife", "context", "examples", "output", "input",
            "mation", "keywords", "sentences", "explanations"
        }
        STOPWORDS = {'für', 'und', 'der', 'die', 'das', 'ein', 'eine', 'mit', 'von', 'zu', 'im', 'an', 'am', 'the',
                     'and', 'for', 'with', 'of', 'in', 'at', 'to', 'a', 'is'}

        seen = set()
        unique_tokens = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                unique_tokens.append(t)

        anchor_words = [w for w in tag_name.lower().split() if w not in STOPWORDS]
        anchor_set = set(anchor_words)

        cleaned = [
            t for t in unique_tokens
            if len(t) > 2
               and re.match(r'^[a-zA-ZäöüÄÖÜß\-]+$', t)
               and t.strip('-')
               and t not in anchor_set
               and t not in STOPWORDS
               and t not in PROMPT_BLEED
        ]

        result = " ".join(anchor_words + cleaned[:11])
        print(f"[expand] {tag_name}: {result}")
        return result