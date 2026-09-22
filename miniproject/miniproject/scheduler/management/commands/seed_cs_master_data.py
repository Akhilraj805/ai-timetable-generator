from django.core.management.base import BaseCommand
from django.db import transaction

from miniproject.scheduler.models import Class, Teacher, Subject, Lab


SUBJECTS_BY_SEMESTER = {
    3: [
        "MA201: Linear Algebra & Complex Analysis",
        "CS201: Discrete Computational Structures",
        "CS203: Switching Theory and Logic Design",
        "CS205: Data Structures",
        "CS207: Electronics Devices & Circuits",
        "HS210: Life Skills",
        "HS200: Business Economics",
        "CS231: Data Structures Lab",
        "CS233: Electronics Circuits Lab",
    ],
    4: [
        "MA202: Probability Distributions, Transforms and Numerical Methods",
        "CS202: Computer Organization and Architecture",
        "CS204: Operating Systems",
        "CS206: Object Oriented Design and Programming",
        "CS208: Principles of Database Design",
        "HS210: Life Skills",
        "HS200: Business Economics",
        "CS232: FOSS Lab",
        "CS234: Digital Systems Lab",
    ],
    5: [
        "CS301: Theory of Computation",
        "CS303: System Software",
        "CS305: Microprocessors and Microcontrollers",
        "CS307: Data Communication",
        "CS309: Graph Theory and Combinatorics",
        "CS341: Design Project",
        "CS331: System Software Lab",
        "CS333: Application Software Development Lab",
        "Elective I (CS36X): Soft Computing / Signals and Systems / Optimization Techniques / Logic for Computer Science / Digital System Testing & Testable Design",
    ],
    6: [
        "CS302: Design and Analysis of Algorithms",
        "CS304: Compiler Design",
        "CS306: Computer Networks",
        "CS308: Software Engineering and Project Management",
        "HS300: Principles of Management",
        "CS332: Microprocessor Lab",
        "CS334: Network Programming Lab",
        "CS352: Comprehensive Exam",
        "Elective II (CS36X): Computer Vision / Mobile Computing / Natural Language Processing / Web Technologies / High Performance Computing",
    ],
    7: [
        "CS401: Computer Graphics",
        "CS403: Programming Paradigms",
        "CS405: Computer System Architecture",
        "CS407: Distributed Computing",
        "CS409: Cryptography and Network Security",
        "CS451: Seminar & Project Preliminary",
        "CS431: Compiler Design Lab",
        "Elective III (CS46X): Computational Geometry / Digital Image Processing / Bio Informatics / Machine Learning / Computational Complexity",
    ],
    8: [
        "CS402: Data Mining and Warehousing",
        "CS404: Embedded Systems",
        "CS46X: Elective IV (Fuzzy Set Theory / Artificial Intelligence / Data Science / Cloud Computing / Principles of Information Security)",
        "Elective V (Non-Departmental)",
        "CS492: Project",
    ],
}

TEACHERS = [
    "Jisha Miss",
    "Alpha miss",
    "Krishnaveni miss",
    "Shandry miss",
    "Arya miss",
    "Mary Priyanka Miss",
    "Shrutisree miss",
    "Gargi miss",
    "Reenu miss",
    "Anjana miss",
    "Tinimol miss",
    "Jyothis miss",
    "Rakhi miss",
    "Linda miss",
    "Swapna miss",
    "Ojus sir (HOD)",
]


def is_lab_subject(name: str) -> bool:
    return " lab" in name.lower()


class Command(BaseCommand):
    help = "Seed CS department master data (classes/subjects/teachers/labs)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing Teachers/Subjects/Classes (keeps Timetable/ReservedSlot).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = bool(options.get("reset"))

        if reset:
            Subject.objects.all().delete()
            Class.objects.filter(class_name__in=[f"S{s}" for s in SUBJECTS_BY_SEMESTER.keys()]).delete()
            Teacher.objects.all().delete()

        # Labs
        Lab.objects.get_or_create(lab_name="Lab A", defaults={"room": "Lab"})
        Lab.objects.get_or_create(lab_name="Lab B", defaults={"room": "Lab"})

        # Teachers
        created_teachers = 0
        for t in TEACHERS:
            _, created = Teacher.objects.get_or_create(teacher_name=t.strip())
            created_teachers += int(created)

        # Semester "classes" (S3..S8) and their subjects
        created_classes = 0
        created_subjects = 0
        for sem, subj_list in SUBJECTS_BY_SEMESTER.items():
            cls, created = Class.objects.get_or_create(
                class_name=f"S{sem}",
                defaults={"semester": sem},
            )
            if not created and cls.semester != sem:
                cls.semester = sem
                cls.save(update_fields=["semester"])
            created_classes += int(created)

            for subj_name in subj_list:
                stype = "Lab" if is_lab_subject(subj_name) else "Theory"
                _, created_subj = Subject.objects.get_or_create(
                    class_ref=cls,
                    subject_name=subj_name.strip(),
                    defaults={"subject_type": stype, "semester": sem},
                )
                created_subjects += int(created_subj)

        self.stdout.write(self.style.SUCCESS("Seed completed."))
        self.stdout.write(
            f"Created: {created_teachers} teachers, {created_classes} classes, {created_subjects} subjects."
        )

