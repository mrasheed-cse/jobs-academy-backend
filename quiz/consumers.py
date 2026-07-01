from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from jwt import decode as jwt_decode
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings
from datetime import timedelta
import time
from .models import Exam, Question, QuestionOption, ExamAttempt, ExamDifficulty
import logging
logger = logging.getLogger(__name__)
User = get_user_model()
import random
class ExamConsumer(AsyncWebsocketConsumer):
    active_users = {}  # Initialize the active users dictionary
    group_questions = {}  # Store the exam questions for the group

    async def connect(self):
        self.exam_id = self.scope['url_route']['kwargs']['exam_id']
        self.user = None  # Will be set later
        self.current_question_index = 0  # Initialize the current question index
        self.group_name = f'exam_{self.exam_id}'  # Set the group name for the exam

        
        # if not hasattr(self, 'active_users'):
        #     self.active_users = {}
        # Accept the WebSocket connection
        await self.accept()
        # Join the exam group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def disconnect(self, close_code):
        # Leave the exam group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if self.user and self.user.username in self.active_users:
            del self.active_users[self.user.username]
            await self.broadcast_active_users()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        # If the action is to authenticate the user, get the token
        if action == 'authenticate':
            token = data.get('token')
            self.user = await self.get_user_from_token(token)
            if not self.user:
                await self.send(text_data=json.dumps({
                    'error': 'Authentication failed. Invalid token.'
                }))
                await self.close()
                return

            if self.user.username not in self.active_users:
                self.active_users[self.user.username] = 0  # Initialize score
                await self.broadcast_active_users() 

            # Start the exam if this is the first user, or join the ongoing exam
            if self.exam_id not in self.group_questions:
                await self.start_exam()
            else:
                await self.send_next_question()

        elif action == 'next_question':
            await self.send_next_question()

        elif action == 'submit_answer':
            question_id = data.get('question_id')
            selected_option_id = data.get('selected_option_id')
            await self.check_answer(question_id, selected_option_id)

    async def broadcast_active_users(self):
        """Broadcast the list of active users and their scores to all users in the group."""
        await self.channel_layer.group_send(self.group_name, {
            'action': 'active_users',
            'type': 'send_active_users',
            'active_users': self.active_users,
        })
    
    async def send_active_users(self, event):
        """Send the list of active users and their scores to the WebSocket."""
        await self.send(text_data=json.dumps({
            'action': 'active_users',
            'users': event['active_users'],
        }))
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            # Decode the JWT token using the secret key
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

            # Extract the phone number from the payload
            phone_number = payload.get('user_id')  # Adjust this according to your token structure
            if phone_number:
                user = User.objects.get(phone_number=phone_number)  # Fetch the user using phone_number
                return user
        except User.DoesNotExist:
            print("User not found")
        except jwt.ExpiredSignatureError:
            print("Token has expired")
        except jwt.InvalidTokenError:
            print("Invalid token")
        
        return None

    async def start_exam(self):
        """Fetch a limited number of exam questions for the group based on difficulty percentages."""
        try:
            # Fetch the exam and its difficulty percentages
            exam = await sync_to_async(Exam.objects.get)(exam_id=self.exam_id)
            # difficulty = await database_sync_to_async(ExamDifficulty.objects.get)(exam=exam)

            # Total number of questions to generate
            
            exam_attempt = await database_sync_to_async(ExamAttempt.objects.create)(
                exam=exam,
                user=self.user,
                total_correct_answers=0
            )
            
            selected_questions = []
            
            questions = await sync_to_async(list)(exam.questions.all())

            if not questions:
                await self.send(text_data=json.dumps({'error': 'No questions found for this exam.'}))
                await self.close()
                return

            self.group_questions[self.exam_id] = questions
            
            
            selected_questions = questions
            
            
            # Shuffle the selected questions to ensure randomness across difficulties
            random.shuffle(selected_questions)

        
            # Store the selected questions for the group
            self.group_questions[self.exam_id] = selected_questions
            self.current_question_index = 0  # Reset question index

            # Send the first question to the user
            await self.send_next_question()

        except Exam.DoesNotExist:
            await self.send(text_data=json.dumps({'error': 'Exam not found.'}))
        except ExamDifficulty.DoesNotExist:
            await self.send(text_data=json.dumps({'error': 'Exam difficulty configuration not found.'}))

    async def send_next_question(self):
        """Send the next question in the exam to all users in the group."""
        questions = self.group_questions.get(self.exam_id, [])
        if self.current_question_index < len(questions):
            question = questions[self.current_question_index]
            duration = await self.get_exam_duration()
            if duration:
                duration_in_seconds = int(duration.total_seconds())
            await self.send(text_data=json.dumps({
                'action': 'question',
                'question': question.text,
                'options': [{'id': option.id, 'text': option.text} for option in await database_sync_to_async(list)(question.options.all())],
                'question_id': question.id,
                'current_question_number': self.current_question_index + 1,
                'total_questions': len(questions),
                'score': await self.get_user_score(),
                'duration': duration_in_seconds
            }))
            self.current_question_index += 1
        else:
            await self.end_exam() 

    async def check_answer(self, question_id, selected_option_id):
        """Validate the selected answer and broadcast score updates."""
        question = await database_sync_to_async(Question.objects.get)(id=question_id)
        selected_option = await database_sync_to_async(QuestionOption.objects.get)(id=selected_option_id)

        # Check if the selected option is correct
        is_correct = selected_option.is_correct

        # Update the user's exam attempt
        exam_attempt = await database_sync_to_async(ExamAttempt.objects.filter(exam_id=self.exam_id, user=self.user).order_by('-attempt_time').first)()

        if is_correct:
            exam_attempt.total_correct_answers += 1
        
        await database_sync_to_async(exam_attempt.save)()

        self.active_users[self.user.username] = exam_attempt.total_correct_answers
        await self.broadcast_score_update()
        
        # Broadcast the updated score to the user
        await self.send(text_data=json.dumps({
            'action': 'score_update',
            'score': exam_attempt.total_correct_answers,
            'correct': is_correct
        }))
    
    async def end_exam(self):
        """End the exam and send the final results."""
        questions = self.group_questions.get(self.exam_id, [])
        correct_answers = self.active_users.get(self.user.username, 0)
        total_questions = len(questions)
        wrong_answers = total_questions - correct_answers

        # Send results to user
        await self.send(text_data=json.dumps({
            'action': 'exam_complete',
            'score': correct_answers,
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers,
            'total_questions': total_questions,
        }))
        await self.broadcast_exam_results(correct_answers, wrong_answers, total_questions)

    
    async def broadcast_score_update(self):
        """Broadcast the scores of all active users to the exam group."""
        await self.channel_layer.group_send(self.group_name, {
            'type': 'send_score_update',
            'active_users': self.active_users,
        })

    async def send_score_update(self, event):
        """Send the score update to all users in the exam group."""
        await self.send(text_data=json.dumps({
            'action': 'active_users',
            'users': event['active_users'],
        }))
        
        
        
        
    async def broadcast_exam_results(self, correct_answers, wrong_answers, total_questions):
        """Broadcast the exam completion results to all users in the group."""
        await self.channel_layer.group_send(self.group_name, {
            'type': 'send_exam_results',
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers,
            'total_questions': total_questions,
        })

    async def send_exam_results(self, event):
        """Send the exam completion results to all users."""
        await self.send(text_data=json.dumps({
            'action': 'exam_complete',
            'correct_answers': event['correct_answers'],
            'wrong_answers': event['wrong_answers'],
            'total_questions': event['total_questions'],
        }))


    @database_sync_to_async
    def get_user_score(self):
        """Calculate the user's current score."""
        exam_attempt = ExamAttempt.objects.filter(exam_id=self.exam_id, user=self.user).first()
        if exam_attempt:
            return exam_attempt.total_correct_answers  # Return the user's current correct answers
        return 0

    @database_sync_to_async
    def get_exam_duration(self):
        exam = Exam.objects.get(exam_id=self.exam_id)
        return exam.duration




