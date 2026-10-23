
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Course, Enrollment, Question, Choice, Submission


@login_required
@require_POST
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(
        Enrollment, user=request.user, course=course
    )

    submission = Submission.objects.create(enrollment=enrollment)

    for question in course.questions.all():
        selected_id = request.POST.get(str(question.id))
        if selected_id:
            choice = Choice.objects.filter(
                pk=selected_id, question=question
            ).first()
            if choice:
                submission.choices.add(choice)

    return redirect(
        "onlinecourse:exam_result",
        course_id=course.id,
        submission_id=submission.id
    )


@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__user=request.user,
        enrollment__course=course
    )

    selected_choices = submission.choices.select_related("question")
    selected_by_question = {
        choice.question_id: choice for choice in selected_choices
    }

    grade = 0
    max_grade = 0
    results = []

    for question in course.questions.prefetch_related("choice_set"):
        max_grade += question.grade
        selected = selected_by_question.get(question.id)
        correct = question.choice_set.filter(is_correct=True).first()

        if selected and selected.is_correct:
            grade += question.grade

        results.append({
            "question": question,
            "selected_choice": selected,
            "correct_choice": correct,
            "is_correct": bool(selected and selected.is_correct),
            "choices": question.choice_set.all(),
        })

    context = {
        "course": course,
        "submission": submission,
        "grade": grade,
        "max_grade": max_grade,
        "choices": selected_choices,
        "results": results,
    }
    return render(
        request,
        "onlinecourse/exam_result_bootstrap.html",
        context
    )
