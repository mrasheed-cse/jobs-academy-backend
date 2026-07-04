from collections import defaultdict
import pandas as pd
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter

from .models import *
from .serializers import *
from quiz.permissions import IsTeacherOrAdmin


class LanguageListAPIView(ListAPIView):
    """GET /api/languages/ — list available dictionary languages.

    Read-only, public. Needed because the dictionary upload UI (both
    single-word and bulk-Excel) requires a language_id, and previously
    there was no way for the frontend to discover valid IDs other than
    hardcoding them.
    """
    queryset = Language.objects.all().order_by("name")
    serializer_class = LanguageSerializer
    permission_classes = [AllowAny]


class WordOfTheDayAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        word = Word.today_word()

        if not word:
            return Response(
                {"detail": "No words available"},
                status=404
            )

        serializer = WordSerializer(word)
        return Response(serializer.data)


# GET /api/words/<id>/
class WordDetailAPIView(RetrieveAPIView):
    queryset = (
        Word.objects
        .select_related("language", "part_of_speech")
        .prefetch_related(
            "forms",
            "senses__definitions",
            "senses__examples",
            "senses__bangla_meanings",
        )
    )
    serializer_class = WordSerializer
    permission_classes = [AllowAny]




# GET /api/words/az/
# class WordAZAPIView(APIView):
#     permission_classes = [AllowAny]

#     def get(self, request):
#         queryset = (
#             Word.objects
#             .select_related("part_of_speech", "language")
#             .prefetch_related(
#                 "forms",
#                 "senses__definitions",
#                 "senses__examples",
#                 # "senses__synonyms__word",
#                 # "senses__antonyms__word",
#             )
#             .order_by("text")
#         )

#         grouped_words = defaultdict(list)

#         for word in queryset:
#             letter = word.text[0].upper()
#             grouped_words[letter].append(
#                 WordSerializer(word).data
#             )

#         return Response(dict(sorted(grouped_words.items())))


class WordAZAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = (
            Word.objects
            .select_related("part_of_speech")
            .only(
                "id",
                "text",
                "phonetic_uk",
                "phonetic_us",
                "part_of_speech__name",
            )
            .order_by("text")
        )

        grouped_words = defaultdict(list)

        for word in queryset:
            letter = word.text[0].upper()
            grouped_words[letter].append(
                WordAZSerializer(word).data
            )

        return Response(grouped_words)

# GET /api/words/search/?q=apple
class WordSearchAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip().lower()
        if not query:
            return Response([])

        words = Word.objects.filter(text__istartswith=query).order_by("text")[:20]

        if len(words) < 20:
            extra_words = Word.objects.filter(text__icontains=query).exclude(
                id__in=words.values_list("id", flat=True)
            )[:10]
            words = list(words) + list(extra_words)

        serializer = WordListSerializer(words, many=True)
        return Response(serializer.data)


import re
import pandas as pd

def extract_multi_values(text):
    """
    Extract comma-separated words.
    Quotes are ignored completely.

    Examples:
    add, apply
    "add, apply"
    "add","apply"
    """
    if pd.isna(text):
        return []

    # Remove quotes
    text = re.sub(r'["\']', '', str(text))

    # Split by comma
    return [
        item.strip()
        for item in text.split(',')
        if item.strip()
    ]




