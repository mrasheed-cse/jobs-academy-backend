from django.contrib import admin
from .models import (
    Language,
    PartOfSpeech,
    Word,
    Sense,
    Definition,
    ExampleSentence,
    ExampleTranslation,
    BanglaMeaning,
    WordForm,
)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(PartOfSpeech)
class PartOfSpeechAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class WordFormInline(admin.TabularInline):
    model = WordForm
    extra = 0


class BanglaMeaningInline(admin.TabularInline):
    model = BanglaMeaning
    extra = 1


class DefinitionInline(admin.TabularInline):
    model = Definition
    extra = 1


class ExampleTranslationInline(admin.TabularInline):
    model = ExampleTranslation
    extra = 1


class ExampleSentenceInline(admin.TabularInline):
    model = ExampleSentence
    extra = 1
    show_change_link = True


@admin.register(Sense)
class SenseAdmin(admin.ModelAdmin):
    list_display = ("word", "short_definition")
    search_fields = (
        "short_definition",
        "word__text",
        "synonyms",
        "antonyms",
    )
    list_filter = (
        "word__language",
        "word__part_of_speech",
    )

    fieldsets = (
        (None, {
            "fields": ("word", "short_definition", "usage_note")
        }),
        ("Synonyms & Antonyms", {
            "fields": ("synonyms", "antonyms"),
            "description": "Comma separated values only",
        }),
    )

    inlines = [
        DefinitionInline,
        BanglaMeaningInline,
        ExampleSentenceInline,
    ]


@admin.register(ExampleSentence)
class ExampleSentenceAdmin(admin.ModelAdmin):
    list_display = ("sentence", "sense")
    search_fields = ("sentence",)
    inlines = [ExampleTranslationInline]


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("text", "language", "part_of_speech", "created_at")
    search_fields = ("text",)
    list_filter = ("language", "part_of_speech")
    ordering = ("text",)
    inlines = [WordFormInline]
