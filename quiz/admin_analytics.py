from django.db.models import Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import PastExamAttempt


class DailyTopScorersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.GET.get("date")
        print("hello", date_str)
        if date_str:
            try:
                selected_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        else:
            selected_date = timezone.now().date()

        # Aggregate user scores by date
        top_scorers = (
            PastExamAttempt.objects
            .filter(attempt_time__date=selected_date)
            .values("user__id", "user__username", "user__phone_number")
            .annotate(total_score=Sum("score"))
            .order_by("-total_score")
        )
        print("hello", top_scorers)
        return Response({
            "date": selected_date,
            "top_scorers": list(top_scorers)
        })
# from django.db.models import Sum
# from django.utils import timezone
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from .models import PastExamAttempt


# class DailyTopScorersAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         date_str = request.GET.get("date")
#         if date_str:
#             try:
#                 selected_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
#             except ValueError:
#                 return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
#         else:
#             selected_date = timezone.now().date()

#         # Aggregate user scores by date
#         top_scorers = (
#             PastExamAttempt.objects
#             .filter(attempt_time__date=selected_date)
#             .values("user__id", "user__username", "user__phone_number")
#             .annotate(total_score=Sum("score"))
#             .order_by("-total_score")
#         )

#         return Response({
#             "date": selected_date,
#             "top_scorers": list(top_scorers)
#         })
