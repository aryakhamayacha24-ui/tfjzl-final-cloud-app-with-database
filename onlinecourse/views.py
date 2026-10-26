
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST

from .models import (
    Choice,
    Course,
    Enrollment,
    Question,
    Submission,
)


def registration_request(request):
    context = {}

    if request.method == "GET":
        return render(
            request,
            "onlinecourse/user_registration_bootstrap.html",
            context,
        )

    username = request.POST.get("username", "").strip()
    password = request.POST.get("psw", "")
    first_name = request.POST.get("firstname", "")
    last_name = request.POST.get("lastname", "")

    if not username or not password:
        context["message"] = "Username and password are required."
        return render(
            request,
            "onlinecourse/user_registration_bootstrap.html",
            context,
        )

    if User.objects.filter(username=username).exists():
        context["message"] = "User already exists."
        return render(
            request,
            "onlinecourse/user_registration_bootstrap.html",
            context,
        )

    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    login(request, user)
    return redirect("onlinecourse:index")


def login_request(request):
    context = {}

    if request.method == "GET":
        return render(
            request,
            "onlinecourse/user_login_bootstrap.html",
            context,
        )

    username = request.POST.get("username", "")
    password = request.POST.get("psw", "")

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is not None:
        login(request, user)
        return redirect("onlinecourse:index")

    context["message"] = "Invalid username or password."
    return render(
        request,
        "onlinecourse/user_login_bootstrap.html",
        context,
    )


def logout_request(request):
    logout(request)
    return redirect("onlinecourse:index")


def check_if_enrolled(user, course):
    if not user.is_authenticated:
        return False

    return Enrollment.objects.filter(
        user=user,
        course=course,
    ).exists()


class CourseListView(generic.ListView):
    template_name = "onlinecourse/course_list_bootstrap.html"
    context_object_name = "course_list"

    def get_queryset(self):
        courses = Course.objects.order_by("-total_enrollment")[:10]

        for course in courses:
            course.is_enrolled = check_if_enrolled(
                self.request.user,
                course,
            )

        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "onlinecourse/course_details_bootstrap.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        context["is_enrolled"] = check_if_enrolled(
            self.request.user,
            course,
        )
        context["exam_questions"] = (
            course.questions.prefetch_related("choice_set").all()
        )

        return context


@login_required
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    if request.method == "POST":
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={"mode": Enrollment.HONOR},
        )

        if created:
            course.total_enrollment += 1
            course.save(update_fields=["total_enrollment"])

    return HttpResponseRedirect(
        reverse(
            "onlinecourse:course_details",
            args=(course.id,),
        )
    )


@login_required
@require_POST
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course=course,
    )

    submission = Submission.objects.create(
        enrollment=enrollment,
    )

    for question in course.questions.all():
        selected_id = request.POST.get(str(question.id))

        if not selected_id:
            continue

        choice = Choice.objects.filter(
            pk=selected_id,
            question=question,
        ).first()

        if choice:
            submission.choices.add(choice)

    return redirect(
        "onlinecourse:show_exam_result",
        course_id=course.id,
        submission_id=submission.id,
    )


@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)

    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__user=request.user,
        enrollment__course=course,
    )

    selected_choices = list(
        submission.choices.select_related("question")
    )

    selected_ids = [choice.id for choice in selected_choices]

    selected_by_question = {
        choice.question_id: choice
        for choice in selected_choices
    }

    total_score = 0
    possible_score = 0
    results = []

    questions = course.questions.prefetch_related("choice_set")

    for question in questions:
        selected = selected_by_question.get(question.id)

        # Calculate the score using the Question model method.
        question_selected_ids = (
            [selected.id] if selected is not None else []
        )

        question_score = question.is_get_score(
            question_selected_ids
        )

        total_score += question_score
        possible_score += question.grade

        correct_choices = list(
            question.choice_set.filter(is_correct=True)
        )

        results.append({
            "question": question,
            "selected_choice": selected,
            "correct_choices": correct_choices,
            "correct_choice": (
                correct_choices[0] if correct_choices else None
            ),
            "is_correct": question_score == question.grade,
            "choices": question.choice_set.all(),
        })

    grade_percent = (
        round(total_score * 100 / possible_score)
        if possible_score > 0
        else 0
    )

    context = {
        "course": course,
        "submission": submission,
        "total_score": total_score,
        "possible_score": possible_score,
        "selected_ids": selected_ids,
        "possible": possible_score,
        "grade_percent": grade_percent,
        "grade": grade_percent,
        "max_grade": 100,
        "results": results,
        "choices": selected_choices,
    }

    return render(
        request,
        "onlinecourse/exam_result_bootstrap.html",
        context,
    )