class DictionaryExcelUploadAPIView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, language_id):
        serializer = DictionaryExcelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        df = pd.read_excel(serializer.validated_data["file"])

        try:
            language = Language.objects.get(id=language_id)
        except Language.DoesNotExist:
            return Response({"detail": "Invalid language ID"}, status=400)

        bn_language, _ = Language.objects.get_or_create(
            code="BN", defaults={"name": "Bangla"}
        )

        created_senses = 0
        errors = []

        for i, row in df.iterrows():
            try:
                # ---------- PART OF SPEECH ----------
                pos, _ = PartOfSpeech.objects.get_or_create(
                    name=str(row["pos"]).lower().strip()
                )

                # ---------- WORD ----------
                word, _ = Word.objects.get_or_create(
                    language=language,
                    text=str(row["word"]).lower().strip(),
                    part_of_speech=pos,
                    defaults={
                        "phonetic_uk": row.get("phonetic_uk", ""),
                        "phonetic_us": row.get("phonetic_us", "")
                    }
                )

                # ---------- SENSE ----------
                sense, created = Sense.objects.get_or_create(
                    word=word,
                    short_definition=str(row["short_definition"]).strip()
                )
                if created:
                    created_senses += 1

                # ---------- BANGLA MEANINGS ----------
                if pd.notna(row.get("bangla_meanings")):
                    for m in str(row["bangla_meanings"]).split(";"):
                        BanglaMeaning.objects.get_or_create(
                            sense=sense,
                            meaning=m.strip()
                        )

                # ---------- DEFINITIONS ----------
                Definition.objects.get_or_create(
                    sense=sense,
                    definition_text=str(row["short_definition"]).strip()
                )

                # ---------- EXAMPLES ----------
                examples = extract_multi_values(row.get("examples"))
                bn_examples = extract_multi_values(row.get("example_bn"))

                for idx, ex in enumerate(examples):
                    ex_obj, _ = ExampleSentence.objects.get_or_create(
                        sense=sense,
                        sentence=ex
                    )
                    if idx < len(bn_examples):
                        ExampleTranslation.objects.get_or_create(
                            example=ex_obj,
                            language=bn_language,
                            defaults={"translated_text": bn_examples[idx]}
                        )

                # ---------- WORD FORMS ----------
                if pd.notna(row.get("forms")):
                    for f in str(row["forms"]).split(";"):
                        if ":" in f:
                            form, label = f.split(":", 1)
                            WordForm.objects.get_or_create(
                                word=word,
                                form=form.strip(),
                                label=label.strip()
                            )

                # ---------- SYNONYMS (TEXT FIELD) ----------
                if pd.notna(row.get("synonyms")):
                    new_synonyms = extract_multi_values(row["synonyms"])
                    existing = sense.get_synonyms_list()
                    merged = sorted(set(existing + new_synonyms))
                    sense.synonyms = ", ".join(merged)

                # ---------- ANTONYMS (TEXT FIELD) ----------
                if pd.notna(row.get("antonyms")):
                    new_antonyms = extract_multi_values(row["antonyms"])
                    existing = sense.get_antonyms_list()
                    merged = sorted(set(existing + new_antonyms))
                    sense.antonyms = ", ".join(merged)

                sense.save()

            except Exception as e:
                errors.append({
                    "row": i + 2,
                    "error": str(e)
                })

        return Response({
            "language": language.name,
            "created_senses": created_senses,
            "errors": errors
        })


class WordCreateAPIView(APIView):
    """POST /api/language/{language_id}/words/create/ — create a single
    dictionary word with one or more senses. Companion to the Excel bulk
    upload for adding individual words without preparing a spreadsheet.
    Same permission and data model as the bulk upload, so a word created
    here looks identical (in GET /api/words/{id}/) to one created via
    Excel.
    """
    permission_classes = [IsTeacherOrAdmin]

    @transaction.atomic
    def post(self, request, language_id):
        serializer = WordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            language = Language.objects.get(id=language_id)
        except Language.DoesNotExist:
            return Response({"detail": "Invalid language ID"}, status=400)

        bn_language, _ = Language.objects.get_or_create(
            code="BN", defaults={"name": "Bangla"}
        )

        pos, _ = PartOfSpeech.objects.get_or_create(name=data["pos"].lower().strip())

        word, word_created = Word.objects.get_or_create(
            language=language,
            text=data["word"].lower().strip(),
            part_of_speech=pos,
            defaults={
                "phonetic_uk": data.get("phonetic_uk", ""),
                "phonetic_us": data.get("phonetic_us", ""),
            },
        )
        if not word_created:
            return Response(
                {"detail": f"'{data['word']}' already exists for this language and part of speech."},
                status=409,
            )

        for form in data.get("forms", []):
            if form.get("form") and form.get("label"):
                WordForm.objects.get_or_create(
                    word=word, form=str(form["form"]).strip(), label=str(form["label"]).strip()
                )

        for sense_data in data["senses"]:
            sense = Sense.objects.create(
                word=word,
                short_definition=sense_data["short_definition"].strip(),
                usage_note=sense_data.get("usage_note", ""),
                synonyms=", ".join(s.strip() for s in sense_data.get("synonyms", []) if s.strip()),
                antonyms=", ".join(a.strip() for a in sense_data.get("antonyms", []) if a.strip()),
            )

            for meaning in sense_data.get("bangla_meanings", []):
                if meaning.strip():
                    BanglaMeaning.objects.create(sense=sense, meaning=meaning.strip())

            definition_text = sense_data.get("definition_text") or sense_data["short_definition"]
            if definition_text.strip():
                Definition.objects.create(sense=sense, definition_text=definition_text.strip())

            examples = sense_data.get("examples", [])
            examples_bn = sense_data.get("examples_bn", [])
            for i, ex in enumerate(examples):
                if not ex.strip():
                    continue
                ex_obj = ExampleSentence.objects.create(sense=sense, sentence=ex.strip())
                if i < len(examples_bn) and examples_bn[i].strip():
                    ExampleTranslation.objects.create(
                        example=ex_obj, language=bn_language, translated_text=examples_bn[i].strip()
                    )

        return Response(WordSerializer(word).data, status=201)