# from asgiref.sync import database_sync_to_async
# import jwt
# from django.conf import settings
# from .models import Exam, Question, QuestionOption, ExamAttempt


# from .models import Exam, Question, QuestionOption, ExamAttempt, ExamDifficulty

# User = get_user_model()

# class ExamConsumer(AsyncWebsocketConsumer):
#     active_users = {}  # Initialize the active users dictionary

#     async def connect(self):
#         self.exam_id = self.scope['url_route']['kwargs']['exam_id']
#         self.user = None  # Will be set later
#         self.current_question_index = 0  # Initialize the current question index
#         self.group_name = f'exam_{self.exam_id}'  # Set the group name for the exam

#         # Accept the WebSocket connection
#         await self.accept()
#         # Join the exam group
#         await self.channel_layer.group_add(self.group_name, self.channel_name)

#     async def disconnect(self, close_code):
#         # Leave the exam group
#         await self.channel_layer.group_discard(self.group_name, self.channel_name)
#         if self.user and self.user.username in self.active_users:
#             del self.active_users[self.user.username]
#             await self.broadcast_active_users()

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         action = data.get('action')

#         # If the action is to authenticate the user, get the token
#         if action == 'authenticate':
#             token = data.get('token')
#             self.user = await self.get_user_from_token(token)
#             if not self.user:
#                 await self.send(text_data=json.dumps({
#                     'error': 'Authentication failed. Invalid token.'
#                 }))
#                 print("Authentication failed: Invalid token.")
#                 await self.close()
#                 return
#             else:
#                 print("Authenticated user: {self.user.username}")
#             # Add the user to active users
#             self.active_users[self.user.username] = 0  # Initialize score to 0
#             print(f"Active users after adding {self.user.username}: {self.active_users}")
#             await self.broadcast_active_users()  # Broadcast active users list
#             # Proceed to start the exam after successful authentication
#             await self.start_exam()
        
