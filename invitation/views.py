from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from quiz.models import Exam
from .models import ExamInvite
from django.contrib.auth import get_user_model
User = get_user_model()
from django.template.loader import render_to_string
from rest_framework import generics
from .serializers import ExamInviteSerializer


class InviteViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        exam_id = self.kwargs.get('exam_id')  # Get exam_id from URL
        invited_users = request.data.get('user_id', [])  # Expecting a list of user IDs
        # print(invited_users)

        exam = get_object_or_404(Exam, exam_id=exam_id)

        for user_id in invited_users:
            # print(type(user_id))
            user_id = int(user_id)
            try:
                invited_user = User.objects.get(id=user_id)
                print(invited_user)
                invitation, created = ExamInvite.objects.get_or_create(
                    exam=exam,
                    invited_by=request.user,
                    invited_user=invited_user
                )

                # if created:
                invitation.send_invitation_email()  # Assuming you have a method for sending emails
                # You might want to handle cases where the invitation was not created
            except User.DoesNotExist:
                return Response({'detail': f'User with id {user_id} not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'detail': 'Invitations processed successfully'}, status=status.HTTP_200_OK)



@api_view(['POST'])
def accept_invitation(request, token):
    # Get the invitation by token
    invitation = get_object_or_404(ExamInvite, token=token)

    # Ensure the invitation hasn't already been accepted
    # if invitation.invited_user is not None:
    #     return Response({"error": "This invitation has already been accepted."}, status=400)

    # Accept the invitation (you can update any related fields here)
    invitation.invited_user = request.user  # If no login, this can be a placeholder or manual input later
    invitation.status = 'accepted'
    invitation.save()

    return Response({"message": "Invitation accepted successfully."})


class InvitedExamsView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ExamInviteSerializer

    def get_queryset(self):
        # Filter invitations where the current user is the invited_by
        print("hello")
        return ExamInvite.objects.filter(invited_user=self.request.user)

