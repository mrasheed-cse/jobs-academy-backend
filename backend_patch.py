# Run this on the server to add ModelTestCreateView and ModelTestPastExamsView

VIEWS_TO_ADD = '''

class ModelTestCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        method = request.data.get('method', 'question_bank')
        title           = request.data.get('title', '').strip()
        total_questions = int(request.data.get('total_questions', 50))
        total_marks     = int(request.data.get('total_marks', 100))
        pass_mark       = int(request.data.get('pass_mark', 50))
        duration        = int(request.data.get('duration', 60))
        negative_mark   = float(request.data.get('negative_mark', 0.25))
        organization_id = request.data.get('organization_id')
        exam_type_id    = request.data.get('exam_type_id')

        if not title:
            return Response({'error': 'মডেল টেস্টের নাম দিন'}, status=400)

        try:
            exam_type = ExamType.objects.get(id=int(exam_type_id)) if exam_type_id else ExamType.objects.first()
        except (ExamType.DoesNotExist, TypeError, ValueError):
            exam_type = ExamType.objects.first()

        organization = Organization.objects.filter(id=organization_id).first() if organization_id else None

        if method == 'question_bank':
            return self._create_from_question_bank(request, title, total_questions, total_marks, pass_mark, duration, negative_mark, organization, exam_type)
        elif method == 'excel':
            return self._create_from_excel(request, title, total_questions, total_marks, pass_mark, duration, negative_mark, organization, exam_type)
        else:
            return Response({'error': 'Invalid method'}, status=400)

    def _create_from_question_bank(self, request, title, total_questions, total_marks, pass_mark, duration, negative_mark, organization, exam_type):
        past_exam_ids_raw = request.data.get('past_exam_ids', [])
        if isinstance(past_exam_ids_raw, str):
            try: past_exam_ids = json.loads(past_exam_ids_raw)
            except: past_exam_ids = []
        else:
            past_exam_ids = list(past_exam_ids_raw)
        past_exam_ids = [int(x) for x in past_exam_ids if x]

        if not past_exam_ids:
            return Response({'error': 'অন্তত একটি পরীক্ষা নির্বাচন করুন'}, status=400)

        past_exams = PastExam.objects.filter(pk__in=past_exam_ids)
        peqs = (PastExamQuestion.objects.filter(exam__in=past_exams)
                .select_related('question').prefetch_related('question__options').distinct())

        available = peqs.count()
        if available < total_questions:
            return Response({'error': f'নির্বাচিত পরীক্ষাগুলোতে মাত্র {available}টি প্রশ্ন আছে। {total_questions}টি চাওয়া হয়েছে।'}, status=400)

        selected_peqs = list(peqs.order_by('?')[:total_questions])
        random.shuffle(selected_peqs)
        return self._save_exam(request, title, total_questions, total_marks, pass_mark, duration, negative_mark, organization, exam_type, selected_peqs)

    def _create_from_excel(self, request, title, total_questions, total_marks, pass_mark, duration, negative_mark, organization, exam_type):
        import openpyxl
        from io import BytesIO
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Excel ফাইল দিন'}, status=400)
        try:
            wb = openpyxl.load_workbook(BytesIO(file.read()))
            ws = wb.active
            rows = list(ws.iter_rows(min_row=2, values_only=True))
        except Exception as e:
            return Response({'error': f'Excel পড়তে সমস্যা: {e}'}, status=400)

        created_questions = []
        errors = []
        for i, row in enumerate(rows, 2):
            if not row or not row[0]: continue
            try:
                q_text = str(row[0]).strip()
                opts   = [str(row[j]).strip() if len(row) > j and row[j] else '' for j in range(1, 5)]
                answer = str(row[5]).strip().upper() if len(row) > 5 and row[5] else 'A'
                subj   = str(row[6]).strip() if len(row) > 6 and row[6] else 'General'
                subject, _ = Subject.objects.get_or_create(name=subj)
                category, _ = Category.objects.get_or_create(name='Model Test')
                question, created = Question.objects.get_or_create(
                    text=q_text,
                    defaults={'marks': 1, 'difficulty_level': 3, 'subject': subject, 'category': category, 'status': 'approved'}
                )
                if created:
                    for k, opt_text in enumerate(opts, 1):
                        if opt_text:
                            QuestionOption.objects.create(question=question, text=opt_text, is_correct=(f'option{k}' == f'option{ord(answer)-64}' if answer.isalpha() else k == int(answer)))
                created_questions.append(question)
            except Exception as e:
                errors.append(f'Row {i}: {e}')

        if not created_questions:
            return Response({'error': 'কোনো প্রশ্ন পাওয়া যায়নি', 'errors': errors}, status=400)

        selected = created_questions[:total_questions]
        return self._save_exam_from_questions(request, title, len(selected), total_marks, pass_mark, duration, negative_mark, organization, exam_type, selected, errors)

    def _save_exam(self, request, title, total_questions, total_marks, pass_mark, duration, negative_mark, organization, exam_type, selected_peqs):
        with transaction.atomic():
            exam = Exam.objects.create(
                title=title, total_questions=total_questions, total_mark=total_marks,
                pass_mark=pass_mark, duration=timedelta(minutes=duration),
                negative_mark=negative_mark, created_by=request.user,
                exam_type=exam_type, organization=organization,
            )
            Status.objects.create(exam=exam, status='draft', user=request.user)
            for i, peq in enumerate(selected_peqs):
                q = peq.question
                eq = ExamQuestion.objects.create(exam=exam, question=q, points=1.0, order=i+1)
                for opt in q.options.all()[:4]:
                    ExamQuestionOption.objects.create(exam_question=eq, option=opt)
        return Response({'exam_id': str(exam.exam_id), 'title': exam.title, 'total_questions': total_questions, 'message': f\'মডেল টেস্ট "{title}" সফলভাবে তৈরি হয়েছে!\' }, status=201)

    def _save_exam_from_questions(self, request, title, total_questions, total_marks, pass_mark, duration, negative_mark, organization, exam_type, questions, errors):
        with transaction.atomic():
            exam = Exam.objects.create(
                title=title, total_questions=total_questions, total_mark=total_marks,
                pass_mark=pass_mark, duration=timedelta(minutes=duration),
                negative_mark=negative_mark, created_by=request.user,
                exam_type=exam_type, organization=organization,
            )
            Status.objects.create(exam=exam, status='draft', user=request.user)
            for i, q in enumerate(questions):
                eq = ExamQuestion.objects.create(exam=exam, question=q, points=1.0, order=i+1)
                for opt in q.options.all()[:4]:
                    ExamQuestionOption.objects.create(exam_question=eq, option=opt)
        return Response({'exam_id': str(exam.exam_id), 'title': exam.title, 'total_questions': total_questions, 'message': f\'মডেল টেস্ট "{title}" সফলভাবে তৈরি হয়েছে!\', 'warnings': errors[:5]}, status=201)


class ModelTestPastExamsView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        org_id = request.query_params.get('organization_id')
        qs = PastExam.objects.filter(is_published=True).select_related('organization', 'position').order_by('-exam_date')
        if org_id:
            qs = qs.filter(organization_id=org_id)
        data = [{'id': e.pk, 'title': e.title, 'organization': e.organization.name if e.organization else '',
                 'position': e.position.name if e.position else '', 'exam_date': str(e.exam_date),
                 'total_questions': e.total_questions} for e in qs[:100]]
        return Response({'past_exams': data, 'total': len(data)})
'''

import os
views_path = '/home/all_projects/jobsAcademy/Quiz-Application/quiz/views.py'
with open(views_path) as f:
    c = f.read()

if 'class ModelTestCreateView(' not in c:
    c += VIEWS_TO_ADD
    with open(views_path, 'w') as f:
        f.write(c)
    print('Views added')
else:
    print('Already exists')