#         elif action == 'next_question':
#             await self.send_next_question()

#         elif action == 'submit_answer':
#             question_id = data.get('question_id')
#             selected_option_id = data.get('selected_option_id')
#             await self.check_answer(question_id, selected_option_id)

#     async def broadcast_active_users(self):
#         print(f"Sending active users: {self.active_users}")
#         """Broadcast the list of active users and their scores to all users in the group."""
#         await self.channel_layer.group_send(self.group_name, {
#             'action': 'active_users',
#             'type': 'send_active_users',
#             'active_users': self.active_users,
#         })
    
#     async def send_active_users(self, event):
#         print(f"Sending active users: {event['active_users']}")
#         """Send the list of active users and their scores to the WebSocket."""
#         await self.send(text_data=json.dumps({
#             'action': 'active_users',
#             'users': event['active_users'],
#         }))
    
#     @database_sync_to_async
#     def get_user_from_token(self, token):
#         try:
#             # Decode the JWT token using the secret key
#             payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

#             # Extract the phone number from the payload
#             phone_number = payload.get('user_id')  # Adjust this according to your token structure
#             if phone_number:
#                 user = User.objects.get(phone_number=phone_number)  # Fetch the user using phone_number
#                 return user
#         except User.DoesNotExist:
#             print("User not found.")
#         except jwt.ExpiredSignatureError:
#             print("Token has expired.")
#         except jwt.InvalidTokenError:
#             print("Invalid token.")
#         except Exception as e:
#             print("Error decoding token:", e)
        
#         return None

#     async def start_exam(self):
#         """Fetch a limited number of exam questions based on difficulty percentages and send the first one."""
#         try:
#             # Fetch the exam and its difficulty percentages
#             exam = await database_sync_to_async(Exam.objects.prefetch_related('questions').get)(exam_id=self.exam_id)
#             difficulty = await database_sync_to_async(ExamDifficulty.objects.get)(exam=exam)
            
            
            
