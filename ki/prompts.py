"""Prompts für die KI-Zusammenfassungen (Abschnitt 9 des Konzepts).

In einer eigenen Datei, damit sie sich leicht anpassen lassen. Grundregeln in
allen Prompts: auf Deutsch antworten, nur Informationen aus dem Text
verwenden, nichts erfinden, keine Bewertungen oder Ratschläge.
"""
from __future__ import annotations

GRUNDREGELN = (
    "Antworte ausschließlich auf Deutsch. Verwende nur Informationen aus dem "
    "gegebenen Text, erfinde nichts hinzu. Gib keine Bewertungen, Meinungen "
    "oder Ratschläge ab."
)

TAGES_STICHPUNKTE_SYSTEM = f"{GRUNDREGELN} Du fasst Tagebucheinträge in kurze Stichpunkte zusammen."

TAGES_STICHPUNKTE_SCHEMA = {
    "type": "object",
    "properties": {
        "stichpunkte": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        }
    },
    "required": ["stichpunkte"],
}


def tages_stichpunkte_prompt(text: str) -> str:
    return (
        "Fasse den folgenden Tagebucheintrag in genau drei kurze Stichpunkte zu den "
        "wichtigsten Ereignissen des Tages zusammen. Hat der Text weniger Inhalt, gib "
        "entsprechend weniger Stichpunkte zurück (auch nur einen oder gar keinen, wenn "
        "nichts Nennenswertes im Text steht).\n\n"
        f"Tagebucheintrag:\n{text}"
    )


# --------------------------------------------------------------------------
# Monats- und Jahresübersicht (Abschnitt 9.2 und 9.3): beide deutlich
# ausführlicher als die Tages-Stichpunkte, mit Blick auf Ereignisse UND
# Stimmung - aber nur, soweit sie sich aus der Eingabe ergeben, nicht erfunden.
# --------------------------------------------------------------------------

UEBERSICHT_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "stichpunkte": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
    },
    "required": ["text", "stichpunkte"],
}

MONATS_UEBERSICHT_SYSTEM = (
    f"{GRUNDREGELN} Du fasst die Tages-Stichpunkte eines Monats zu einer ausführlichen "
    "Monatsübersicht zusammen: was waren die großen Ereignisse und Unternehmungen, und "
    "wie war die Stimmung im Monat (Erfolge, Rückschläge, was hat beschäftigt) - jeweils "
    "nur, soweit sich das aus den gegebenen Stichpunkten erkennen lässt."
)

JAHRES_UEBERSICHT_SYSTEM = (
    f"{GRUNDREGELN} Du fasst die Monatsübersichten eines Jahres zu einer ausführlichen "
    "Jahresübersicht zusammen: die großen Ereignisse, Ausflüge und Erlebnisse, die das "
    "Jahr geprägt haben, sowie die persönliche Entwicklung - Höhen und Tiefen, Freude und "
    "Trauer, was gut gelaufen ist und was weniger, welche Learnings erkennbar sind - "
    "jeweils nur, soweit sich das aus den gegebenen Monatsübersichten ergibt."
)


def monats_uebersicht_prompt(tage: list[tuple[str, str]]) -> str:
    """`tage`: Liste von (Datumsanzeige, Tages-Stichpunkte), ältester zuerst."""
    eingabe = "\n\n".join(f"{anzeige}:\n{stichpunkte}" for anzeige, stichpunkte in tage)
    return (
        "Schreibe aus den folgenden Tages-Stichpunkten eines Monats eine ausführliche "
        "Monatsübersicht in mehreren zusammenhängenden Absätzen. Erzähle, was die großen "
        "Ereignisse und Unternehmungen des Monats waren. Gehe außerdem auf die Stimmung im "
        "Monat ein: gab es Erfolge oder schöne Momente, gab es Rückschläge oder schwierige "
        "Phasen, was hat sichtlich beschäftigt - aber nur, soweit sich das aus den "
        "Stichpunkten erkennen lässt. Erfinde nichts hinzu. Gib zusätzlich drei bis fünf "
        "kurze Stichpunkte für eine Vorschau zurück.\n\n"
        f"Tages-Stichpunkte:\n{eingabe}"
    )


def jahres_uebersicht_prompt(monate: list[tuple[str, str]]) -> str:
    """`monate`: Liste von (Monatsanzeige, Monatsübersicht-Text), ältester zuerst."""
    eingabe = "\n\n".join(f"{anzeige}:\n{text}" for anzeige, text in monate)
    return (
        "Schreibe aus den folgenden Monatsübersichten eines Jahres eine ausführliche "
        "Jahresübersicht in mehreren Absätzen. Gehe auf die großen Ereignisse, Ausflüge "
        "und Erlebnisse ein, die das Jahr geprägt haben. Gehe außerdem ausführlich auf die "
        "persönliche Entwicklung ein: Höhen und Tiefen, Freude und Trauer, was gut "
        "gelaufen ist und was weniger, welche Learnings erkennbar sind - aber nur, soweit "
        "sich das aus den Monatsübersichten ergibt. Erfinde nichts hinzu. Gib zusätzlich "
        "drei bis fünf kurze Stichpunkte für eine Vorschau zurück.\n\n"
        f"Monatsübersichten:\n{eingabe}"
    )


# --------------------------------------------------------------------------
# Frage zur Vergangenheit (Abschnitt 7.6: „Suche/Frage“). Nutzt dieselben
# Zusammenfassungen wie die Rückschau als Kontext, siehe ki/fragen.py.
# --------------------------------------------------------------------------

FRAGE_SYSTEM = (
    f"{GRUNDREGELN} Du beantwortest einer Person Fragen zu ihrer eigenen Vergangenheit "
    "anhand von Auszügen aus ihrem Tagebuch. Lässt sich die Frage aus den gegebenen "
    "Informationen nicht beantworten, sage das offen, statt etwas zu vermuten oder zu erfinden."
)

FRAGE_SCHEMA = {
    "type": "object",
    "properties": {"antwort": {"type": "string"}},
    "required": ["antwort"],
}


def frage_prompt(frage: str, kontext: str) -> str:
    return (
        "Beantworte die folgende Frage ausschließlich anhand der gegebenen Auszüge aus dem "
        "Tagebuch. Wenn die Antwort darin nicht enthalten ist, sage ehrlich, dass sich das "
        "in den Einträgen nicht findet, statt zu raten.\n\n"
        f"Frage: {frage}\n\n"
        f"Auszüge aus dem Tagebuch:\n{kontext}"
    )
