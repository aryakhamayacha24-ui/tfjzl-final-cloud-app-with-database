
# Exam assessment models

class Question(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    question_text = models.TextField()
    grade = models.IntegerField(default=1)

    def __str__(self):
        return self.question_text

    def is_get_score(self, selected_ids):
        correct_choices = self.choice_set.filter(is_correct=True)
        correct_ids = set(correct_choices.values_list("id", flat=True))
        return self.grade if correct_ids == set(selected_ids) else 0


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )
    choice_text = models.CharField(max_length=100)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.choice_text


class Submission(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="submissions"
    )
    choices = models.ManyToManyField(Choice)

    def __str__(self):
        return f"Submission {self.pk}"