class IllustrationProxyView(APIView):
    """POST /api/illustration/
    Proxies a request to the Anthropic API to generate an SVG illustration
    for a dictionary example sentence. Keeps the API key server-side.
    Requires authentication (any logged-in user can use this).
    """
    permission_classes = [AllowAny]  # illustration is a public feature

    def post(self, request):
        import os, requests as req_lib

        sentence = request.data.get('sentence', '')
        word = request.data.get('word', '')
        meaning = request.data.get('meaning', '')

        if not sentence:
            return Response({'detail': 'sentence is required'}, status=400)

        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return Response({'detail': 'ANTHROPIC_API_KEY not configured'}, status=503)

        prompt = (
            f'Create a beautiful minimalist animated SVG illustration for this sentence: \"{sentence}\"\n\n'
            f'Key word: \"{word}\" (meaning: \"{meaning}\")\n\n'
            'Rules:\n'
            '- viewBox=\"0 0 400 200\" width=\"400\" height=\"200\"\n'
            '- Flat editorial design, soft professional color palette (3-4 colors)\n'
            '- Include smooth looping CSS animation inside a <style> tag\n'
            '- Clearly represent the sentence meaning through shapes and figures\n'
            '- No text labels inside the SVG\n'
            '- Output ONLY the raw SVG code starting with <svg, nothing else'
        )

        try:
            resp = req_lib.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'claude-sonnet-4-6',
                    'max_tokens': 1500,
                    'messages': [{'role': 'user', 'content': prompt}],
                },
                timeout=30,
            )
            data = resp.json()
            text = data.get('content', [{}])[0].get('text', '')
            import re
            match = re.search(r'<svg[\s\S]*?</svg>', text, re.IGNORECASE)
            if match:
                return Response({'svg': match.group(0)})
            return Response({'detail': 'No SVG in response', 'raw': text[:200]}, status=502)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class PixabayProxyView(APIView):
    """GET /api/pixabay/?q=search+terms&page=1

    Proxies Pixabay image search with in-memory caching to reduce latency.
    - First request: ~600ms (Pixabay API call)
    - Cached requests: <5ms (served from memory)
    Cache expires after 24 hours. Max 500 entries (LRU eviction).
    """
    permission_classes = [AllowAny]
    _cache = {}          # {cache_key: (timestamp, hits)}
    _CACHE_TTL = 86400   # 24 hours
    _MAX_CACHE  = 500

    def get(self, request):
        import os, time, hashlib
        import requests as req_lib

        api_key = os.environ.get('PIXABAY_API_KEY', '')
        if not api_key:
            return Response({'hits': []}, status=200)

        q    = request.GET.get('q', '').strip()
        page = request.GET.get('page', '1')
        if not q:
            return Response({'hits': []})

        # ── Cache lookup ──────────────────────────────────────────────
        cache_key = hashlib.md5(f"{q}|{page}".encode()).hexdigest()
        now = time.time()
        if cache_key in self._cache:
            ts, hits = self._cache[cache_key]
            if now - ts < self._CACHE_TTL:
                return Response({'hits': hits, 'cached': True})

        # ── Pixabay API call ──────────────────────────────────────────
        try:
            resp = req_lib.get(
                'https://pixabay.com/api/',
                params={
                    'key': api_key,
                    'q': q,
                    'image_type': 'photo',
                    'orientation': 'horizontal',
                    'safesearch': 'true',
                    'per_page': 15,
                    'page': page,
                    'lang': 'en',
                    'editors_choice': 'false',
                    'order': 'popular',
                },
                timeout=8,
            )
            data = resp.json()
            hits = [
                {'webformatURL': h['webformatURL'], 'tags': h.get('tags', '')}
                for h in data.get('hits', [])
            ]

            # Evict oldest entry if cache is full
            if len(self._cache) >= self._MAX_CACHE:
                oldest = min(self._cache, key=lambda k: self._cache[k][0])
                del self._cache[oldest]

            self._cache[cache_key] = (now, hits)
            return Response({'hits': hits})
        except Exception as e:
            return Response({'hits': [], 'detail': str(e)})
