from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from api.models import Chapter, Sentence, Word


PRACTICE_DATA = [
    {
        "chapter": "인사와 일상",
        "difficulty": "beginner",
        "context_tag": "daily",
        "words": [
            ("감사합니다", "고맙습니다"),
            ("실례합니다", "미안합니다"),
            ("괜찮아요", "일 없습니다"),
            ("조금만 기다려 주세요", "잠깐 기다려 주십시오"),
            ("처음 뵙겠습니다", "처음 만나 뵙겠습니다"),
            ("잘 부탁드립니다", "잘 부탁합니다"),
            ("전화드릴게요", "전화하겠습니다"),
            ("확인해 볼게요", "확인해 보겠습니다"),
        ],
        "sentences": [
            ("안녕하세요, 오늘 처음 뵙겠습니다.", "안녕하십니까, 오늘 처음 만나 뵙겠습니다."),
            ("잠시만 기다려 주세요.", "잠깐 기다려 주십시오."),
            ("지금 바로 확인해 볼게요.", "지금 바로 확인해 보겠습니다."),
            ("오늘은 일정이 조금 바빠요.", "오늘은 일정이 조금 바쁩니다."),
            ("연락 주셔서 감사합니다.", "련락 주셔서 고맙습니다."),
            ("괜찮으시면 내일 다시 이야기해요.", "일 없으시면 래일 다시 이야기합시다."),
            ("필요하시면 제가 도와드릴게요.", "필요하시면 제가 도와드리겠습니다."),
            ("먼저 들어가 보겠습니다.", "먼저 들어가 보겠습니다."),
            ("이해하기 쉽게 다시 설명해 주세요.", "리해하기 쉽게 다시 설명해 주십시오."),
            ("오늘도 수고 많으셨습니다.", "오늘도 수고 많으셨습니다."),
        ],
    },
    {
        "chapter": "식당과 음식",
        "difficulty": "beginner",
        "context_tag": "food",
        "words": [
            ("포장", "싸가기"),
            ("맵기", "매운 정도"),
            ("영수증", "영수표"),
            ("현금", "현찰"),
            ("카드", "카드"),
            ("추가 주문", "더 주문"),
            ("계산", "결제"),
            ("반찬", "부식"),
        ],
        "sentences": [
            ("이 메뉴는 맵기 조절이 되나요?", "이 차림표 음식은 매운 정도를 조절할 수 있습니까?"),
            ("덜 맵게 부탁드려요.", "덜 맵게 해주십시오."),
            ("포장해서 가져가고 싶어요.", "싸서 가져가고 싶습니다."),
            ("반찬을 조금 더 주실 수 있나요?", "부식을 조금 더 주실 수 있습니까?"),
            ("영수증 부탁드립니다.", "영수표를 부탁드립니다."),
            ("카드로 계산할게요.", "카드로 결제하겠습니다."),
            ("현금영수증도 발급해 주세요.", "현금영수증도 발급해 주십시오."),
            ("이거 하나 추가 주문할게요.", "이것 하나 더 주문하겠습니다."),
            ("매장이 많이 바쁘네요.", "매장이 매우 바쁩니다."),
            ("음식이 정말 맛있어요.", "음식이 정말 맛있습니다."),
        ],
    },
    {
        "chapter": "병원과 행정",
        "difficulty": "intermediate",
        "context_tag": "medical_admin",
        "words": [
            ("진료 예약", "치료 약속"),
            ("접수", "등록"),
            ("대기 번호", "기다림 번호"),
            ("신분증", "공민증"),
            ("처방전", "약 처방문"),
            ("주민센터", "인민위원회"),
            ("서류", "문건"),
            ("발급", "내줌"),
        ],
        "sentences": [
            ("진료 예약을 변경하고 싶어요.", "치료 약속 시간을 바꾸고 싶습니다."),
            ("접수는 어디에서 하나요?", "등록은 어디에서 합니까?"),
            ("대기 번호가 나오면 안내해 주세요.", "기다림 번호가 나오면 알려 주십시오."),
            ("신분증을 보여 드릴게요.", "공민증을 보여드리겠습니다."),
            ("처방전을 약국에 제출하면 되나요?", "약 처방문을 약국에 내면 됩니까?"),
            ("주민센터에서 서류를 발급받았어요.", "인민위원회에서 문건을 발급받았습니다."),
            ("신청서 작성 방법을 알려 주세요.", "신청서 쓰는 방법을 알려 주십시오."),
            ("필요한 서류가 더 있나요?", "필요한 문건이 더 있습니까?"),
            ("오늘 안에 처리 가능한가요?", "오늘 안에 처리가 가능합니까?"),
            ("문제가 생기면 다시 방문할게요.", "문제가 생기면 다시 찾아오겠습니다."),
        ],
    },
    {
        "chapter": "직장과 대화",
        "difficulty": "intermediate",
        "context_tag": "work",
        "words": [
            ("회의", "협의회"),
            ("업무 보고", "사업 총화"),
            ("동료", "동무"),
            ("마감", "끝내는 시각"),
            ("일정", "계획"),
            ("휴가", "휴식일"),
            ("인수인계", "사업 넘겨주기"),
            ("피드백", "의견"),
        ],
        "sentences": [
            ("오늘 회의는 세 시에 시작합니다.", "오늘 협의회는 세 시에 시작합니다."),
            ("업무 보고 자료를 메일로 보냈습니다.", "사업 총화 자료를 메일로 보냈습니다."),
            ("마감 전에 한 번 더 확인해 주세요.", "끝내는 시각 전 한 번 더 확인해 주십시오."),
            ("이번 주 일정이 변경되었습니다.", "이번 주 계획이 변경되었습니다."),
            ("동료와 역할을 나눠서 진행할게요.", "동무와 역할을 갈라 진행하겠습니다."),
            ("휴가 일정은 다음 주로 잡을게요.", "휴식일 계획은 다음 주로 잡겠습니다."),
            ("인수인계 문서를 작성해 두었습니다.", "사업 넘겨주기 문서를 작성해 두었습니다."),
            ("피드백 주셔서 감사합니다.", "의견 주셔서 고맙습니다."),
            ("어려운 부분은 같이 해결해 봅시다.", "어려운 부분은 함께 해결합시다."),
            ("회의록은 오늘 안에 공유하겠습니다.", "회의록은 오늘 안에 공유하겠습니다."),
        ],
    },
    {
        "chapter": "교통과 길찾기",
        "difficulty": "beginner",
        "context_tag": "transport",
        "words": [
            ("환승", "갈아타기"),
            ("정류장", "정차장"),
            ("출구", "나가는 곳"),
            ("요금", "삯"),
            ("교통카드", "승차카드"),
            ("노선", "운행길"),
            ("막차", "마지막 차"),
            ("길 안내", "길 설명"),
        ],
        "sentences": [
            ("이 버스는 시청까지 가나요?", "이 뻐스는 시청까지 갑니까?"),
            ("지하철 환승은 어디에서 하나요?", "지하전동차 갈아타기는 어디에서 합니까?"),
            ("가장 가까운 출구가 몇 번인가요?", "가장 가까운 나가는 곳이 몇 번입니까?"),
            ("교통카드 충전은 여기서 되나요?", "승차카드 충전은 여기서 됩니까?"),
            ("요금은 얼마인가요?", "삯은 얼마입니까?"),
            ("막차 시간이 언제예요?", "마지막 차 시간이 언제입니까?"),
            ("이 주소까지 길 안내 부탁드려요.", "이 주소까지 길 설명 부탁드립니다."),
            ("택시를 어디서 잡으면 되나요?", "택시는 어디서 타면 됩니까?"),
            ("도착까지 몇 분 걸릴까요?", "도착까지 몇 분 걸리겠습니까?"),
            ("길이 막혀서 조금 늦을 것 같아요.", "길이 막혀 조금 늦을 것 같습니다."),
        ],
    },
    {
        "chapter": "쇼핑과 결제",
        "difficulty": "beginner",
        "context_tag": "shopping",
        "words": [
            ("교환", "바꾸기"),
            ("환불", "돈 돌려받기"),
            ("사이즈", "크기"),
            ("할인", "깎기"),
            ("포인트", "적립점수"),
            ("결제", "계산"),
            ("품절", "다 팔림"),
            ("재고", "남은 물건"),
        ],
        "sentences": [
            ("이 옷은 다른 사이즈가 있나요?", "이 옷은 다른 크기가 있습니까?"),
            ("할인 적용이 가능한가요?", "값 깎기 적용이 가능합니까?"),
            ("포인트 적립도 해 주세요.", "적립점수도 넣어 주십시오."),
            ("교환 기간이 어떻게 되나요?", "바꾸는 기간이 어떻게 됩니까?"),
            ("환불은 카드 취소로 진행해 주세요.", "돈 돌려받기는 카드 취소로 진행해 주십시오."),
            ("이 상품은 품절인가요?", "이 상품은 다 팔렸습니까?"),
            ("재고가 들어오면 연락 부탁드려요.", "남은 물건이 들어오면 련락 부탁드립니다."),
            ("결제는 한 번에 하겠습니다.", "계산은 한 번에 하겠습니다."),
            ("영수증은 모바일로 받아도 되나요?", "영수표는 휴대전화로 받아도 됩니까?"),
            ("포장도 같이 부탁드립니다.", "싸가는 것도 함께 부탁드립니다."),
        ],
    },
    {
        "chapter": "학교와 공부",
        "difficulty": "intermediate",
        "context_tag": "education",
        "words": [
            ("수강 신청", "과목 등록"),
            ("과제", "학습 과업"),
            ("발표", "토론 발표"),
            ("시험 범위", "시험 범주"),
            ("출석", "참석"),
            ("지각", "늦음"),
            ("보충 수업", "보강 수업"),
            ("상담", "의논"),
        ],
        "sentences": [
            ("수강 신청 기간이 언제까지인가요?", "과목 등록 기간이 언제까지입니까?"),
            ("과제 제출 마감이 오늘입니다.", "학습 과업 제출 마감이 오늘입니다."),
            ("발표 자료를 미리 공유해 주세요.", "토론 발표 자료를 미리 공유해 주십시오."),
            ("시험 범위를 다시 알려 주세요.", "시험 범주를 다시 알려 주십시오."),
            ("출석 체크는 앱으로 하나요?", "참석 확인은 앱으로 합니까?"),
            ("지각하면 감점이 되나요?", "늦으면 점수가 깎입니까?"),
            ("보충 수업 일정이 잡혔습니다.", "보강 수업 일정이 잡혔습니다."),
            ("진로 상담을 신청하고 싶어요.", "진로 의논을 신청하고 싶습니다."),
            ("이 부분을 다시 설명해 주세요.", "이 부분을 다시 설명해 주십시오."),
            ("복습 자료를 받아 볼 수 있을까요?", "복습 자료를 받아볼 수 있습니까?"),
        ],
    },
    {
        "chapter": "은행과 통신",
        "difficulty": "advanced",
        "context_tag": "finance_telecom",
        "words": [
            ("계좌", "통장"),
            ("이체", "송금"),
            ("비밀번호", "암호"),
            ("한도", "제한액"),
            ("수수료", "봉사료"),
            ("요금제", "통신 계획"),
            ("본인 인증", "신원 확인"),
            ("재발급", "다시 발급"),
        ],
        "sentences": [
            ("새 계좌를 만들고 싶습니다.", "새 통장을 만들고 싶습니다."),
            ("이체 한도를 올릴 수 있나요?", "송금 제한액을 올릴 수 있습니까?"),
            ("비밀번호를 변경하고 싶어요.", "암호를 바꾸고 싶습니다."),
            ("수수료가 얼마나 나오나요?", "봉사료가 얼마나 나옵니까?"),
            ("휴대폰 요금제를 변경하려고 해요.", "휴대전화 통신 계획을 바꾸려고 합니다."),
            ("본인 인증 문자가 오지 않아요.", "신원 확인 문자가 오지 않습니다."),
            ("유심을 재발급받고 싶습니다.", "유심을 다시 발급받고 싶습니다."),
            ("인터넷 속도가 너무 느려요.", "인터넷 속도가 너무 느립니다."),
            ("자동이체를 설정해 주세요.", "자동송금을 설정해 주십시오."),
            ("상담사 연결 부탁드립니다.", "상담원 련결 부탁드립니다."),
        ],
    },
]


