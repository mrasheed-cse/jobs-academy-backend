"""
AI-powered word importer for English dictionary.
Reads words from Excel, generates all fields via Gemini, saves as pending.
"""
import json
import requests
import threading
from django.db import transaction
from .models import Word, Sense, BanglaMeaning, Definition, DefinitionTranslation, ExampleSentence, ExampleTranslation, Language, PartOfSpeech, WordImportJob


def generate_word_data(word_text: str, api_key: str) -> dict:
    """Call Gemini directly to generate full dictionary entry for a word."""
    prompt = f"""Generate a complete English dictionary entry for the word: "{word_text}"

Return ONLY valid JSON with this exact structure, no markdown, no explanation:
{{
  "word": "{word_text}",
  "phonetic_uk": "/phonetic notation/",
  "phonetic_us": "/phonetic notation/",
  "part_of_speech": "noun|verb|adjective|adverb|preposition|conjunction|interjection",
  "short_definition": "Clear concise English definition in 1-2 sentences",
  "bangla_meaning": "বাংলা অর্থ (2-3 words)",
  "bangla_meaning_note": "formal|informal|literal",
  "definition_text": "Detailed English definition with usage context",
  "definition_bangla": "বিস্তারিত বাংলা অনুবাদ",
  "example_sentence": "A natural example sentence using the word in context.",
  "example_bangla": "উদাহরণ বাক্যের বাংলা অনুবাদ।",
  "synonyms": "synonym1, synonym2, synonym3",
  "antonyms": "antonym1, antonym2",
  "word_level": "beginner|intermediate|advanced"
}}"""

    import time as _time
    for attempt in range(3):  # retry up to 3 times
        resp = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'tencent/hy3:free',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 1000,
            },
            timeout=30
        )
        if resp.status_code == 429:
            _time.sleep(15 * (attempt + 1))  # backoff: 15s, 30s, 45s
            continue
        resp.raise_for_status()
        break
    else:
        resp.raise_for_status()
    content = resp.json()['choices'][0]['message']['content'].strip()
    content = content.replace('```json', '').replace('```', '').strip()
    return json.loads(content)


# Cache languages to avoid transaction issues
_lang_cache = {}

def _get_languages():
    global _lang_cache
    if 'en' not in _lang_cache:
        _lang_cache['en'] = Language.objects.filter(name='English').first()
    if 'bn' not in _lang_cache:
        _lang_cache['bn'] = Language.objects.filter(name='Bangla').first() or Language.objects.filter(name='Bengali').first() or Language.objects.filter(code='BN').first()
    return _lang_cache['en'], _lang_cache['bn']

@transaction.atomic
def save_word_entry(data: dict, job) -> Word:
    """Save generated word data to database."""
    lang_en, lang_bn = _get_languages()

    # Get or create part of speech
    pos_name = data.get('part_of_speech', 'noun').lower()
    pos, _ = PartOfSpeech.objects.get_or_create(name=pos_name)

    # Create Word
    word, created = Word.objects.get_or_create(
        language=lang_en,
        text=data['word'].lower(),
        part_of_speech=pos,
        defaults={
            'phonetic_uk': data.get('phonetic_uk', ''),
            'phonetic_us': data.get('phonetic_us', ''),
        }
    )
    if not created:
        word.phonetic_uk = data.get('phonetic_uk', '')
        word.phonetic_us = data.get('phonetic_us', '')
        word.save()

    # Create Sense
    sense = Sense.objects.create(
        word=word,
        short_definition=data.get('short_definition', ''),
        synonyms=data.get('synonyms', ''),
        antonyms=data.get('antonyms', ''),
    )

    # Create BanglaMeaning
    BanglaMeaning.objects.create(
        sense=sense,
        meaning=data.get('bangla_meaning', ''),
        note=data.get('bangla_meaning_note', ''),
    )

    # Create Definition
    defn = Definition.objects.create(
        sense=sense,
        definition_text=data.get('definition_text', ''),
    )

    # Definition translation (Bangla)
    DefinitionTranslation.objects.create(
        definition=defn,
        language=lang_bn,
        translated_text=data.get('definition_bangla', ''),
    )

    # Example sentence
    example = ExampleSentence.objects.create(
        sense=sense,
        sentence=data.get('example_sentence', ''),
    )

    # Example translation (Bangla)
    ExampleTranslation.objects.create(
        example=example,
        language=lang_bn,
        translated_text=data.get('example_bangla', ''),
    )

    # Link word to import job
    job.words.add(word)

    return word


def process_word_import(job_id: int, words: list, api_key: str):
    """Background thread: process each word via AI.
    Skips duplicates already in the database.
    Tracks: total_attempted, processed, skipped_duplicates, failed.
    """
    from .models import WordImportJob, Word, Language
    job = WordImportJob.objects.get(pk=job_id)
    job.status = 'processing'

    # Deduplicate the input list itself (case-insensitive)
    seen_in_list = set()
    unique_words = []
    for w in words:
        w = w.strip().lower()
        if w and w not in seen_in_list:
            seen_in_list.add(w)
            unique_words.append(w)

    job.total_words = len(unique_words)
    job.save(update_fields=['status', 'total_words'])

    # Check which words already exist in DB
    try:
        lang_en = Language.objects.filter(name='English').first()
        if lang_en:
            existing = set(
                Word.objects.filter(language=lang_en, text__in=unique_words)
                .values_list('text', flat=True)
            )
        else:
            existing = set()
    except Exception:
        existing = set()

    processed = 0
    failed = 0
    skipped = len(existing)

    # Record duplicates in job
    if existing:
        job.skipped_words = skipped
        job.skipped_log = ', '.join(sorted(existing))
        job.save(update_fields=['skipped_words', 'skipped_log'])

    # Only process non-existing words
    words_to_process = [w for w in unique_words if w not in existing]

    for word_text in words_to_process:
        job.current_word = word_text
        job.save(update_fields=['current_word'])

        try:
            data = generate_word_data(word_text, api_key)
            save_word_entry(data, job)
            processed += 1
        except Exception as e:
            failed += 1
            job.error_log += f'\n{word_text}: {str(e)}'

        import time
        time.sleep(10)  # 10 second delay for free model rate limits
        job.processed_words = processed
        job.failed_words = failed
        job.save(update_fields=['processed_words', 'failed_words', 'error_log'])

    job.status = 'done'
    job.current_word = ''
    job.save(update_fields=['status', 'current_word'])
