from django.shortcuts import render, redirect
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from miniproject.scheduler.timetable_algorithm import TimetableGenerator, Subject as AlgoSubject
from miniproject.scheduler.models import (
    Class, Teacher, Subject, SubjectRequirement,
    SubjectTeacher, Lab, ReservedSlot, Timetable,
    TeacherAvailability
)


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
DAY_NAMES_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def index(request):
    return render(request, "input.html", {
        "teachers": Teacher.objects.all().order_by("teacher_name"),
        "subjects": Subject.objects.select_related("class_ref").all().order_by("class_ref__class_name", "subject_name"),
        "labs": Lab.objects.all().order_by("lab_name"),
        "classes": Class.objects.all().order_by("class_name"),
    })


# ==================== TEACHER AVAILABILITY ====================

def teacher_availability_view(request):
    """Render the Teacher Availability Matrix page."""
    return render(request, "teacher_availability.html", {
        "teachers": Teacher.objects.all().order_by("teacher_name"),
    })


@csrf_exempt
def teacher_availability_api(request):
    """
    GET  ?teacher_id=N  → returns 5×6 matrix as JSON
    POST {teacher_id, matrix}  → saves the matrix
    """
    if request.method == "GET":
        teacher_id = request.GET.get("teacher_id")
        if not teacher_id:
            return JsonResponse({"error": "teacher_id required"}, status=400)

        # Build a 5×6 matrix, default all available
        matrix = [[True for _ in range(6)] for _ in range(5)]

        slots = TeacherAvailability.objects.filter(teacher_id=int(teacher_id))
        for slot in slots:
            if 0 <= slot.day < 5 and 0 <= slot.period < 6:
                matrix[slot.day][slot.period] = slot.is_available

        return JsonResponse({"matrix": matrix})

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        teacher_id = data.get("teacher_id")
        matrix = data.get("matrix")

        if not teacher_id or not matrix:
            return JsonResponse({"error": "teacher_id and matrix required"}, status=400)

        try:
            teacher = Teacher.objects.get(teacher_id=int(teacher_id))
        except Teacher.DoesNotExist:
            return JsonResponse({"error": "Teacher not found"}, status=404)

        with transaction.atomic():
            for day_idx, row in enumerate(matrix):
                for period_idx, is_available in enumerate(row):
                    TeacherAvailability.objects.update_or_create(
                        teacher=teacher,
                        day=day_idx,
                        period=period_idx,
                        defaults={"is_available": bool(is_available)}
                    )

        return JsonResponse({"status": "saved"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


# ==================== GENERATE TIMETABLE ====================

@transaction.atomic
def generate(request):
    
    # STEP 1: Read form inputs (DB-driven)
   
    selected_class_ids = []
    for i in range(1, 7):
        v = (request.POST.get(f"class_{i}") or "").strip()
        if v:
            selected_class_ids.append(int(v))


    # STEP 2: Clear previous generated data

    Timetable.objects.all().delete()
    ReservedSlot.objects.all().delete()

    # lab rooms.
    Lab.objects.get_or_create(lab_name="Lab A", defaults={"room": "Lab"})
    Lab.objects.get_or_create(lab_name="Lab B", defaults={"room": "Lab"})

    # Load selected classes from DB (master data comes from admin)
    selected_classes = list(Class.objects.filter(class_id__in=selected_class_ids))
    class_by_id = {c.class_id: c for c in selected_classes}
    algo_classes = [c.class_name for c in selected_classes]
    class_by_name = {c.class_name: c for c in selected_classes}

    # STEP 3: Read per-class subject rows 

    algo_subjects = {cname: [] for cname in algo_classes}

    for i in range(1, 7):
        class_id_raw = (request.POST.get(f"class_{i}") or "").strip()
        if not class_id_raw:
            continue
        class_id = int(class_id_raw)
        cls_obj = class_by_id.get(class_id)
        if not cls_obj:
            continue
        cname = cls_obj.class_name

        subj_ids = request.POST.getlist(f"class_{i}_subject[]")
        teacher1_ids = request.POST.getlist(f"class_{i}_teacher1[]")
        teacher2_ids = request.POST.getlist(f"class_{i}_teacher2[]")
        hours_list = request.POST.getlist(f"class_{i}_hours[]")
        kind_list = request.POST.getlist(f"class_{i}_kind[]")  # Theory/Lab
        lab_list = request.POST.getlist(f"class_{i}_lab[]")    # "Lab A"/"Lab B"

        row_count = max(len(subj_ids), len(hours_list), len(kind_list), 0)
        for idx in range(row_count):
            subj_id_raw = (subj_ids[idx] if idx < len(subj_ids) else "").strip()
            if not subj_id_raw:
                continue

            db_subj = Subject.objects.filter(subject_id=int(subj_id_raw), class_ref=cls_obj).first()
            if not db_subj:
                continue

            t1 = (teacher1_ids[idx] if idx < len(teacher1_ids) else "").strip()
            t2 = (teacher2_ids[idx] if idx < len(teacher2_ids) else "").strip()
            teachers = [t for t in (t1, t2) if t]

            hours_raw = (hours_list[idx] if idx < len(hours_list) else "0").strip()
            try:
                hours = int(hours_raw)
            except ValueError:
                hours = 0

            kind = (kind_list[idx] if idx < len(kind_list) else "Theory").strip()
            is_lab = kind == "Lab"
            if is_lab:
                hours = 3

            preferred_lab = None
            if is_lab:
                preferred_lab = (lab_list[idx] if idx < len(lab_list) else "").strip() or None

            # Use subject ID as identity
            algo_subjects[cname].append(
                AlgoSubject(str(db_subj.subject_id), teachers, hours, is_lab, preferred_lab=preferred_lab)
            )

    # STEP 4: Reserved slots (1-based UI → 0-based internal)

    reserved_classes = request.POST.getlist("reserved_class")
    reserved_days = request.POST.getlist("reserved_day")
    reserved_hours = request.POST.getlist("reserved_hour")
    for c_id, d, h in zip(reserved_classes, reserved_days, reserved_hours):
        if d and h:
            cls_obj = class_by_id.get(int(c_id)) if (c_id or "").strip() else None
            day_idx = int(d) - 1
            hour_idx = int(h) - 1
            if 0 <= day_idx < 5 and 0 <= hour_idx < 6:
                ReservedSlot.objects.create(day=day_idx, hour=hour_idx, class_ref=cls_obj)

    algo_reserved = {c: set() for c in algo_classes}
    for slot in ReservedSlot.objects.all():
        if slot.class_ref and slot.class_ref.class_name in algo_reserved:
            algo_reserved[slot.class_ref.class_name].add((slot.day, slot.hour))
        elif not slot.class_ref:
            for c in algo_reserved:
                algo_reserved[c].add((slot.day, slot.hour))

    # STEP 4.5: Load teacher unavailability from database

    teacher_unavailability = {}
    unavail_slots = TeacherAvailability.objects.filter(is_available=False)
    for slot in unavail_slots:
        teacher_id_str = str(slot.teacher_id)
        if teacher_id_str not in teacher_unavailability:
            teacher_unavailability[teacher_id_str] = set()
        teacher_unavailability[teacher_id_str].add((slot.day, slot.period))

    # STEP 5: Run Timetable Algorithm

    generator = TimetableGenerator(algo_classes, algo_subjects, algo_reserved, teacher_unavailability)
    result = generator.generate()

    # Check for conflicts
    if not result["success"]:
        # Build a human-readable conflict report
        conflicts = result.get("conflicts", [])
        teacher_cache = {}
        subject_cache = {}
        conflict_details = []

        for conflict in conflicts:
            # Resolve subject name
            subj_id = conflict["subject_id"]
            if subj_id not in subject_cache:
                db_subj = Subject.objects.filter(subject_id=int(subj_id)).first()
                subject_cache[subj_id] = db_subj.subject_name if db_subj else f"Subject #{subj_id}"
            subj_name = subject_cache[subj_id]

            # Resolve teacher names
            teacher_names = []
            for tid in conflict["teachers"]:
                if tid not in teacher_cache:
                    t = Teacher.objects.filter(teacher_id=int(tid)).first()
                    teacher_cache[tid] = t.teacher_name if t else f"Teacher #{tid}"
                teacher_names.append(teacher_cache[tid])

            # Build blocked slot descriptions
            blocked_descriptions = []
            for bs in conflict["blocked_slots"]:
                tid = bs["teacher_id"]
                if tid not in teacher_cache:
                    t = Teacher.objects.filter(teacher_id=int(tid)).first()
                    teacher_cache[tid] = t.teacher_name if t else f"Teacher #{tid}"
                blocked_descriptions.append({
                    "teacher_name": teacher_cache[tid],
                    "day_name": bs["day_name"],
                    "period": bs["period"],
                })

            conflict_details.append({
                "class_name": conflict["class"],
                "subject_name": subj_name,
                "teacher_names": teacher_names,
                "required_hours": conflict["required_hours"],
                "placed_hours": conflict["placed_hours"],
                "blocked_slots": blocked_descriptions,
            })

        return render(request, "result.html", {
            "conflict_errors": conflict_details,
            "day_names": DAY_NAMES,
        })

    tables = result["timetables"]

    # STEP 6: Save Generated Timetable to Database

    for class_name, grid in tables.items():
        cls_obj = class_by_name[class_name]

        for day_idx, row in enumerate(grid):
            for period_idx, cell in enumerate(row):

                # Determine block type and linked objects
                if (day_idx, period_idx) in algo_reserved[class_name]:
                    block_type = "Reserved"
                    subj_obj = None
                    teacher_obj = None
                    lab_obj = None

                elif cell is None:
                    block_type = "Free"
                    subj_obj = None
                    teacher_obj = None
                    lab_obj = None

                else:
                    # Lab cells
                    if isinstance(cell, dict) and cell.get("type") == "Lab":
                        block_type = "Lab"
                        subject_id = int(cell.get("subject"))
                        lab_name = cell.get("lab")
                        db_subj = Subject.objects.filter(
                            subject_id=subject_id, class_ref=cls_obj
                        ).first()
                        subj_obj = db_subj
                        lab_obj = Lab.objects.filter(lab_name=lab_name).first()
                    else:
                        # Theory subject cell is a string with subject_id
                        db_subj = Subject.objects.filter(
                            subject_id=int(cell), class_ref=cls_obj
                        ).first()
                        block_type = "Subject" if db_subj else "Free"
                        subj_obj = db_subj
                        lab_obj = None

                    # Get first teacher for this subject
                    teacher_obj = None
                    if db_subj:
                        # Try to get the first teacher from the SubjectTeacher relationship
                        st = SubjectTeacher.objects.filter(subject=db_subj).first()
                        if st:
                            teacher_obj = st.teacher

                Timetable.objects.create(
                    class_ref=cls_obj,
                    subject=subj_obj,
                    teacher=teacher_obj,
                    lab=lab_obj,
                    day=day_idx,
                    period=period_idx,
                    block_type=block_type
                )

    # STEP 7: Display

    display_tables = {}
  

    for class_name, cls_obj in class_by_name.items():
        entries = Timetable.objects.filter(class_ref=cls_obj).order_by('day', 'period')

        grid = [[None for _ in range(6)] for _ in range(5)]

        for entry in entries:
            cell_data = {
                'block_type': entry.block_type,
                'subject': entry.subject.subject_name if entry.subject else None,
                'teacher': entry.teacher.teacher_name if entry.teacher else None,
                'lab': entry.lab.lab_name if entry.lab else None,
            }
            grid[entry.day][entry.period] = cell_data

        display_tables[class_name] = grid

    return render(request, "result.html", {
        "tables": display_tables,
        "day_names": DAY_NAMES,
    })