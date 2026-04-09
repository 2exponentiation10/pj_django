from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.learning_visuals import seed_practice_visuals
from api.models import VisualGenerationJob


class Command(BaseCommand):
    help = "Run a queued visual generation job for practice learning assets."

    def add_arguments(self, parser):
        parser.add_argument("job_id", type=int)

    def handle(self, *args, **options):
        job_id = options["job_id"]
        try:
            job = VisualGenerationJob.objects.select_related("owner").get(pk=job_id)
        except VisualGenerationJob.DoesNotExist as exc:
            raise CommandError(f"VisualGenerationJob {job_id} does not exist") from exc

        if job.status == VisualGenerationJob.STATUS_SUCCEEDED:
            self.stdout.write(self.style.WARNING("Job already succeeded"))
            return

        job.status = VisualGenerationJob.STATUS_RUNNING
        job.started_at = timezone.now()
        job.finished_at = None
        job.error_text = ""
        job.message = "작업을 시작합니다."
        job.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "error_text",
                "message",
            ]
        )

        def progress_callback(payload):
            VisualGenerationJob.objects.filter(pk=job.pk).update(
                status=payload.get("status", VisualGenerationJob.STATUS_RUNNING),
                total_items=payload.get("total_items", 0),
                completed_items=payload.get("completed_items", 0),
                chapters_count=payload.get("chapters", 0),
                words_count=payload.get("words", 0),
                sentences_count=payload.get("sentences", 0),
                message=payload.get("message", ""),
            )

        try:
            result = seed_practice_visuals(owner=job.owner, progress_callback=progress_callback)
            VisualGenerationJob.objects.filter(pk=job.pk).update(
                status=VisualGenerationJob.STATUS_SUCCEEDED,
                total_items=result.get("total_items", 0),
                completed_items=result.get("completed_items", 0),
                chapters_count=result.get("chapters", 0),
                words_count=result.get("words", 0),
                sentences_count=result.get("sentences", 0),
                message="시각자료 재생성이 완료되었습니다.",
                finished_at=timezone.now(),
            )
        except Exception as exc:
            VisualGenerationJob.objects.filter(pk=job.pk).update(
                status=VisualGenerationJob.STATUS_FAILED,
                error_text=str(exc),
                message="시각자료 재생성에 실패했습니다.",
                finished_at=timezone.now(),
            )
            raise
