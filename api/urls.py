from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChapterViewSet,
    SentenceViewSet,
    WordViewSet,
    chat_with_gemini,
    evaluate_pronunciation,
    get_chapter_evaluation_results,
    get_chapter_learning_progress,
    get_next_chapter,
    get_progress,
    get_review_queue,
    get_saved_sentences,
    get_saved_words,
    mark_sentence_as_called,
    mark_word_as_called,
    reset_sentence_pronunciation,
    update_sentence,
    update_sentence_accuracy,
    update_sentence_accuracy_and_text,
    update_word,
)

router = DefaultRouter()
router.register(r"chapters", ChapterViewSet, basename="chapters")
router.register(r"words", WordViewSet, basename="words")
router.register(r"sentences", SentenceViewSet, basename="sentences")

urlpatterns = [
    path("", include(router.urls)),
    path("chapters/<int:pk>/words/", ChapterViewSet.as_view({"get": "words"}), name="chapter-words"),
    path(
        "chapters/<int:pk>/sentences/",
        ChapterViewSet.as_view({"get": "sentences"}),
        name="chapter-sentences",
    ),
    path(
        "chapters/<int:pk>/incollect_words/",
        ChapterViewSet.as_view({"get": "incollect_words"}),
        name="chapter-incollect-words",
    ),
    path(
        "chapters/<int:pk>/incollect_sentences/",
        ChapterViewSet.as_view({"get": "incollect_sentences"}),
        name="chapter-incollect-sentences",
    ),
    path("chapters/<int:pk>/accuracy/", ChapterViewSet.as_view({"get": "accuracy"}), name="chapter-accuracy"),
    path("chapters/<int:chapter_id>/learning_progress/", get_chapter_learning_progress, name="chapter-learning-progress"),
    path(
        "chapters/<int:chapter_id>/evaluation_results/",
        get_chapter_evaluation_results,
        name="chapter-evaluation-results",
    ),
    path("words/<int:pk>/save/", WordViewSet.as_view({"post": "save_word"}), name="word-save"),
    path("sentences/<int:pk>/save/", SentenceViewSet.as_view({"post": "save_sentence"}), name="sentence-save"),
    path("words/<int:word_id>/update/", update_word, name="word-update"),
    path("sentences/<int:sentence_id>/update/", update_sentence, name="sentence-update"),
    path("words/<int:word_id>/mark_called/", mark_word_as_called, name="word-mark-called"),
    path("sentences/<int:sentence_id>/mark_called/", mark_sentence_as_called, name="sentence-mark-called"),
    path(
        "sentences/<int:sentence_id>/reset_pronunciation/",
        reset_sentence_pronunciation,
        name="sentence-reset-pronunciation",
    ),
    path("sentences/<int:sentence_id>/update_accuracy/", update_sentence_accuracy, name="sentence-update-accuracy"),
    path(
        "sentences/<int:sentence_id>/update_accuracy_and_text/",
        update_sentence_accuracy_and_text,
        name="sentence-update-accuracy-and-text",
    ),
    path("saved_words/", get_saved_words, name="saved-words"),
    path("saved_sentences/", get_saved_sentences, name="saved-sentences"),
    path("get_progress/", get_progress, name="get-progress"),
    path("next_chapter/", get_next_chapter, name="next-chapter"),
    path("review_queue/", get_review_queue, name="review-queue"),
    path("chat/", chat_with_gemini, name="chat-with-gemini"),
    path("pronunciation/evaluate/", evaluate_pronunciation, name="evaluate-pronunciation"),
]
