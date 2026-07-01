from rest_framework import serializers
from .models import *
from quiz.models import Position, Organization, Department
from quiz.serializers import OrganizationSerializer, DepartmentSerializer, PositionSerializer

class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = [
            "id",
            "government_job",
            "title",
            "description",
            "pdf",
            "link",
            "created_at",
            "updated_at",
        ]




class GovernmentJobSerializer(serializers.ModelSerializer):
    # Read-only nested serializers
    organization = OrganizationSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    positions = PositionSerializer(read_only=True, many=True)  # ✅ changed from "position"

    # Writable fields
    organization_id = serializers.IntegerField(write_only=True, required=True)
    department_id = serializers.IntegerField(write_only=True, required=False)
    position_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    pdf = serializers.SerializerMethodField()


    notices = NoticeSerializer(many=True, read_only=True) 
    
    class Meta:
        model = GovernmentJob
        fields = '__all__'

    def create(self, validated_data):
        organization_id = validated_data.pop('organization_id')
        department_id = validated_data.pop('department_id', None)
        position_ids = validated_data.pop('position_ids', [])

        organization = Organization.objects.get(id=organization_id)
        department = Department.objects.get(id=department_id) if department_id else None

        government_job = GovernmentJob.objects.create(
            organization=organization,
            department=department,
            **validated_data
        )

        if position_ids:
            positions = Position.objects.filter(id__in=position_ids)
            government_job.positions.set(positions)  # ✅ correct for M2M

        return government_job

    def update(self, instance, validated_data):
        organization_id = validated_data.pop('organization_id', None)
        department_id = validated_data.pop('department_id', None)
        position_ids = validated_data.pop('position_ids', None)

        if organization_id:
            instance.organization = Organization.objects.get(id=organization_id)
        if department_id:
            instance.department = Department.objects.get(id=department_id)
        if position_ids is not None:
            positions = Position.objects.filter(id__in=position_ids)
            instance.positions.set(positions)  # ✅ correct for M2M

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def get_pdf(self, obj):
        if obj.pdf:
            return obj.pdf.url   # just /media/...
        return None