#             exam_attempt = await database_sync_to_async(ExamAttempt.objects.create)(
#                 exam=exam,
#                 user=self.user,
#                 total_correct_answers=0
#             )
#             # Total number of questions to generate
#             total_questions = exam.questions_to_generate
#             questions_distribution = {
#                 1: total_questions * difficulty.difficulty1_percentage / 100,
#                 2: total_questions * difficulty.difficulty2_percentage / 100,
#                 3: total_questions * difficulty.difficulty3_percentage / 100,
#                 4: total_questions * difficulty.difficulty4_percentage / 100,
#                 5: total_questions * difficulty.difficulty5_percentage / 100,
#                 6: total_questions * difficulty.difficulty6_percentage / 100
#             }
            
#             selected_questions = []
            
#             # Randomly select questions from each difficulty level
#             for level, num_questions in questions_distribution.items():
#                 if num_questions > 0:
#                     # Fetch the questions of the current difficulty level
#                     questions = await database_sync_to_async(list)(
#                         exam.questions.filter(difficulty_level=level).order_by('?')[:num_questions]
#                     )
#                     selected_questions.extend(questions)
            
#             # Shuffle the selected questions to ensure randomness across difficulties
#             random.shuffle(selected_questions)

#             # Set the questions for the exam session
#             self.questions = selected_questions
            
#             # Send the first question to the user
#             await self.send_next_question()

#         except Exam.DoesNotExist:
#             await self.send(text_data=json.dumps({'error': 'Exam not found.'}))
#         except ExamDifficulty.DoesNotExist:
#             await self.send(text_data=json.dumps({'error': 'Exam difficulty configuration not found.'}))

#     async def send_next_question(self):
#         """Send the next question in the exam."""
#         if self.current_question_index < len(self.questions):
#             question = self.questions[self.current_question_index]
#             await self.send(text_data=json.dumps({
#                 'action': 'question',
#                 'question': question.text,
#                 'options': [{'id': option.id, 'text': option.text} for option in await database_sync_to_async(list)(question.options.all())],
#                 'question_id': question.id,
#                 'current_question_number': self.current_question_index + 1,
#                 'total_questions': len(self.questions),
#                 'score': await self.get_user_score()
#             }))
#             self.current_question_index += 1
#         else:
#             await self.send(text_data=json.dumps({'action': 'exam_complete', 'message': 'All questions have been answered.'}))

#     async def check_answer(self, question_id, selected_option_id):
#         """Validate the selected answer and broadcast score updates."""
#         question = await database_sync_to_async(Question.objects.get)(id=question_id)
#         selected_option = await database_sync_to_async(QuestionOption.objects.get)(id=selected_option_id)

#         # Check if the selected option is correct
#         is_correct = selected_option.is_correct

#         # exam = await database_sync_to_async(Exam.objects.get)(exam_id=self.exam_id)
#         # Update the user's exam attempt
#         exam_attempt = await database_sync_to_async(ExamAttempt.objects.filter(exam_id=self.exam_id, user=self.user).order_by('-timestamp').first)()

#         if is_correct:
#             exam_attempt.total_correct_answers += 1
        
#         await database_sync_to_async(exam_attempt.save)()

#         self.active_users[self.user.username] = exam_attempt.total_correct_answers
#         await self.broadcast_score_update()
        
#         # Broadcast the updated score to the user
#         await self.send(text_data=json.dumps({
#             'action': 'score_update',
#             'score': exam_attempt.total_correct_answers,
#             'correct': is_correct
#         }))
        
#     async def broadcast_score_update(self):
#         """Broadcast the scores of all active users to the exam group."""
#         await self.channel_layer.group_send(self.group_name, {
#             'type': 'send_score_update',
#             'active_users': self.active_users,
#         })

#     async def send_score_update(self, event):
#         """Send the score update to all users in the exam group."""
#         await self.send(text_data=json.dumps({
#             'action': 'active_users',
#             'users': event['active_users'],
#         }))

#     @database_sync_to_async
#     def get_user_score(self):
#         """Calculate the user's current score."""
#         exam_attempt = ExamAttempt.objects.filter(exam_id=self.exam_id, user=self.user).first()
#         if exam_attempt:
#             return exam_attempt.total_correct_answers  # Return the user's current correct answers
#         return 0




