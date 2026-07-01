from django.db import models
from django.utils import timezone
import hashlib
class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)  # EN, FR
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class PartOfSpeech(models.Model):
    name = models.CharField(max_length=30)  # noun, verb, adjective

    def __str__(self):
        return self.name


class Word(models.Model):
    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        related_name="words"
    )
    text = models.CharField(max_length=100, db_index=True)
    phonetic_uk = models.CharField(max_length=100, blank=True)
    phonetic_us = models.CharField(max_length=100, blank=True)
    part_of_speech = models.ForeignKey(
        PartOfSpeech,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("language", "text", "part_of_speech")
        ordering = ["text"]   # 🔥 dictionary-style sorting

    def save(self, *args, **kwargs):
        self.text = self.text.lower()
        super().save(*args, **kwargs)

    
    @classmethod
    def today_word(cls):
        today = timezone.now().strftime("%Y-%m-%d")

        qs = cls.objects.all().order_by("id")
        count = qs.count()

        if count == 0:
            return None

        # Deterministic index based on date
        index = int(
            hashlib.sha256(today.encode()).hexdigest(),
            16
        ) % count

        return qs[index]
    
    
    
    def __str__(self):
        return f"{self.text} ({self.part_of_speech})"

class Sense(models.Model):
    word = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name="senses"
    )
    short_definition = models.TextField()
    usage_note = models.TextField(blank=True)  # formal, informal, etc.

    # NEW: comma-separated text
    synonyms = models.TextField(
        blank=True,
        help_text="Comma separated synonyms (e.g. add, connect, join)"
    )
    antonyms = models.TextField(
        blank=True,
        help_text="Comma separated antonyms (e.g. remove, subtract)"
    )
    
    def get_synonyms_list(self):
        return [s.strip() for s in self.synonyms.split(",") if s.strip()]

    def get_antonyms_list(self):
        return [a.strip() for a in self.antonyms.split(",") if a.strip()]
    
    
    def __str__(self):
        return self.short_definition



class BanglaMeaning(models.Model):
    sense = models.ForeignKey(
        Sense,
        on_delete=models.CASCADE,
        related_name="bangla_meanings"
    )
    meaning = models.TextField()
    note = models.CharField(
        max_length=100,
        blank=True,
        help_text="formal / informal / literal / figurative"
    )

    def __str__(self):
        return self.meaning



class Definition(models.Model):
    sense = models.ForeignKey(
        Sense,
        on_delete=models.CASCADE,
        related_name="definitions"
    )
    definition_text = models.TextField()

    def __str__(self):
        return self.definition_text

class DefinitionTranslation(models.Model):
    definition = models.ForeignKey(
        Definition,
        on_delete=models.CASCADE,
        related_name="translations"
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    translated_text = models.TextField()

    class Meta:
        unique_together = ("definition", "language")

    def __str__(self):
        return self.translated_text


class ExampleSentence(models.Model):
    sense  = models.ForeignKey(Sense, on_delete=models.CASCADE, related_name="examples")
    sentence = models.TextField()

    def __str__(self):
        return self.sentence


class ExampleTranslation(models.Model):
    example = models.ForeignKey(
        ExampleSentence,
        on_delete=models.CASCADE,
        related_name="translations"
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE
    )
    translated_text = models.TextField()

    class Meta:
        unique_together = ("example", "language")

    def __str__(self):
        return self.translated_text


# class Synonym(models.Model):
#     sense = models.ForeignKey(
#         Sense,
#         on_delete=models.CASCADE,
#         related_name="synonyms"
#     )
    
#     word = models.ForeignKey(
#         Word,
#         on_delete=models.CASCADE,
#         related_name="as_synonym"
#     )


#     class Meta:
#         unique_together = ("sense", "word")

#     def __str__(self):
#         return self.word.text


# class Antonym(models.Model):
#     sense = models.ForeignKey(
#         Sense,
#         on_delete=models.CASCADE,
#         related_name="antonyms"
#     )
#     word = models.ForeignKey(
#         Word,
#         on_delete=models.CASCADE,
#         related_name="as_antonym"
#     )


    # class Meta:
    #     unique_together = ("sense", "word")

    # def __str__(self):
    #     return self.word.text


class WordForm(models.Model):
    word = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name="forms"
    )
    form = models.CharField(max_length=100)  # plural, past tense
    label = models.CharField(max_length=50)  # plural, past, gerund

    def __str__(self):
        return f"{self.form} ({self.label})"
