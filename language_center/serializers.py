from rest_framework import serializers
from .models import (
    Language,
    PartOfSpeech,
    Word,
    Sense,
    BanglaMeaning,
    Definition,
    DefinitionTranslation,
    ExampleSentence,
    ExampleTranslation,
    WordForm,
)

# -------------------------
# BASIC SERIALIZERS
# -------------------------

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "name", "code", "description"]


class PartOfSpeechSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartOfSpeech
        fields = ["id", "name"]


class WordFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = WordForm
        fields = ["id", "form", "label"]


# -------------------------
# DEFINITION SERIALIZERS
# -------------------------

class DefinitionTranslationSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(read_only=True)

    class Meta:
        model = DefinitionTranslation
        fields = ["id", "language", "translated_text"]


class DefinitionSerializer(serializers.ModelSerializer):
    translations = DefinitionTranslationSerializer(many=True, read_only=True)

    class Meta:
        model = Definition
        fields = ["id", "definition_text", "translations"]


# -------------------------
# EXAMPLE SERIALIZERS
# -------------------------

class ExampleTranslationSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(read_only=True)

    class Meta:
        model = ExampleTranslation
        fields = ["id", "language", "translated_text"]


class ExampleSentenceSerializer(serializers.ModelSerializer):
    translations = ExampleTranslationSerializer(many=True, read_only=True)

    class Meta:
        model = ExampleSentence
        fields = ["id", "sentence", "translations"]


# -------------------------
# BANGLA MEANING
# -------------------------

class BanglaMeaningSerializer(serializers.ModelSerializer):
    class Meta:
        model = BanglaMeaning
        fields = ["id", "meaning", "note"]


# -------------------------
# RELATED WORD (FOR SYN/ANT)
# -------------------------

class RelatedWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Word
        fields = ["id", "text"]


# class SynonymSerializer(serializers.ModelSerializer):
#     word = RelatedWordSerializer(read_only=True)

#     class Meta:
#         model = Synonym
#         fields = ["id", "word"]


# class AntonymSerializer(serializers.ModelSerializer):
#     word = RelatedWordSerializer(read_only=True)

#     class Meta:
#         model = Antonym
#         fields = ["id", "word"]


# -------------------------
# SENSE SERIALIZER (CORE)
# -------------------------

class SenseSerializer(serializers.ModelSerializer):
    bangla_meanings = BanglaMeaningSerializer(many=True, read_only=True)
    definitions = DefinitionSerializer(many=True, read_only=True)
    examples = ExampleSentenceSerializer(many=True, read_only=True)

    # expose as list instead of raw comma string (optional but recommended)
    synonyms = serializers.SerializerMethodField()
    antonyms = serializers.SerializerMethodField()

    class Meta:
        model = Sense
        fields = [
            "id",
            "short_definition",
            "usage_note",
            "synonyms",
            "antonyms",
            "bangla_meanings",
            "definitions",
            "examples",
        ]

    def get_synonyms(self, obj):
        if not obj.synonyms:
            return []
        return [s.strip() for s in obj.synonyms.split(",") if s.strip()]

    def get_antonyms(self, obj):
        if not obj.antonyms:
            return []
        return [a.strip() for a in obj.antonyms.split(",") if a.strip()]



# -------------------------
# WORD SERIALIZERS
# -------------------------

class WordSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(read_only=True)
    part_of_speech = PartOfSpeechSerializer(read_only=True)
    forms = WordFormSerializer(many=True, read_only=True)
    senses = SenseSerializer(many=True, read_only=True)

    class Meta:
        model = Word
        fields = [
            "id",
            "text",
            "phonetic_uk",
            "phonetic_us",
            "language",
            "part_of_speech",
            "forms",
            "senses",
        ]

class WordAZSerializer(serializers.ModelSerializer):
    part_of_speech = serializers.StringRelatedField()

    class Meta:
        model = Word
        fields = [
            "id",
            "text",
            "phonetic_uk",
            "phonetic_us",
            "part_of_speech",
        ]


class WordListSerializer(serializers.ModelSerializer):
    part_of_speech = PartOfSpeechSerializer(read_only=True)

    class Meta:
        model = Word
        fields = ["id", "text", "part_of_speech"]



# serializers_excel.py
from rest_framework import serializers

class DictionaryExcelUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file):
        if not file.name.endswith((".xlsx", ".xls")):
            raise serializers.ValidationError("Only Excel files are allowed")
        return file


# -------------------------
# SINGLE WORD CREATION (admin/teacher dictionary upload form)
# -------------------------

class WordCreateSenseSerializer(serializers.Serializer):
    """One sense (definition) of a word, with its translations/examples."""
    short_definition = serializers.CharField()
    usage_note = serializers.CharField(required=False, allow_blank=True, default="")
    bangla_meanings = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    definition_text = serializers.CharField(required=False, allow_blank=True, default="")
    examples = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    examples_bn = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    synonyms = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    antonyms = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class WordCreateSerializer(serializers.Serializer):
    """Input shape for POST /api/words/create/ — a single dictionary word
    with at least one sense. Mirrors the same Word -> Sense ->
    BanglaMeaning/Definition/ExampleSentence structure the Excel bulk
    upload already builds, so both paths produce consistent data."""
    word = serializers.CharField(max_length=100)
    pos = serializers.CharField(max_length=30, help_text="Part of speech, e.g. noun, verb")
    phonetic_uk = serializers.CharField(required=False, allow_blank=True, default="")
    phonetic_us = serializers.CharField(required=False, allow_blank=True, default="")
    forms = serializers.ListField(
        child=serializers.DictField(), required=False, default=list,
        help_text='[{"form": "running", "label": "present participle"}, ...]',
    )
    senses = WordCreateSenseSerializer(many=True)

    def validate_senses(self, value):
        if not value:
            raise serializers.ValidationError("At least one sense (definition) is required.")
        return value