# class ExamConsumer(AsyncWebsocketConsumer):
#     active_users = {}  # Initialize the active users dictionary
#     group_questions = {}  # Store the exam questions for the group

#     async def connect(self):
#         self.exam_id = self.scope['url_route']['kwargs']['exam_id']
#         self.user = None  # Will be set later
#         self.current_question_index = 0  # Initialize the current question index
#         self.group_name = f'exam_{self.exam_id}'  # Set the group name for the exam

        
#         # if not hasattr(self, 'active_users'):
#         #     self.active_users = {}
#         # Accept the WebSocket connection
#         await self.accept()
#         # Join the exam group
#         await self.channel_layer.group_add(self.group_name, self.channel_name)

#     async def disconnect(self, close_code):
#         # Leave the exam group
#         await self.channel_layer.group_discard(self.group_name, self.channel_name)
#         if self.user and self.user.username in self.active_users:
#             del self.active_users[self.user.username]
#             await self.broadcast_active_users()
#         await self.channel_layer.group_discard(self.group_name, self.channel_name)

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         action = data.get('action')

#         # If the action is to authenticate the user, get the token
#         if action == 'authenticate':
#             token = data.get('token')
#             self.user = await self.get_user_from_token(token)
#             if not self.user:
#                 await self.send(text_data=json.dumps({
#                     'error': 'Authentication failed. Invalid token.'
#                 }))
#                 await self.close()
#                 return

#             if self.user.username not in self.active_users:
#                 self.active_users[self.user.username] = 0  # Initialize score
#                 await self.broadcast_active_users() 

#             # Start the exam if this is the first user, or join the ongoing exam
#             if self.exam_id not in self.group_questions:
#                 await self.start_exam()
#             else:
#                 await self.send_next_question()

#         elif action == 'next_question':
#             await self.send_next_question()

#         elif action == 'submit_answer':
#             question_id = data.get('question_id')
#             selected_option_id = data.get('selected_option_id')
#             await self.check_answer(question_id, selected_option_id)

#     async def broadcast_active_users(self):
#         """Broadcast the list of active users and their scores to all users in the group."""
#         await self.channel_layer.group_send(self.group_name, {
#             'action': 'active_users',
#             'type': 'send_active_users',
#             'active_users': self.active_users,
#         })
    
#     async def send_active_users(self, event):
#         """Send the list of active users and their scores to the WebSocket."""
#         await self.send(text_data=json.dumps({
#             'action': 'active_users',
#             'users': event['active_users'],
#         }))
    
#     @database_sync_to_async
#     def get_user_from_token(self, token):
#         try:
#             # Decode the JWT token using the secret key
#             payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

#             # Extract the phone number from the payload
#             phone_number = payload.get('user_id')  # Adjust this according to your token structure
#             if phone_number:
#                 user = User.objects.get(phone_number=phone_number)  # Fetch the user using phone_number
#                 return user
#         except User.DoesNotExist:
#             print("User not found")
#         except jwt.ExpiredSignatureError:
#             print("Token has expired")
#         except jwt.InvalidTokenError:
#             print("Invalid token")
        
#         return None

#     async def start_exam(self):
#         """Fetch a limited number of exam questions for the group based on difficulty percentages."""
#         try:
#             # Fetch the exam and its difficulty percentages
#             exam = await sync_to_async(Exam.objects.get)(exam_id=self.exam_id)
#             # difficulty = await database_sync_to_async(ExamDifficulty.objects.get)(exam=exam)

#             # Total number of questions to generate
            
#             exam_attempt = await database_sync_to_async(ExamAttempt.objects.create)(
#                 exam=exam,
#                 user=self.user,
#                 total_correct_answers=0
#             )
            
            
            
#             # total_questions = exam.total_questions
#             # questions_distribution = {
#             #     1: total_questions * difficulty.difficulty1_percentage / 100,
#             #     2: total_questions * difficulty.difficulty2_percentage / 100,
#             #     3: total_questions * difficulty.difficulty3_percentage / 100,
#             #     4: total_questions * difficulty.difficulty4_percentage / 100,
#             #     5: total_questions * difficulty.difficulty5_percentage / 100,
#             #     6: total_questions * difficulty.difficulty6_percentage / 100
#             # }
            