class Command(BaseCommand):
    help = "탈북민 사투리 교정용 연습 콘텐츠(챕터/단어/문장)를 중복 없이 추가합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="master",
            help="콘텐츠를 소유할 사용자명 (기본: master)",
        )
        parser.add_argument(
            "--reset-progress",
            action="store_true",
            help="기존 단어/문장의 호출/정답/정확도 상태를 초기화합니다.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options.get("username") or "master"
        user_model = get_user_model()
        owner, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "is_active": True,
                "is_staff": username == "master",
                "is_superuser": username == "master",
                "email": f"{username}@local",
            },
        )
        if created:
            owner.set_unusable_password()
            owner.save(update_fields=["password"])

        created_chapters = 0
        created_words = 0
        created_sentences = 0

        for item in PRACTICE_DATA:
            chapter_title = item["chapter"]
            chapter, chapter_created = Chapter.objects.get_or_create(
                owner=owner,
                title=chapter_title,
                defaults={
                    "accuracy": 0.0,
                    "difficulty": item.get("difficulty", "beginner"),
                    "context_tag": item.get("context_tag", "daily"),
                },
            )
            if chapter_created:
                created_chapters += 1
            else:
                updated_fields = []
                new_difficulty = item.get("difficulty")
                new_context_tag = item.get("context_tag")
                if new_difficulty and chapter.difficulty != new_difficulty:
                    chapter.difficulty = new_difficulty
                    updated_fields.append("difficulty")
                if new_context_tag and chapter.context_tag != new_context_tag:
                    chapter.context_tag = new_context_tag
                    updated_fields.append("context_tag")
                if updated_fields:
                    chapter.save(update_fields=updated_fields)

            for korean, north in item["words"]:
                if not Word.objects.filter(chapter=chapter, korean_word=korean).exists():
                    Word.objects.create(
                        chapter=chapter,
                        korean_word=korean,
                        north_korean_word=north,
                        is_called=False,
                        is_correct=False,
                        is_collect=False,
                        accuracy=0.0,
                    )
                    created_words += 1

            for korean, north in item["sentences"]:
                if not Sentence.objects.filter(chapter=chapter, korean_sentence=korean).exists():
                    Sentence.objects.create(
                        chapter=chapter,
                        korean_sentence=korean,
                        north_korean_sentence=north,
                        is_called=False,
                        is_correct=False,
                        is_collect=False,
                        accuracy=0.0,
                    )
                    created_sentences += 1

        if options["reset_progress"]:
            Word.objects.filter(chapter__owner=owner).update(
                is_called=False, is_correct=False, is_collect=False, accuracy=0.0
            )
            Sentence.objects.filter(chapter__owner=owner).update(
                is_called=False, is_correct=False, is_collect=False, accuracy=0.0
            )
            Chapter.objects.filter(owner=owner).update(accuracy=0.0)
            self.stdout.write(
                self.style.WARNING("학습/평가 진행도(호출/정답/정확도)를 초기화했습니다.")
            )

        self.stdout.write(
            self.style.SUCCESS(
                "완료: "
                f"chapters +{created_chapters}, "
                f"words +{created_words}, "
                f"sentences +{created_sentences}"
            )
        )
