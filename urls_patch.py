urls_path = '/home/all_projects/jobsAcademy/Quiz-Application/quiz/urls.py'
with open(urls_path) as f:
    c = f.read()

if 'ModelTestCreateView' not in c:
    # Add import
    c = c.replace(
        'from .views import *',
        'from .views import *\nfrom .views import ModelTestCreateView, ModelTestPastExamsView'
    )
    # Add URLs
    c = c.rstrip()
    c += """
    path('model-tests/create/', ModelTestCreateView.as_view(), name='model-test-create'),
    path('model-tests/past-exams/', ModelTestPastExamsView.as_view(), name='model-test-past-exams'),
"""
    # This needs to be inside urlpatterns - find the closing bracket
    with open(urls_path, 'w') as f:
        f.write(c)
    print('URLs added')
else:
    print('Already exists')