#             selected_questions = []
            
#             # Randomly select questions from each difficulty level
#             # for level, num_questions in questions_distribution.items():
#             #     if num_questions > 0:
#             #         # Fetch the questions of the current difficulty level
#             #         questions = await database_sync_to_async(list)(
#             #             exam.questions.filter(difficulty_level=level).order_by('?')[:num_questions]
#             #         )
#             #         selected_questions.extend(questions)
            
#             questions = await sync_to_async(list)(exam.questions.all())

#             if not questions:
#                 await self.send(text_data=json.dumps({'error': 'No questions found for this exam.'}))
#                 await self.close()
#                 return

#             self.group_questions[self.exam_id] = questions
            
            
#             selected_questions = questions
            
            
#             # Shuffle the selected questions to ensure randomness across difficulties
#             random.shuffle(selected_questions)

        
#             # Store the selected questions for the group
#             self.group_questions[self.exam_id] = selected_questions
#             self.current_question_index = 0  # Reset question index

#             # Send the first question to the user
#             await self.send_next_question()

#         except Exam.DoesNotExist:
#             await self.send(text_data=json.dumps({'error': 'Exam not found.'}))
#         except ExamDifficulty.DoesNotExist:
#             await self.send(text_data=json.dumps({'error': 'Exam difficulty configuration not found.'}))

#     async def send_next_question(self):
#         """Send the next question in the exam to all users in the group."""
#         questions = self.group_questions.get(self.exam_id, [])
#         if self.current_question_index < len(questions):
#             question = questions[self.current_question_index]
#             await self.send(text_data=json.dumps({
#                 'action': 'question',
#                 'question': question.text,
#                 'options': [{'id': option.id, 'text': option.text} for option in await database_sync_to_async(list)(question.options.all())],
#                 'question_id': question.id,
#                 'current_question_number': self.current_question_index + 1,
#                 'total_questions': len(questions),
#                 'score': await self.get_user_score()
#             }))
#             self.current_question_index += 1
#         else:
#             await self.send(text_data=json.dumps({'action': 'exam_complete', 'message': 'All questions have been answered.'}))

#     async def check_answer(self, question_id, selected_option_id):
#         """Validate the selected answer and broadcast score updates."""
#         question = await database_sync_to_async(Question.objects.get)(id=question_id)
#         selected_option = await database_sync_to_async(QuestionOption.objects.get)(id=selected_option_id)

#         # Check if the selected option is correct
#         is_correct = selected_option.is_correct

#         # Update the user's exam attempt
#         exam_attempt = await database_sync_to_async(ExamAttempt.objects.filter(exam_id=self.exam_id, user=self.user).order_by('-attempt_time').first)()

#         if is_correct:
#             exam_attempt.total_correct_answers += 1
        
#         await database_sync_to_async(exam_attempt.save)()

#         self.active_users[self.user.username] = exam_attempt.total_correct_answers
#         await self.broadcast_score_update()
        
#         # Broadcast the updated score to the user
#         await self.send(text_data=json.dumps({
#             'action': 'score_update',
#             'score': exam_attempt.total_correct_answers,
#             'correct': is_correct
#         }))
        
#     async def broadcast_score_update(self):
#         """Broadcast the scores of all active users to the exam group."""
#         await self.channel_layer.group_send(self.group_name, {
#             'type': 'send_score_update',
#             'active_users': self.active_users,
#         })

#     async def send_score_update(self, event):
#         """Send the score update to all users in the exam group."""
#         await self.send(text_data=json.dumps({
#             'action': 'active_users',
#             'users': event['active_users'],
#         }))

#     @database_sync_to_async
#     def get_user_score(self):
#         """Calculate the user's current score."""
#         exam_attempt = ExamAttempt.objects.filter(exam_id=self.exam_id, user=self.user).first()
#         if exam_attempt:
#             return exam_attempt.total_correct_answers  # Return the user's current correct answers
#         return 0







