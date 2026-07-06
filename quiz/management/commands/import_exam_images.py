import os, json, time, base64
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

class Command(BaseCommand):
    help = 'Import exam questions from images using OpenRouter Vision (free)'

    def add_arguments(self, parser):
        parser.add_argument('--images',   required=True)
        parser.add_argument('--exam',     required=True)
        parser.add_argument('--org',      required=True)
        parser.add_argument('--position', required=True)
        parser.add_argument('--year',     required=True, type=int)
        parser.add_argument('--subject',  default='General Knowledge')
        parser.add_argument('--marks',    default=1, type=int)
        parser.add_argument('--negative', default=0.25, type=float)
        parser.add_argument('--dry-run',  action='store_true')
        parser.add_argument('--delay',    default=3.0, type=float)
        parser.add_argument('--model',    default='google/gemini-2.0-flash-exp:free')

    def handle(self, *args, **options):
        images_dir = Path(options['images'])
        if not images_dir.exists():
            raise CommandError(f'Directory not found: {images_dir}')
        api_key = os.environ.get('OPENROUTER_API_KEY', '')
        if not api_key:
            raise CommandError('OPENROUTER_API_KEY not set. Get free key at https://openrouter.ai/settings/keys')
        exts = {'.jpg','.jpeg','.png','.webp','.bmp'}
        image_files = sorted(f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in exts)
        if not image_files:
            raise CommandError(f'No image files found in {images_dir}')
        self.stdout.write(self.style.SUCCESS(
            f'\n{"─"*60}\n  Exam Import Engine — OpenRouter Vision (Free)\n{"─"*60}\n'
            f'  Images: {len(image_files)}\n  Exam: {options["exam"]}\n'
            f'  Model: {options["model"]}\n  Dry run: {"YES" if options["dry_run"] else "NO"}\n{"─"*60}\n'
        ))
        all_questions, errors = [], []
        for i, img_path in enumerate(image_files, 1):
            self.stdout.write(f'[{i:3}/{len(image_files)}] {img_path.name} ... ', ending='')
            self.stdout.flush()
            try:
                questions = self.scan_image(img_path, api_key, options['model'])
                self.stdout.write(self.style.SUCCESS(f'{len(questions)} question(s)'))
                for q in questions:
                    preview = q['text'][:65] + ('…' if len(q['text']) > 65 else '')
                    correct = f'  → Correct: {q["correct_option"]}' if q.get('correct_option') else ''
                    self.stdout.write(f'        Q{q["number"]}: {preview}{correct}')
                all_questions.extend(questions)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ERROR: {e}'))
                errors.append((img_path.name, str(e)))
            if i < len(image_files):
                time.sleep(options['delay'])
        self.stdout.write(f'\n{"─"*60}\nTotal questions extracted: {len(all_questions)}')
        for name, err in errors:
            self.stdout.write(self.style.ERROR(f'  {name}: {err}'))
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n─── DRY RUN: NOT saving to database ───'))
            self._print_questions(all_questions)
            return
        if not all_questions:
            self.stdout.write(self.style.ERROR('No questions to import.'))
            return
        stats = self.save_to_db(all_questions, options)
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done!\n  Questions created: {stats["q_new"]}\n'
            f'  Skipped: {stats["q_skip"]}\n  Options: {stats["opts"]}\n'
        ))

    def scan_image(self, img_path, api_key, model):
        import requests
        ext_map = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.bmp':'image/png'}
        mime = ext_map.get(img_path.suffix.lower(), 'image/jpeg')
        with open(img_path, 'rb') as f:
            img_b64 = base64.standard_b64encode(f.read()).decode()
        prompt = """Extract ALL multiple-choice questions from this exam paper image.
RULES:
1. Extract every question — do not skip any.
2. Preserve Bengali text exactly.
3. Math: x² → x^2, H₂O → H2O, √x → sqrt(x), π → pi
4. Correct answer marked as ans.A/circled/ticked → record it.
5. Options a/b/c/d or ক/খ/গ/ঘ → output as A/B/C/D.
Output ONLY this JSON:
{"questions":[{"number":1,"text":"question text","options":{"A":"opt a","B":"opt b","C":"opt c","D":"opt d"},"correct_option":"C","subject_hint":"gk"}]}
If no questions: {"questions":[]}"""
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json',
                     'HTTP-Referer':'https://jobs.academy','X-Title':'Jobs Academy'},
            json={'model':model,'max_tokens':4096,
                  'messages':[{'role':'user','content':[
                      {'type':'image_url','image_url':{'url':f'data:{mime};base64,{img_b64}'}},
                      {'type':'text','text':prompt}]}]},
            timeout=60,
        )
        if response.status_code != 200:
            raise ValueError(f'API {response.status_code}: {response.text[:300]}')
        raw = response.json()['choices'][0]['message']['content'].strip()
        if '```' in raw:
            for part in raw.split('```'):
                part = part.strip().lstrip('json').strip()
                if part.startswith('{'):
                    raw = part; break
        s, e = raw.find('{'), raw.rfind('}')+1
        if s == -1: raise ValueError(f'No JSON: {raw[:200]}')
        data = json.loads(raw[s:e])
        questions = []
        for q in data.get('questions', []):
            text = (q.get('text') or '').strip()
            if not text: continue
            opts = {k.strip().upper():str(v).strip() for k,v in (q.get('options') or {}).items() if k.strip().upper() in 'ABCD' and v}
            questions.append({'number':q.get('number',len(questions)+1),'text':text,'options':opts,
                              'correct_option':(q.get('correct_option') or '').strip().upper() or None,
                              'subject_hint':q.get('subject_hint','gk')})
        return questions

    @transaction.atomic
    def save_to_db(self, questions, opts):
        from quiz.models import Question, QuestionOption, Category, Subject, Organization, Position, ExamType, PastExam, PastExamQuestion
        org,_ = Organization.objects.get_or_create(name=opts['org'])
        position,_ = Position.objects.get_or_create(name=opts['position'])
        exam_type,_ = ExamType.objects.get_or_create(name='MCQ')
        smap = {'math':'Mathematics','physics':'Physics','chemistry':'Chemistry','biology':'Biology',
                'english':'English','bangla':'Bengali','gk':'General Knowledge','ict':'ICT'}
        past_exam,created = PastExam.objects.get_or_create(
            title=opts['exam'],
            defaults={'organization':org,'position':position,'exam_type':exam_type,
                      'exam_date':f"{opts['year']}-01-01",'duration':60,
                      'total_questions':len(questions),'pass_mark':50,
                      'negative_mark':opts['negative'],'is_published':True})
        q_new=q_skip=opt_count=0
        for q_data in questions:
            text = q_data['text']
            if Question.objects.filter(text=text).exists():
                q_skip+=1; continue
            sn = smap.get(q_data.get('subject_hint','gk').lower(), opts['subject'])
            subj,_ = Subject.objects.get_or_create(name=sn)
            cat,_ = Category.objects.get_or_create(name=sn)
            question = Question.objects.create(text=text,marks=opts['marks'],category=cat,
                                               subject=subj,difficulty_level=2,status='approved')
            q_new+=1
            for key in ('A','B','C','D'):
                ot = q_data['options'].get(key,'').strip()
                if not ot: continue
                QuestionOption.objects.create(question=question,text=ot,is_correct=(key==q_data.get('correct_option')))
                opt_count+=1
            PastExamQuestion.objects.create(exam=past_exam,question=question,order=q_data['number'],points=float(opts['marks']))
        past_exam.total_questions = PastExamQuestion.objects.filter(exam=past_exam).count()
        past_exam.save(update_fields=['total_questions'])
        return {'exam':opts['exam'],'q_new':q_new,'q_skip':q_skip,'opts':opt_count}

    def _print_questions(self, questions):
        for q in questions:
            self.stdout.write(f'\n  Q{q["number"]}: {q["text"]}')
            for k in ('A','B','C','D'):
                v = q['options'].get(k)
                if v:
                    mark = '✓' if k==q.get('correct_option') else ' '
                    self.stdout.write(f'    [{mark}] {k}. {v}')
